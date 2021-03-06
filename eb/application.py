from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from urllib.request import urlopen
from boto.s3.key import Key
import boto.s3
import json
import tweepy

application = Flask(__name__)

@application.route('/test', methods=['GET', 'POST'])
def test():
    return 'test'


@application.route('/receive_text', methods=['GET', 'POST'])
def receiveText():
    try:
        fromNumber = request.values.get('From')
        msgText = request.values.get('Body')

        if fromNumber is None or msgText is None:
            return str(MessagingResponse().message('Error: Malformed message.'))

        words = msgText.split()

        if len(words) < 2:
            return str(MessagingResponse().message(
                'Your message must include both an action and a twitter handle.'))

        action = words[0].upper()
        handle = words[1].upper()

        if action not in ('FOLLOW', 'UNFOLLOW'):
            return str(MessagingResponse().message(
                'Your action must be either "Follow" or "Unfollow". Your action was "%s".' % action))
        elif not handleExists(handle):
            return str(MessagingResponse().message('Could not find the twitter handle "%s"' % handle))

        handleToPhones = downloadUsersJson()
        phones = handleToPhones.get(handle, [])

        if action == 'FOLLOW' and fromNumber not in phones:
            phones.append(fromNumber)
        elif action == 'UNFOLLOW' and fromNumber in phones:
            phones.remove(fromNumber)

        if phones:
            handleToPhones[handle] = phones
        else:
            del handleToPhones[handle]

        uploadUsersJson(handleToPhones)

        return str(MessagingResponse().message("You have %sed %s" % (action.lower(), handle)))
    except Exception as e:
        return str(MessagingResponse().message(str(e)))

def handleExists(handle):
    with open('auth.json') as f:
        authInfo = json.loads(f.read())

    auth = tweepy.OAuthHandler(authInfo['twitter_api_key'], authInfo['twitter_api_secret'])
    auth.set_access_token(authInfo['twiter_access_token'], authInfo['twitter_access_secret'])
    api = tweepy.API(auth)

    try:
        api.get_user(handle)
        return True
    except tweepy.error.TweepError:
        return False

def downloadUsersJson():
    return json.loads(urlopen('https://s3.amazonaws.com/twinty/users.json').read().decode())

def uploadUsersJson(jsonDict):
    bucket = boto.connect_s3('<redacted>', '<redacted>') \
                    .get_bucket('twinty')

    tmp = json.dumps(jsonDict)
    kOld = Key(bucket)
    kNew = Key(bucket)
    kOld.key = 'users.json'
    bucket.delete_key(kOld)
    kNew.key = 'users.json'
    kNew.content_type = 'application/json'
    kNew.set_contents_from_string(tmp)
    kNew.set_acl('public-read')


if __name__ == '__main__':
    # with open('auth.json') as f:
    #     authInfo = json.loads(f.read())
    
    # client = Client(authInfo['twilio_acct_sid'], authInfo['twilio_auth_token'])
    client = Client('<redacted>', '<redacted>')

    # aws info
    # conn = boto.connect_s3(authInfo['aws_access_key'], authInfo['aws_secret_key'])

    application.debug = True
    application.run()
