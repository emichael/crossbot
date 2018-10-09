import hashlib
import hmac
import json
import time

from datetime import date
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse

from crossbot.models import MiniCrosswordTime, CBUser
from crossbot.views import slash_command

# Create your tests here.

class ModelTests(TestCase):

    def test_something(self):
        pass


class SlackAppTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

        self.slack_sk = b'8f742231b10e8888abcd99yyyzzz85a5'

        self.patcher_sk = patch('keys.SLACK_SECRET_SIGNING_KEY', self.slack_sk)
        # Make the slack api return an object with always returns 'ok'
        self.patcher_slack = patch('crossbot.slack._slack_api', MagicMock('ok'))

        self.patcher_sk.start()
        self.patcher_slack.start()

    def tearDown(self):
        self.patcher_sk.stop()
        self.patcher_slack.stop()

    def post_valid_request(self, post_data):
        request = self.factory.post(reverse('slash_command'),
                                    post_data)
        ts = str(time.time())
        request.META['HTTP_X_SLACK_REQUEST_TIMESTAMP'] = ts
        request.META['HTTP_X_SLACK_SIGNATURE'] = 'v0=' + hmac.new(
            key=self.slack_sk,
            msg=b'v0:' + bytes(ts, 'utf8') + b':' + request.body,
            digestmod=hashlib.sha256
        ).hexdigest()
        return slash_command(request)


    def test_bad_signature(self):
        response = self.client.post(reverse('slash_command'),
                                    HTTP_X_SLACK_REQUEST_TIMESTAMP=str(time.time()),
                                    HTTP_X_SLACK_SIGNATURE=b'')
        self.assertEqual(response.status_code, 400)

    def test_add(self):
        response = self.post_valid_request({
            'type': 'event_callback',
            'text': 'add :10',
            'response_url': 'foobar',
            'trigger_id': 'foobar',
            'channel_id': 'foobar',
            'user_id': 'UALICE',
            'user_name': '@alice',
        })

        self.assertEqual(response.status_code, 200)

        alice = CBUser.objects.get(slackid='UALICE')

        self.assertEqual(len(alice.minicrosswordtime_set.all()), 1)
