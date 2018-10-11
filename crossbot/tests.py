import hashlib
import hmac
import json
import time

from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse

from crossbot import date
from crossbot.models import CrossbotSettings, CBUser, Hat
from crossbot.settings import CROSSBUCKS_PER_SOLVE
from crossbot.views import slash_command

# Create your tests here.

class PatchingTestCase(TestCase):
    def patch(self, *args, **kwargs):
        patcher = patch(*args, **kwargs)
        patcher.start()
        self.addCleanup(patcher.stop)
        return patcher

class ModelTests(TestCase):

    def test_add_user(self):
        alice = CBUser.from_slackid('UALICE', 'alice')
        self.assertIsInstance(alice, CBUser)
        self.assertEqual(alice, CBUser.from_slackid('UALICE', 'bob'))
        alice = CBUser.from_slackid('UALICE')
        self.assertEqual(CBUser.from_slackid('UALICE').slackname, 'bob')

    def test_add_time(self):
        alice = CBUser.from_slackid('UALICE', 'alice')
        self.assertEqual(alice.crossbucks, 0)

        a, t, cb, i = alice.add_mini_crossword_time(10, date(None))
        self.assertTrue(a)
        self.assertEqual(t.user, alice)
        self.assertEqual(t.seconds, 10)
        self.assertEqual(t.date, date(None))
        self.assertEqual(cb, CROSSBUCKS_PER_SOLVE)
        self.assertEqual(alice.crossbucks, cb)

        self.assertEqual(alice.get_mini_crossword_time(date(None)), t)

    def test_add_remove_time(self):
        alice = CBUser.from_slackid('UALICE', 'alice')
        self.assertEqual(alice.crossbucks, 0)

        alice.add_mini_crossword_time(10, date(None))
        self.assertEqual(alice.crossbucks, CROSSBUCKS_PER_SOLVE)

        alice.remove_mini_crossword_time(date(None))
        self.assertEqual(alice.crossbucks, CROSSBUCKS_PER_SOLVE)
        self.assertEqual(alice.get_mini_crossword_time(date(None)), None)

        a, t, cb, i = alice.add_mini_crossword_time(10, date(None))
        self.assertTrue(a)
        self.assertEqual(t.user, alice)
        self.assertEqual(t.seconds, 10)
        self.assertEqual(t.date, date(None))
        self.assertEqual(cb, 0)
        self.assertEqual(i, None)
        self.assertEqual(alice.crossbucks, CROSSBUCKS_PER_SOLVE)
        self.assertNotEqual(alice.get_mini_crossword_time(date(None)), None)

    def test_add_fail(self):
        alice = CBUser.from_slackid('UALICE', 'alice')
        a, t, cb, i = alice.add_mini_crossword_time(-1, date(None))
        self.assertTrue(a)
        self.assertEqual(t.seconds, -1)
        self.assertEqual(t.date, date(None))
        self.assertTrue(t.is_fail())
        self.assertEqual(cb, 0)
        self.assertEqual(i, None)

class SlackAppTests(PatchingTestCase):

    def setUp(self):
        self.factory = RequestFactory()

        self.slack_sk = b'8f742231b10e8888abcd99yyyzzz85a5'

        self.patch('keys.SLACK_SECRET_SIGNING_KEY', self.slack_sk)
        # Make the slack api return an object with always returns 'ok'
        self.patch('crossbot.slack._slack_api', MagicMock('ok'))

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

    def slack_post(self, text, who='alice'):

        return self.post_valid_request({
            'type': 'event_callback',
            'text': text,
            'response_url': 'foobar',
            'trigger_id': 'foobar',
            'channel_id': 'foobar',
            'user_id': 'U' + who.upper(),
            'user_name': '@' + who,
        })

    def test_add(self):

        response = self.slack_post(text='add :10')

        self.assertEqual(response.status_code, 200)

        body = json.loads(response.content)
        self.assertEqual(body['response_type'], 'ephemeral')

        alice = CBUser.objects.get(slackid='UALICE')

        self.assertEqual(len(alice.minicrosswordtime_set.all()), 1)

    def test_double_add(self):

        # two adds on the same day should trigger an error
        response = self.slack_post(text='add :10 2018-08-01')
        response = self.slack_post(text='add :11 2018-08-01')

        self.assertEqual(response.status_code, 200)

        body = json.loads(response.content)
        self.assertEqual(body['response_type'], 'ephemeral')

        # make sure the error message refers to the previous time
        self.assertIn(':10', body['text'])

        alice = CBUser.objects.get(slackid='UALICE')

        # make sure both times didn't get submitted
        times = alice.minicrosswordtime_set.all()
        self.assertEqual(len(times), 1)

        # make sure the original time was preserved
        self.assertEqual(times[0].seconds, 10)

    def test_times(self):
        self.slack_post('add :15 2018-08-01', who='alice')
        self.slack_post('add :40 2018-08-01', who='bob')

        # check date parsing here too
        response = self.slack_post('times 2018-8-1')
        body = json.loads(response.content)

        self.assertEqual(body['response_type'], 'ephemeral')

        lines = body['text'].split('\n')

        # line 0 is date, line 1 should be alice
        self.assertIn('alice', lines[1])
        self.assertIn(':fire:', lines[1])

    def test_hat(self):
        # First, make sure there's a droppable hat
        hat = Hat.objects.create(name="foohat")

        # Crank up the droprate to 100%
        settings = CrossbotSettings.get_solo()
        settings.item_drop_rate = 1.0
        settings.save()

        # Alice must find a foohat
        response = self.slack_post('add :15 2018-08-01', who='alice')
        self.assertIn("foohat", json.loads(response.content)['text'])

        # Alice can put it on
        response = self.slack_post('hat foohat', who='alice')
        self.assertIn("donned", json.loads(response.content)['text'])
