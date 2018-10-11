import requests
import keys

from crossbot.models import CBUser

SLACK_URL = 'https://slack.com/api/'

def _slack_api(endpoint, method, **kwargs):
    assert method in ['GET', 'POST']
    headers = {'Authorization': 'Bearer ' + keys.SLACK_OAUTH_ACCESS_TOKEN}
    url = SLACK_URL + endpoint

    if method == 'GET':
        func = requests.get
    elif method == 'POST':
        func = requests.post
    else:
        raise ValueError('invalid method: ' + method)

    return func(url, headers=headers, params=kwargs)

def _slack_api_ok(endpoint, method, key, **kwargs):
    resp = _slack_api(endpoint, method, **kwargs).json()
    if resp.get('ok'):
        return resp[key]
    else:
        raise ValueError('bad response: ' + resp.get('error'))

def slack_users():
    return _slack_api_ok('users.list', 'GET', 'members')

def react(emoji, channel, timestamp):
    return _slack_api_ok('reactions.add', 'POST', 'ok', name=emoji, channel=channel, timestamp=timestamp)

def post_message(channel, **kwargs):
    return _slack_api_ok('chat.postMessage', 'POST', 'ts', channel=channel, **kwargs)


class SlackRequest:

    def __init__(self, post_data, in_channel=False):
        self.text = post_data['text']
        self.response_url = post_data['response_url']
        self.trigger_id = post_data['trigger_id']
        self.channel = post_data['channel_id']

        self.slackid = post_data['user_id']
        self.user = CBUser.from_slackid(slackid=post_data['user_id'],
                                        slackname=post_data['user_name'])

        self.in_channel = in_channel
        self.replies = []

    def reply(self, msg, direct=False):
        self.replies.append(msg)

    # note, this one is not delayed
    def message_and_react(self, msg, emoji):
        # TODO: add author and author_icon here?
        timestamp = post_message(self.channel, text=msg)
        react(emoji, self.channel, timestamp)

    def response_json(self):
        response = {
            'response_type': 'in_channel' if self.in_channel else 'ephemeral',
            'text': '\n'.join(self.replies)
        }

        if self.in_channel:
            response['author_name'] = str(self.user)

            if self.user.hat:
                response['author_icon'] = self.user.hat.url

        return response


# class SlackEventRequest:
#     def __init__(self, post_data, in_channel=False):
#         self.text = post_data['text']
#         self.timestamp = post_data['ts']
#         self.channel = post_data['channel']

#         self.slackid = post_data['user_id']
#         slackuser, created = crossbot.models.CBUser.objects.get_or_create(
#             slackid = post_data['user'],
#         )

#         self.user = slackuser.user

#         self.in_channel = in_channel

#     def reply(self, msg, direct=False):
#         post_message(self.channel, text = msg)

#     # note, this one is not delayed
#     def message_and_react(self, msg, emoji):
#         react(emoji, self.channel, self.timestamp)
