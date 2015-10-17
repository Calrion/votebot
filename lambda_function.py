import boto3
import os
import time
import urllib
from collections import defaultdict
from slacker import Slacker

datestr = '%m/%d/%Y-%H:%M:%S'
table_vote_options = 'vote-options'
table_vote_open = 'vote-open'
delimiter = ','

with open(os.path.join(os.path.dirname(__file__), 'SLACK_BOT_API_TOKEN')) as f:
    bot_api_token = f.read().strip()
with open(os.path.join(os.path.dirname(__file__), 'SLACK_CHANNEL_TOKEN')) as f:
    incoming_token = f.read().strip()

slack = Slacker(bot_api_token)
ddb = boto3.resource('dynamodb', region_name='us-west-2')


def _formparams_to_dict(s1):
    """ Converts the incoming formparams from Slack into a dictionary. Ex: 'text=votebot+ping' """
    retval = {}
    for val in s1.split('&'):
        k, v = val.split('=')
        retval[k] = v
    return retval


def lambda_handler(event, context):
    """ This is the function Lambda will call. Supported commands:
    - ping: Immediately responds back with a 'pong' message.
    - open: Opens voting for a particular item as configured in Dynamo.
    - close: Closes an open vote.
    """
    param_map = _formparams_to_dict(event['formparams'])
    text = param_map['text'].split('+')
    requesting_user = param_map['user_name']
    channel_name = '#{}'.format(param_map['channel_name'])
    retval = {}

    if param_map['token'] != incoming_token:  # Check for a valid Slack token
        retval['text'] = 'invalid incoming Slack token'

    elif 'ping' == text[1]:
        retval['text'] = 'pong'

    elif 'help' == text[1]:
        retval['text'] = 'You can use the following commands: help , ping , list , open , close.'

    elif 'list' == text[1]:
        ltable = ddb.Table(table_vote_options)
        list_res = ltable.scan()
        listed = []
        for i in list_res['Items']:
              listed.append(i['selection'])
        thelist = "The following votes can be cast: "
        thelist += " , ".join(listed)
        slack.chat.post_message(channel=channel_name, text=thelist, as_user=True)

    elif 'open' == text[1]:
        try:
            selection = text[2]
            table = ddb.Table(table_vote_options)
            res = table.get_item(Key={'selection': selection})
            if 'Item' not in res:
                retval['text'] = '{} not a valid selection'.format(selection)
            else:
                item = res['Item']
                options = item['options']
                icon_emoji = item.get('icon_emoji', 'ballot_box_with_check')
                # Voting is open!
                vote_id = '-'.join([selection, time.strftime(datestr)])
                slack_text = '<!here> {} has opened voting for `{}`. Please vote by clicking on an emoji! ' \
                             'To close voting, please enter `votebot close {}`'.format(requesting_user, selection, vote_id),
                resp = slack.chat.post_message(channel=channel_name, text=slack_text, as_user=True)

                if not resp.body['ok']:
                    retval['text'] = 'Response from Slack was not ok'
                else:
                    # For each option, write a message and make a reaction emoji
                    timestamps = []
                    for option in options.split(delimiter):
                        opt_resp = slack.chat.post_message(channel=channel_name, text=option.lstrip(), as_user=True)
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
        except Exception as e:
            retval['text'] = 'Error: {}'.format(str(e))

    elif 'close' == text[1]:
        try:
            vote_id = urllib.unquote(text[2])
            print('looking up vote id {}'.format(vote_id))
            table = ddb.Table(table_vote_open)
            res = table.get_item(Key={'vote': vote_id})
            if 'Item' not in res:
                retval['text'] = '{} is not an open vote'.format(vote_id)
            else:
                item = res['Item']
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
                slack_text = '<!here> {} closed voting for {}! Results:\n```'.format(requesting_user, vote_id)
                for k in sorted(votes_from_slack.keys(), reverse=True):
                    slack_text += '{} vote(s) each for {}\n'.format(k, ', '.join(votes_from_slack[k]))
                slack_text += 'Total votes: {}\n'.format(total)
                slack_text += '```'
                slack.chat.post_message(channel=channel_name, text=slack_text, as_user=True)

                # Remove the open vote from the table
                table.delete_item(Key={'vote': vote_id})
        except Exception as e:
            retval['text'] = 'Error: {}'.format(str(e))
    else:
        retval['text'] = 'unknown command'

    return retval
