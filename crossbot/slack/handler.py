import traceback

from . import commands
from .parser import Parser
from .api import *


class Request:
    userid = 'command-line-user'

    def __init__(self, text):
        self.text = text

    def react(self, emoji):
        print('react :{}:'.format(emoji))

    def reply(self, msg, direct=False):
        prefix = '@user - ' if direct else ''
        print(prefix + msg)

    def upload(self, name, path):
        print(path)


class Handler:
    def __init__(self, limit_commands=False):
        self.parser = Parser(limit_commands)
        self.init_plugins()

    def init_plugins(self):
        for mod_name in commands.__all__:
            try:
                mod = getattr(commands, mod_name)

                # hopefully the plugins will add themselves to subparsers
                if hasattr(mod, 'init'):
                    mod.init(self)
                else:
                    print('WARNING: plugin "{}" has no init()'.format(mod.__name__))
            except:
                print('ERROR: Something went wrong when importing "{}"'.format(mod_name))
                traceback.print_exc()

    def handle_request(self, request, parse=True):
        """ Parses the request and calls the right command.

        If parsing fails, this raises crossbot.parser.ParserException.
        """

        if parse:
            command, args = self.parser.parse(request.text)
            request.args = args
        else:
            command = request.command

        return command(request)


class SlashCommandRequest:

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
        timestamp = post_message(self.channel, text=msg)
        react(emoji, self.channel, timestamp)

    def response_json(self):
        return {
            'response_type': 'in_channel' if self.in_channel else 'ephemeral',
            'text': '\n'.join(self.replies)
        }
