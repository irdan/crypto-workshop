#!/usr/bin/env python
 
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from urlparse import urlparse, parse_qs
from random import getrandbits
from datetime import datetime

import hashlib
import json
import uuid
 
'''
    Data structure for storage:

I want to keep things simple.  Naively, just store the ID of init (but not completed) games, along with the input needed to reproduce the hash.

This is the minimal set of data to work. 

The next feature would be to try to get sessions, so that there could be a "get X number in a row before proceeding to the next level"

'''

database = {}

def pick_number(bits):
    number = str(getrandbits(bits))
    return number


def compute_hash(value, salt=""):
    md = hashlib.md5()
    md.update(value + salt)
    digest = md.hexdigest()
    return digest


def can_be_int(string):
    try:
        int(string)
        return True
    except:
        return False


def init_game(level, params):
    global database

    # define salt
    ID = str(uuid.uuid4())
    time = datetime.now().strftime('%Y-%m-%d %H:%M')
    if level == '0':
        salt = ''
    elif level == '1':
        salt = "|" + str(ID) + "|" + time
    elif level == '2':
        salt = "|" + str(ID) + "|" + str(uuid.uuid4())

    num_bits = 8
    number = pick_number(num_bits)
    digest = compute_hash(number + salt)

    database[ID] = {'pick': number, 'salt': salt, 'hash': digest, 'level': level}

    if level == '2': # add match character count to database

        if 'matches' not in params:
            return json.dumps({'Error': 'You must specify how lazy the server is'})

        if not can_be_int(params['matches'][0]):
            return json.dumps({'Error': 'You must specify an integer value'})
        
        database[ID]['matches'] = int(params['matches'][0])

    description = "Welcome to level{}. Thanks for playing! Pick a number between 0 and {}".format(level, 2**num_bits - 1)
    response = {"ID": ID, "commitment": digest, 'description': description}
    if level == '1':
        response['time'] = time
    return json.dumps(response)


def partial_match(guess, char_count, digest_number):
    digest_guess = compute_hash(guess)
    if digest_guess[0:char_count] == digest_number[0:char_count]:
        if digest_guess[-char_count:] == digest_number[-char_count:]:
            return True
    return False


def play_game(params):
    global database

    if 'ID' not in params or 'answer' not in params:
        return json.dumps({'Results': "incorrect parameters received"})
    ID = params['ID'][0]
    guess = params['answer'][0]

    if ID not in database:
        return json.dumps({"Error": "ID {} not found in database, have you already played that game?".format(ID)})

    if guess == database[ID]['pick']:
        outcome = "{} is Correct!".format(guess)
    elif database[ID]['level'] == '2' and partial_match(guess, database[ID]['matches'], database[ID]['hash']):
        outcome = "{} is Correct!".format(guess)
    else:
        outcome = "{} is Incorrect :(".format(guess)

    salt = database[ID]['salt']
    input_text = database[ID]['pick'] + database[ID]['salt']
    message = "md5sum({}) = {}".format(input_text, database[ID]['hash'])
    del database[ID]
    return json.dumps({"Results": outcome, "proof": message, 'Game_ID': ID})


# HTTPRequestHandler class
class coinFlipHandler(BaseHTTPRequestHandler):
 
    def do_GET(self):
        # Send response status code
        self.send_response(200)

        # Send headers
        self.send_header('Content-type','text/html')
        self.end_headers()

        path = self.path[1:].split("?")[0]
        query = parse_qs(urlparse(self.path).query)
        if path in ['level0', 'level1', 'level2']:
            message = init_game(path[-1], query)
        elif path in ['submit']:
            message = play_game(query)
        else:
            message = json.dumps({"Error": "Requested endpoint not found. Available endpoints: level0, level1, level2, submit"})
        self.wfile.write(bytes(str(message) + "\n"))
        return
 

def run():
    print('starting server...')
    with open('./server.config', 'r') as fh:
        try:
            ip = fh.readlines()[0]
            print(ip)
        except Exception as e:
            print("error loading config file. {}".format(e))
            import sys
            sys.exit(1)


    server_address = (ip, 9501)
    httpd = HTTPServer(server_address, coinFlipHandler)
    print('running server...')
    httpd.serve_forever()
 
 
run()

