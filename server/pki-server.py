#!/usr/bin/env python
 
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from urlparse import urlparse, parse_qs
from random import getrandbits, randint
from datetime import datetime

from certgen import createKeyPair, createCertRequest, createCertificate, certText, certPEM
from OpenSSL import crypto

import hashlib
import json
import uuid
import base64
 

'''
    Data structure for storage:

I want to keep things simple.  Naively, just store the ID of init (but not completed) games, along with the input needed to reproduce the hash.

This is the minimal set of data to work. 

The next feature would be to try to get sessions, so that there could be a "get X number in a row before proceeding to the next level"

'''

database = {}
certs = {}

def get_serial_number(cert):
    text = certText(cert).split("\n")
    sn = [line for line in text if "Serial Number:" in line][0].split(":")[1].strip()
    return sn


def get_time_offset(params):
    if 'not_before_offset' in params:
        not_before_offset = params['not_before_offset']
    else:
        not_before_offset = 60 * 60 * 24 * -1  #  default to starting yesterday 
        
    if 'not_after_offset' in params:
        not_after_offset = params['not_after_offset']
    else:
        not_after_offset = 60 * 60 * 24 * 30  #  default to 30 days
    return (not_before_offset, not_after_offset)


def write_ca_to_disk(key_material, is_x509_cert):
    if is_x509_cert:
        with open('CA.pkey', 'w') as CA_key:
            CA_key.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key_material).decode('utf-8'))
    else:
        with open('CA.cert', 'w') as CA_cert:
            CA_cert.write(crypto.dump_certificate(crypto.FILETYPE_PEM, key_material).decode('utf-8'))
    return True


def gen_cert(target_key, signing_cert, signing_key, params):

    # Check Params
    if 'CN' not in params:
        print("CN is a required parameter")
        import sys
        sys.exit(1)

    not_before_offset, not_after_offset = get_time_offset(params)

    if 'extensions' not in params:
        params['extensions'] = []
        
    # genrate CSR
    request = createCertRequest(target_key, CN=params['CN'], extensions=params['extensions'])

    # kindly fulfill the request
    cert = createCertificate(request, 
                             (signing_cert, signing_key), 
                             params['SN'], 
                             (not_before_offset, not_after_offset)
                            )
    return cert


def gen_ca(params={}):

    try: # read from existing CA files
        if 'gen_new' in params and params['gen_new']:
            raise ValueError # skip reading from file

        with open("CA.pkey", 'r') as CA_key:
            cakey = crypto.load_privatekey(crypto.FILETYPE_PEM, CA_key.read())
        with open("CA.cert", 'r') as CA_cert:
            cacert = crypto.load_certificate(crypto.FILETYPE_PEM, CA_cert.read())
        return cacert, cakey

    except:
        if 'SN' not in params:
            params['SN'] = 0

        cakey = createKeyPair()

        not_before_offset, not_after_offset = get_time_offset(params)

        careq  = createCertRequest(cakey, CN='Certificate Authority')
        cacert = createCertificate(careq, (careq, cakey), params['SN'], (not_before_offset, not_after_offset))

        if 'gen_new' not in params:
            if write_ca_to_disk(cacert, False) and write_ca_to_disk(cakey, True):
                return cacert, cakey
            else:
                print("Failed to write CA files to disk")
                import sys
                sys.exit(1)
        else:
            return cacert, cakey


def gen_intermediate(level, cacert, cakey, params={}):
    global certs

    if len(certs[level]['intermediates']) > 0:
        sn = int(max(certs[level]['intermediates'].keys())) + 1
    else:
        sn = 1

    params['CN'] = "Intermediate of CA with SN: {}".format(get_serial_number(cacert))
    params['SN'] = sn
    
    intkey = createKeyPair()
    intcert = gen_cert(intkey, cacert, cakey, params)

    certs[level]['intermediates'][sn] = (intcert, intkey)
    return intcert, intkey


def gen_leaf_cert(level, signing_cert, signing_key, params={}, accurate=False):
    global certs

    if len(certs[level]['leafs']) > 0:
        sn = int(max(certs[level]['leafs'].keys())) + 1
    else:
        sn = 11

    params['CN'] = "Leaf cert signed by intermediate with SN: {}".format(get_serial_number(signing_cert))
    params['SN'] = sn

    leafkey = createKeyPair()
    leafcert = gen_cert(leafkey, signing_cert, signing_key, params)

    certs[level]['leafs'][sn] = (leafcert, leafkey, accurate)
    return leafcert, leafkey

