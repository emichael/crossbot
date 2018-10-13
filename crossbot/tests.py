import hashlib
import hmac
import json
import time

from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse

from crossbot import date
from crossbot.models import CBUser, Item, MiniCrosswordTime
import crossbot.models
from crossbot.settings import APP_SETTINGS
from crossbot.views import slash_command

# Create your tests here.

class PatchingTestCase(TestCase):
    def patch(self, *args, **kwargs):
        patcher = patch(*args, **kwargs)
        patcher.start()
        self.addCleanup(patcher.stop)
        return patcher

    def patch_app_settings(self, key, value):
        old_value = APP_SETTINGS[key]
        def cleanup():
            APP_SETTINGS[key] = old_value
        APP_SETTINGS[key] = value
        self.addCleanup(cleanup)

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
        self.assertEqual(cb, APP_SETTINGS['CROSSBUCKS_PER_SOLVE'])
        self.assertEqual(alice.crossbucks, cb)

        self.assertEqual(alice.get_mini_crossword_time(date(None)), t)

    def test_add_remove_time(self):
        alice = CBUser.from_slackid('UALICE', 'alice')
        self.assertEqual(alice.crossbucks, 0)

        alice.add_mini_crossword_time(10, date(None))
        self.assertEqual(alice.crossbucks, APP_SETTINGS['CROSSBUCKS_PER_SOLVE'])

        alice.remove_mini_crossword_time(date(None))
        self.assertEqual(alice.crossbucks, APP_SETTINGS['CROSSBUCKS_PER_SOLVE'])
        self.assertEqual(alice.get_mini_crossword_time(date(None)), None)

        a, t, cb, i = alice.add_mini_crossword_time(10, date(None))
        self.assertTrue(a)
        self.assertEqual(t.user, alice)
        self.assertEqual(t.seconds, 10)
        self.assertEqual(t.date, date(None))
        self.assertEqual(cb, 0)
        self.assertEqual(i, None)
        self.assertEqual(alice.crossbucks, APP_SETTINGS['CROSSBUCKS_PER_SOLVE'])
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

    def test_streak(self):
        alice = CBUser.from_slackid('UALICE', 'alice')

        # preload the reward amounts
        rs = crossbot.models.STREAK_REWARDS
        (reward3,) = (r.crossbucks_reward() for r in rs if r.length == 3)
        (reward10,) = (r.crossbucks_reward() for r in rs if r.length == 10)

        # set up a broken 10 streak
        _, t1, _, _ = alice.add_mini_crossword_time(18, date('2018-01-01'))
        _, t2, _, _ = alice.add_mini_crossword_time(12, date('2018-01-02'))
        _, t3, _, _ = alice.add_mini_crossword_time(12, date('2018-01-03'))
        _, t4, _, _ = alice.add_mini_crossword_time(15, date('2018-01-04'))
        # t5 is missing
        _, t6, _, _ = alice.add_mini_crossword_time(15, date('2018-01-06'))
        _, t7, _, _ = alice.add_mini_crossword_time(15, date('2018-01-07'))
        _, t8, _, _ = alice.add_mini_crossword_time(15, date('2018-01-08'))
        _, t9, _, _ = alice.add_mini_crossword_time(15, date('2018-01-09'))
        _, t0, _, _ = alice.add_mini_crossword_time(18, date('2018-01-10'))

        # make sure the streak is broken
        streaks = MiniCrosswordTime.participation_streak(alice)
        self.assertListEqual(
            streaks,
            [[t1, t2, t3, t4], [t6, t7, t8, t9, t0]]
        )

        # make sure alice's money is the streak bonuses + the solve bonuses
        self.assertEqual(alice.crossbucks, 2 * reward3 + APP_SETTINGS['CROSSBUCKS_PER_SOLVE'] * 9)

        # fix the broken streak
        _, t5, _, _ = alice.add_mini_crossword_time(15, date('2018-01-05'))

        streaks = MiniCrosswordTime.participation_streak(alice)
        self.assertListEqual(
            streaks,
            [[t1, t2, t3, t4, t5, t6, t7, t8, t9, t0]]
        )

        # make sure the reward diff is correct
        diff = MiniCrosswordTime.participation_streak_reward_diff(alice, t5.date)
        new_rewards = reward3 + reward10
        old_rewards = 2 * reward3
        self.assertEquals(diff, new_rewards - old_rewards)

        # make sure alice's money is the streak bonuses + the solve bonuses
        # without double counting reward3
        self.assertEqual(alice.crossbucks, reward10 + reward3 + APP_SETTINGS['CROSSBUCKS_PER_SOLVE'] * 10)

        # now break it again with a deleted time (t2)
        alice.remove_mini_crossword_time(date('2018-01-02'))
        streaks = MiniCrosswordTime.participation_streak(alice)
        self.assertListEqual(
            streaks,
            [[t1], [t3, t4, t5, t6, t7, t8, t9, t0]]
        )


class SlackAppTests(PatchingTestCase):

    def setUp(self):
        self.factory = RequestFactory()

        self.slack_sk = b'8f742231b10e8888abcd99yyyzzz85a5'

        self.patch('keys.SLACK_SECRET_SIGNING_KEY', self.slack_sk)
        # Make the slack api return an object with always returns 'ok'
        self.patch('crossbot.slack._slack_api', MagicMock('ok'))

        self.patch_app_settings('ITEM_DROP_RATE', 1.0)

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

    def slack_post(self, text, who='alice', expected_status_code = 200, expected_response_type='ephemeral'):

        response = self.post_valid_request({
            'type': 'event_callback',
            'text': text,
            'response_url': 'foobar',
            'trigger_id': 'foobar',
            'channel_id': 'foobar',
            'user_id': 'U' + who.upper(),
            'user_name': '@' + who,
        })

        self.assertEqual(response.status_code, expected_status_code)

        body = json.loads(response.content)
        self.assertEqual(body['response_type'], expected_response_type)

        return body

    def test_add(self):

        self.slack_post(text='add :10')

        alice = CBUser.objects.get(slackid='UALICE')

        self.assertEqual(len(alice.minicrosswordtime_set.all()), 1)

    def test_double_add(self):

        # two adds on the same day should trigger an error
        self.slack_post(text='add :10 2018-08-01')
        response = self.slack_post(text='add :11 2018-08-01')

        # make sure the error message refers to the previous time
        self.assertIn(':10', response['text'])

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

        lines = response['text'].split('\n')

        # line 0 is date, line 1 should be alice
        self.assertIn('alice', lines[1])
        self.assertIn(':fire:', lines[1])

    def test_hat(self):
        # TODO: don't use tophat, add a hat to item set for stability

        # Alice must find a foohat
        response = self.slack_post('add :15 2018-08-01', who='alice')
        self.assertIn("Tophat", response['text'])

        # Alice can put it on
        response = self.slack_post('hat tophat', who='alice')
        self.assertIn("donned", response['text'])

        # Bob can't
        response = self.slack_post('hat tophat', who='bob')
        self.assertNotIn("donned", response['text'])
