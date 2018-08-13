#!/usr/bin/env python
 
from datetime import datetime
from yaml import load

import hashlib
import json
import requests
 

with open('./server.yaml', 'r') as fh:
    try:
        config = load(fh)
    except Exception as e:
        print("error loading config file. {}".format(e))
        import sys
        sys.exit(1)


def init_game(level, matches=''):
    '''
    init_game returns a dict that contains:
        commitment: the hash value of the coin flip outcome
        ID: the uuid of the game that was just started
        description: The instructions for playing
    '''
    url = "http://{}:{}/{}".format(config['ip'], config['port1'], level)
    params = dict(
        matches=matches
    )
    response = requests.get(url, params=params)
    if response.ok:
        return response.json()


def submit_answer(ID, answer):
    url = "http://{}:{}/submit".format(config['ip'], config['port1'])
    params = dict(
        ID=ID,
        answer=answer
    )
    response = requests.get(url, params=params)
    if response.ok:
        return response.json()

def partial_match(hash1, hash2, chars_to_match):
    if hash1[0:chars_to_match] == hash2[0:chars_to_match] and hash1[-chars_to_match:] == hash2[-chars_to_match:]:
        return True
    return False

def compute_hash(value, salt=""):

    try:
        value = str(value)
    except Exception as e:
        print("Hash input must be a string or convertible to string: {}".format(e))
        import sys
        sys.exit(1)

    md = hashlib.md5()
    md.update(value + salt)
    digest = md.hexdigest()
    return digest


#print("Welcome and thanks for playing! The time is {}".format(datetime.now().strftime('%Y-%m-%d %H:%M')))

def beat_level0():
    response = init_game("level0")
    print(json.dumps(response, indent=4))

    # your code goes here

    my_answer = str(0) # probably want to update this

    response = submit_answer(response['ID'], my_answer)
    print(json.dumps(response, indent=4))


def beat_level1():
    response = init_game("level1")
    print(json.dumps(response, indent=4))

    # your code goes here

    my_answer = str(0) # probably want to update this

    response = submit_answer(response['ID'], my_answer)
    print(json.dumps(response, indent=4))


def beat_level2():
    chars_to_match = 1
    response = init_game("level2", chars_to_match)
    print(json.dumps(response, indent=4))

    # your code goes here

    my_answer = str(0) # you probably want to update this

    response = submit_answer(response['ID'], my_answer)
    print(json.dumps(response, indent=4))


beat_level0()
#beat_level1()
#beat_level2()