'''
    Level1 -> Expired cert
    Level2 -> Untrusted CA
    Not implemented
        Level3 -> Problem with Intermediate (revocation)  
        Level4 -> Problem with Intermediate (not a signing authority)
'''
def init_certs(level):
    global certs

    if 0 not in certs: # make sure CA is init no matter what level we start with
        cacert, cakey = gen_ca()
        certs = {0: {'ca': { 0: (cacert, cakey) } } }

    if level != 0 and 0 in certs: # make sure we use the same CA no matter what level we are on
        certs[level] = {'ca': { 0: (certs[0]['ca'][0][0], certs[0]['ca'][0][1]) } } 
        cacert, cakey = certs[0]['ca'][0]

    if level == 2:
        cacert, cakey = gen_ca(params={'SN': 1, 'gen_new': True})
        certs[level]['ca'][1] = (cacert, cakey)

    certs[level]['intermediates'] = {}
    certs[level]['leafs'] = {}
    
    extensions = [ ("keyUsage", True, "keyCertSign, cRLSign, digitalSignature") ]
    params = { 'extensions': extensions }

    # Create intermediate certs
    for i in xrange(0, 10):

        if level == 2:
            if i == 3: # actually sn #4 since we start at 0
                gen_intermediate(level, certs[level]['ca'][0][0], certs[level]['ca'][0][1], params)
            else: # Don't use trusted CA to sign most level 2 intermediate certs
                gen_intermediate(level, certs[level]['ca'][1][0], certs[level]['ca'][1][1], params)

        # elif level == 3: TODO placeholder to call cert revocation here, but not i == 9
            
        elif level == 4:
            if i == 7:
                gen_intermediate(level, cacert, cakey, params)
            else: # Don't allow signing for most level 4 intermeidate certs
                gen_intermediate(level, cacert, cakey, {})
                
        else: # by default use a trusted ca, and include signing extension
            gen_intermediate(level, cacert, cakey, params)

    # Create leaf certs - 2 per intermediate
    for int_sn in certs[level]['intermediates'].keys(): 
        intcert, intkey = certs[level]['intermediates'][int_sn]

        if level == 0: 
            if int_sn == 9:
                gen_leaf_cert(level, intcert, intkey, {}, accurate=True)
            else:
                gen_leaf_cert(level, intcert, intkey, {}, accurate=False)
            gen_leaf_cert(level, intcert, intkey, {}, accurate=False)

        elif level == 1:
            if int_sn == 2: 
                gen_leaf_cert(level, intcert, intkey, {}, accurate=True)
                gen_leaf_cert(level, intcert, intkey, {}, accurate=True)
            else: # Use expired leafs for most level 1 certs
                params = {'not_before_offset': -1 * 60 * 60 * 24 * 60, 'not_after_offset': -1 * 60 * 60 * 24 * 30}
                gen_leaf_cert(level, intcert, intkey, params, accurate=False)
                gen_leaf_cert(level, intcert, intkey, params, accurate=False)

        elif level == 2: 
            if int_sn == 4:
                gen_leaf_cert(level, intcert, intkey, {}, accurate=True)
                gen_leaf_cert(level, intcert, intkey, {}, accurate=True)
            else:
                gen_leaf_cert(level, intcert, intkey, {}, accurate=False)
                gen_leaf_cert(level, intcert, intkey, {}, accurate=False)

        elif level == 3:
            if int_sn == 5: 
                gen_leaf_cert(level, intcert, intkey, {}, accurate=True)
                gen_leaf_cert(level, intcert, intkey, {}, accurate=True)
            else:
                gen_leaf_cert(level, intcert, intkey, {}, accurate=False)
                gen_leaf_cert(level, intcert, intkey, {}, accurate=False)

        elif level == 4:
            if int_sn == 7: # Provide accurate hints if level4 and int_sn is 4
                gen_leaf_cert(level, intcert, intkey, {}, accurate=True)
                gen_leaf_cert(level, intcert, intkey, {}, accurate=True)
            else:
                gen_leaf_cert(level, intcert, intkey, {}, accurate=False)
                gen_leaf_cert(level, intcert, intkey, {}, accurate=False)


