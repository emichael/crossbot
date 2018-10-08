import hashlib
import hmac
import json
import time

from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse

from crossbot.models import MiniCrosswordTime, MyUser
from crossbot.views import event

# Create your tests here.

class ModelTests(TestCase):

    def test_something(self):
        alice = MyUser.objects.create_user('alice')
        bob = MyUser.objects.create_user('bob')
        charlie = MyUser.objects.create_user('charlie')

        self.assertEqual(len(MyUser.objects.all()), 3)

        MiniCrosswordTime.objects.bulk_create([
            MiniCrosswordTime(seconds=20, user=alice, date=date(2018, 5, 5))
        ])

        print(MiniCrosswordTime.objects.all())


        self.assertEqual(1, 1)


class SlackEventTests(TestCase):

    ############################################################################
    # Set up and tear down
    ############################################################################
    def setUp(self):
        self.factory = RequestFactory()

        self.slack_sk = b'8f742231b10e8888abcd99yyyzzz85a5'

        self.patcher_sk = patch('keys.SLACK_SECRET_SIGNING_KEY', self.slack_sk)

        self.patcher_sk.start()

    def tearDown(self):
        self.patcher_sk.stop()

    ############################################################################
    # Utils
    ############################################################################
    def post_valid_request(self, post_data):
        request = self.factory.post(reverse('event'),
                                    json.dumps(post_data),
                                    content_type='application/json')
        ts = str(time.time())
        request.META['HTTP_X_SLACK_REQUEST_TIMESTAMP'] = ts
        request.META['HTTP_X_SLACK_SIGNATURE'] = 'v0=' + hmac.new(
            key=self.slack_sk,
            msg=b'v0:' + bytes(ts, 'utf8') + b':' + request.body,
            digestmod=hashlib.sha256
        ).hexdigest()
        return event(request)

    ############################################################################
    # Tests
    ############################################################################
    def test_bad_signature(self):
        response = self.client.post(reverse('event'),
                                    HTTP_X_SLACK_REQUEST_TIMESTAMP=str(time.time()),
                                    HTTP_X_SLACK_SIGNATURE=b'')
        self.assertEqual(response.status_code, 400)

    def test_add(self):
        response = self.post_valid_request({
                'type': 'event_callback',
                'event': json.dumps({
                    'text': 'cb add :10'
                })
            })
