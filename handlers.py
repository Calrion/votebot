import boto3
import os
import time
import urllib
from collections import defaultdict
from functools import wraps
from slacker import Slacker

with open(os.path.join(os.path.dirname(__file__), 'SLACK_BOT_API_TOKEN')) as f:
    bot_api_token = f.read().strip()
with open(os.path.join(os.path.dirname(__file__), 'SLACK_CHANNEL_TOKEN')) as f:
    incoming_token = f.read().strip()

slack = Slacker(bot_api_token)
ddb = boto3.resource('dynamodb', region_name='us-west-2')

datestr = '%m/%d/%Y-%H:%M:%S'
table_vote_options = 'vote-options'
table_vote_open = 'vote-open'
delimiter = ','
command_handlers = {}


class AlreadyRegisteredException(Exception):
    """ Except which is thrown when a handler is registered which matches the name of an
    already registered handler.
    """
    pass


def handler(command):
    """ A handler corresponds to a command for votebot in Slack. Ex: 'votebot open foo'.
    Here, we have defined a function open() which is registered for the 'open' text
    for this example. The name of the function does not need to match, but when using
    the @handler decorator, the text of the command parameter must match the text in Slack.
    Handlers may return a dictionary which contain a 'text' key with a message to display
    in Slack as its value. See https://api.slack.com/outgoing-webhooks for more information.
    """
    @wraps(handler)
    def decorator(func):
        if not callable(func):
            raise TypeError('expected a callable')
        if command in command_handlers:
            raise AlreadyRegisteredException('{} is already a registered command'.format(type))
        command_handlers[command] = func
        return func
    return decorator


@handler(command='ping')
def ping():
    """ Responds to 'ping' with a 'pong' response.
    """
    return {
        'text': 'pong',
    }


@handler(command='help')
def help():
    """ Responses with the commands supported by votebot.
    """
    return {
        'text': 'You can use the following commands: {}'.format(' , '.join(command_handlers)),
    }


@handler(command='list')
def list(params):
    """ Reads the table containing the types of votes which can be opened and displays it back to the user.
    """
    ltable = ddb.Table(table_vote_options)
    list_res = ltable.scan()
    listed = []
    for i in list_res['Items']:
        listed.append(i['selection'])
    thelist = 'The following votes can be cast: {}'.format(' , '.join(listed))
    slack.chat.post_message(channel=_channel_name(params), text=thelist, as_user=True)


@handler(command='open')
def open(params, text):
    """ Opens voting for an option configured in the voting options table. The vote is recorded in the
    open votes table.
    """
    retval = {}
    selection = text[2]
    table = ddb.Table(table_vote_options)
    get_result = table.get_item(Key={'selection': selection})
    if 'Item' not in get_result:
        retval['text'] = '{} is not a valid selection'.format(selection)
    else:
        item = get_result['Item']
        print('retrieved item for vote: {}'.format(item))
        icon_emoji = item.get('icon_emoji', 'ballot_box_with_check')
        print('using icon_emoji {}'.format(icon_emoji))
        vote_id = '-'.join([selection, time.strftime(datestr)])  # Voting is open
        slack_text = '<!here> {} has opened voting for `{}`. Please vote by clicking on an emoji! ' \
                     'To close voting, please enter `votebot close {}`'.format(_requesting_user(params), selection, vote_id),
        resp = slack.chat.post_message(channel=_channel_name(params), text=slack_text, as_user=True)

        # For each option, write a message and make a reaction emoji
        timestamps = []
        for option in item['options'].split(delimiter):
            opt_resp = slack.chat.post_message(channel=_channel_name(params), text=option.strip(), as_user=True)
            timestamps.append(opt_resp.body['ts'])
            slack.reactions.add(name=icon_emoji, channel=opt_resp.body['channel'], timestamp=opt_resp.body['ts'])
            time.sleep(.5)  # Try not to get throttled by Slack

        # Now write the open vote to vote-open table
        print('writing vote {}'.format(vote_id))
        open_votes_table = ddb.Table(table_vote_open)
        open_votes_table.put_item(Item={
            'vote': vote_id,
            'line_timestamps': delimiter.join(timestamps),
            'channel': resp.body['channel'],
        })
    return retval


@handler(command='close')
def close(params, text):
    """ Closes an open vote located in the open votes table.
    """
    retval = {}
    vote_id = urllib.unquote(text[2])
    print('looking up vote id {}'.format(vote_id))
    table = ddb.Table(table_vote_open)
    get_result = table.get_item(Key={'vote': vote_id})
    if 'Item' not in get_result:
        print('{} not found'.format(vote_id))
        retval['text'] = '{} is not an open vote'.format(vote_id)
    else:
        print('{} found'.format(vote_id))
        item = get_result['Item']
        votes_from_slack = defaultdict(list)
        total = 0
        for ts in item['line_timestamps'].split(delimiter):
            resp = slack.reactions.get(channel=item['channel'], timestamp=ts)
            tally = -1  # Remove votebot's "vote"
            for reaction in resp.body['message']['reactions']:
                text = resp.body['message']['text']
                tally += reaction['count']
            votes_from_slack[tally].append(text.partition('/')[0].strip())  # Uses convention of name / desc1 / desc2
            total += tally
        slack_text = '<!here> {} closed voting for {}! Results:\n```'.format(_requesting_user(params), vote_id)
        for k in sorted(votes_from_slack.keys(), reverse=True):
            slack_text += '{} vote(s) each for {}\n'.format(k, ', '.join(votes_from_slack[k]))
        slack_text += 'Total votes: {}\n'.format(total)
        slack_text += '```'
        slack.chat.post_message(channel=_channel_name(params), text=slack_text, as_user=True)

        # Remove the open vote from the table
        table.delete_item(Key={'vote': vote_id})
    return retval


def _channel_name(params):
    """ Returns the channel name with a hash in front of it which is how Slack expects it.
    """
    return '#{}'.format(params['channel_name'])


def _requesting_user(params):
    """ Returns the user name from the list of parameters.
    """
    return params['user_name']