def get_cert_by_sn(params):
    global certs
    global database
    
    if 'ID' not in params or 'SN' not in params:
        return json.dumps({'Results': "incorrect parameters received"})
    
    ID = params['ID'][0]
    if ID not in database:
        return json.dumps({"Error": "ID {} not found in database, have you already played that game?".format(ID)})

    level = int(database[params['ID'][0]]['level'])
    SN = int(params['SN'][0])

    if SN > 30 or SN < 0: # Magic numbers
        return json.dumps({'Results': "Cert SN should be in the range 0-30"})

    if SN in certs[level]['intermediates']:
        return json.dumps({'text': certText(certs[level]['intermediates'][SN][0]),
                           'pem': certPEM(certs[level]['intermediates'][SN][0]) })

    return json.dumps({'Results': "Cert SN not found. Are you sure you used an intermediate cert SN?"})


def sign_hint(signing_key, hint):
    signature = crypto.sign(signing_key, hint, 'sha256')
    return signature


def get_hint(params):
    global database
    global certs

    if 'ID' not in params or 'level' not in params:
        return json.dumps({'Results': "incorrect parameters received"})

    try:
        level = int(params['level'][0])
    except ValueError as e:
        return json.dumps({'Results': "Level parameter must be an int"})
        
    ID = params['ID'][0]
    if ID not in database:
        return json.dumps({"Error": "ID {} not found in database, have you already played that game?".format(ID)})
    
    cert_sn = randint(11, 30) # Magic numbers
    selected_leaf_cert, selected_leaf_key, accurate = certs[level]['leafs'][cert_sn]

    if level == 0:
        hint = "The number rhymes with {}".format(database[ID]['pick'])
        signature = base64.b16encode(sign_hint(selected_leaf_key, hint)) # always sign accurate hint

        if not accurate: # change hint to ensure sig is invalid
            hint = "The number rhymes with {}".format(randint(0,2**31-1)) # Magic numbers

        return json.dumps({"Hint": hint, 'Signature': signature, 'Signer': certText(selected_leaf_cert), 
                           'cert_pem': crypto.dump_certificate(crypto.FILETYPE_PEM, selected_leaf_cert).decode('utf-8') })

    elif level in [1, 2, 3, 4]:
#        for ca in certs[level]['ca']: # print out the ca's for debugging
#            print(certText(certs[level]['ca'][ca][0]))

        if accurate:
            hint = "The number rhymes with {}".format(database[ID]['pick'])
        else:
            hint = "The number rhymes with {}".format(randint(0,2**31-1)) # Magic numbers
        signature = base64.b16encode(sign_hint(selected_leaf_key, hint))
        return json.dumps({"Hint": hint, 'Signature': signature, 'Signer': certText(selected_leaf_cert), 
                           'cert_pem': crypto.dump_certificate(crypto.FILETYPE_PEM, selected_leaf_cert).decode('utf-8') })


def pick_number(bits):
    number = str(getrandbits(bits))
    return number


def compute_hash(value, salt=""):
    md = hashlib.md5()
    md.update(value + salt)
    digest = md.hexdigest()
    return digest


def init_game(level):
    global database

    # define salt
    ID = str(uuid.uuid4())
    time = datetime.now().strftime('%Y-%m-%d %H:%M')

    salt = "|" + str(ID) + "|" + str(uuid.uuid4()) # secure random salt

    num_bits = 31
    number = pick_number(num_bits)
    digest = compute_hash(number + salt)

    database[ID] = {'pick': number, 'salt': salt, 'hash': digest, 'level': level}

    description = "Welcome to level{}. Thanks for playing! Pick a number between 0 and {}".format(level, 2**num_bits - 1)
    response = {"ID": ID, "commitment": digest, 'description': description}

    return json.dumps(response)


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
        if path in ['level0', 'level1', 'level2', 'level3', 'level4']:
            message = init_game(path[-1])
        elif path in ['submit']:
            message = play_game(query)
        elif path in ['hint']:
            message = get_hint(query)
        elif path in ['get_cert']:
            message = get_cert_by_sn(query)
        elif path in ['get_crl']:
            message = get_crl(query)
        else:
            message = json.dumps({"Error": "Requested endpoint not found. Available endpoints: level0-4, submit, hint, get_cert, crl"})
        self.wfile.write(bytes(str(message) + "\n"))
        return
 
def run():
    print('starting server...')

    for level in [0, 1, 2]:
        init_certs(level)

    # Read our local IP from file
    with open('./server.config', 'r') as fh:
        try:
            ip = fh.readlines()[0]
        except Exception as e:
            print("error loading config file. {}".format(e))
            import sys
            sys.exit(1)

    server_address = (ip, 9502)
    httpd = HTTPServer(server_address, coinFlipHandler)
    print('running server...')
    httpd.serve_forever()
 
 
run()

