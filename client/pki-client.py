#!/usr/bin/env python
 
from datetime import datetime
from yaml import load
from OpenSSL import crypto

import hashlib
import json
import requests
import base64
import types
 


with open('./server.yaml', 'r') as fh:
    try:
        config = load(fh)
    except Exception as e:
        print("error loading config file. {}".format(e))
        import sys
        sys.exit(1)


def init_game(level):
    '''
    init_game returns a dict that contains:
        commitment: the hash value of the coin flip outcome
        ID: the uuid of the game that was just started
        description: The instructions for playing
    '''
    url = "http://{}:{}/{}".format(config['ip'], config['port2'], level)
    response = requests.get(url)
    if response.ok:
        return response.json()


def submit_answer(ID, answer):
    '''
    submit_answer returns a dict that contains:
        Game_ID: the UUID of the game
        Results: the outcome of your answer
        proof: The proof the server is honest
    '''
    url = "http://{}:{}/submit".format(config['ip'], config['port2'])
    params = dict(
        ID=ID,
        answer=answer
    )
    response = requests.get(url, params=params)
    if response.ok:
        return response.json()


def get_hint(ID, level):
    '''
    get_hint returns a dict that contains:
        Signer: The certficate of the party that signed your cert.  Used to assess the truthfulness of the hint.
        Hint: The hint of which number the answer might be.
        Signature: The signature produced by signing the hint with the signer private key
    '''
    url = "http://{}:{}/hint".format(config['ip'], config['port2'])
    params = dict(
        ID=ID,
        level=level
    )
    response = requests.get(url, params=params)
    if response.ok:
        return response.json()


def get_intermediate_cert_by_sn(ID, SN, level):
    '''
    get_cert_by_sn returns a dict that contains:
        text: The certficate associated with the SN that was provided
        pem: The certificate in pem format
    '''
    url = "http://{}:{}/get_cert".format(config['ip'], config['port2'])
    params = dict(
        ID=ID,
        SN=SN
    )
    response = requests.get(url, params=params)
    if response.ok:
        return response.json()


def validate_hint_signature(hint):

    content = hint['Hint']
    signature = base64.b16decode(hint['Signature'])
    cert = crypto.load_certificate(crypto.FILETYPE_PEM, hint['cert_pem'])

    try:
        outcome = crypto.verify(cert, signature, content, 'sha256') 
        if outcome is None:
            return True
        return False
    except Exception as e:
        return False


def extract_times_from_cert(certText):
    certLines = certText.split("\n")
    not_after = ""
    not_before = ""

    for line in certLines:
        if "Not After" in line:
            not_after = line[line.find(":")+1:].strip()
        elif "Not Before" in line:
            not_before = line[line.find(":")+1:].strip()
        elif not_after != "" and not_before != "":
            break
    if not_after == "" or not_before == "":
        print("Unable to extract dates from cert")
    return not_before, not_after


def valid_time(certText):

    not_before, not_after = extract_times_from_cert(certText)

    begin = datetime.strptime(not_before, "%b %d %H:%M:%S %Y %Z")
    end = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
    now = datetime.now()

    if now >= begin and now <= end:
        return True

    return False


def verify_certificate_signature(certificate, root=None):

    if root is None:
        with open("CA.cert", 'r') as fh:
            root = crypto.load_certificate(crypto.FILETYPE_PEM, fh.read())

    if isinstance(certificate, types.UnicodeType): # then convert to X509
        certificate = crypto.load_certificate(crypto.FILETYPE_PEM, certificate)

    store = crypto.X509Store()
    store.add_cert(root)
    store.add_cert(certificate)
    store_context = crypto.X509StoreContext(store, certificate)
    try: 
        if store_context.verify_certificate() is None:
            return True
        return False
    except Exception as e:
        return False


def get_intermdiate_sn_of_cert(certText):
    lines = certText.split("\n")
    for line in lines:
        if "Leaf cert signed by intermediate" in line:
            sn = line.split(":")[2].strip().split(" ")[0]
            return sn


def beat_level0():
    level = 0
    response = init_game("level" + str(level))
    print(json.dumps(response, indent=4))

    hint = get_hint(response['ID'], level)
    print(json.dumps(hint, indent=4))

    # your code goes here
    my_answer = hint['Hint'][23:]

    print(json.dumps(submit_answer(response['ID'], my_answer), indent=4))


def beat_level1():
    level = 1
    response = init_game("level" + str(level))
    print(json.dumps(response, indent=4))

    hint = get_hint(response['ID'], level)
    print(json.dumps(hint, indent=4))

    # your code goes here
    my_answer = hint['Hint'][23:]

    print(json.dumps(submit_answer(response['ID'], my_answer), indent=4))


def beat_level2():
    level = 2
    response = init_game("level" + str(level))
    print(json.dumps(response, indent=4))

    hint = get_hint(response['ID'], level)
    print(json.dumps(hint, indent=4))

    #your code goes here
    my_answer = hint['Hint'][23:]

    print(json.dumps(submit_answer(response['ID'], my_answer), indent=4))


beat_level0()
#beat_level1()
#beat_level2()
