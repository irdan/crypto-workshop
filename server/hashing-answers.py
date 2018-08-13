#!/usr/bin/env python
 
from datetime import datetime

import hashlib
import json
import requests


def init_game(level, matches=''):
    '''
    init_game returns a dict that contains:
        commitment: the hash value of the coin flip outcome
        ID: the uuid of the game that was just started
        description: The instructions for playing
    '''
    url = "http://127.0.0.1:8081/" + level
    params = dict(
        matches=matches
    )
    response = requests.get(url, params=params)
    if response.ok:
        return response.json()
 

def submit_answer(ID, answer):
    url = "http://127.0.0.1:8081/submit"
    params = dict(
        ID=ID,
        answer=answer
    )
    response = requests.get(url, params=params)
    if response.ok:
        return response.json()


def compute_hash(value, salt=""):
    md = hashlib.md5()
    md.update(value + salt)
    digest = md.hexdigest()
    return digest


#print("Welcome and thanks for playing! The time is {}".format(datetime.now().strftime('%Y-%m-%d %H:%M')))

def beat_level0():
    response = init_game("level0")
    print(json.dumps(response, indent=4))

    for i in xrange(0, 256):
        if response['commitment'] == compute_hash(str(i)):
            my_answer = str(i)
            break

    response = submit_answer(response['ID'], my_answer)
    print(json.dumps(response, indent=4))


def beat_level1():
    response = init_game("level1")
    print(json.dumps(response, indent=4))

    for i in xrange(0, 256):
        if response['commitment'] == compute_hash(str(i) + "|" + response['ID'] + "|" + response['time']):
            my_answer = str(i)
            break

    response = submit_answer(response['ID'], my_answer)
    print(json.dumps(response, indent=4))


def beat_level2():
    chars_to_match = 1
    response = init_game("level2", chars_to_match)
    print(json.dumps(response, indent=4))

    # this can be optimized much further by creating a large number of games to potentially compare against

    match = False
    number = 0
    while match is False:
        digest = compute_hash(str(number))
        if response['commitment'][0:chars_to_match] == digest[0:chars_to_match]:
            if response['commitment'][-chars_to_match:] == digest[-chars_to_match:]:
                match = True
                my_answer = str(number)
        number += 1

    print("submitting: {} as match to {}".format(compute_hash(my_answer), response['commitment'] ))
    response = submit_answer(response['ID'], my_answer)
    print(json.dumps(response, indent=4))

beat_level0()
beat_level1()
beat_level2()


