"""Crossbot Django models."""

import datetime
import random

from copy import copy

import yaml

from django.contrib.auth.models import User
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.db import models, transaction
from django.db.models import Q
from solo.models import SingletonModel

from crossbot.settings import APP_SETTINGS


# TODO: switch from return codes to exceptions to help with transactions???
#       or, we can use set_rollback
#       https://stackoverflow.com/questions/39332010/django-how-to-rollback-transaction-atomic-without-raising-exception
class CBUser(models.Model):
    """Main user model used by the rest of the app."""
    class Meta:
        verbose_name = "CBUser"
        verbose_name_plural = "CBUsers"

    slackid = models.CharField(max_length=10, primary_key=True)
    slackname = models.CharField(max_length=100, blank=True)

    auth_user = models.OneToOneField(User, null=True, blank=True,
                                     on_delete=models.SET_NULL,
                                     related_name='cb_user')

    # TODO: since hats are items, should we make sure that users possess them?
    # Right now, someone could have a hat that they don't own (as an item).
    # Probably we want some way to "equip" an item that you own.
    #
    # That does open up some holes as to how to handle giving away your current
    # hat. Maybe you "give" it from your inventory to the hat slot? So equipped
    # items are not owned?
    hat = models.CharField(max_length=20, null=True, blank=True)
    crossbucks = models.IntegerField(default=0)

    @classmethod
    def from_slackid(cls, slackid, slackname=None, create=True):
        """Gets or creates the user with slackid, updating slackname.

        Returns:
            The CBUser if it exists or create=True, None otherwise.
        """
        if create and slackname:
            return cls.objects.update_or_create(
                slackid=slackid, defaults={'slackname': slackname})[0]
        if create:
            return cls.objects.get_or_create(slackid=slackid)[0]
        try:
            user = cls.objects.get(slackid=slackid)
            if slackname:
                user.slackname = slackname
                user.save()
            return user
        except cls.DoesNotExist:
            return None

    @classmethod
    def update_slacknames(cls):
        from crossbot.slack import slack_users

        users = {
            u['id']: u for u in slack_users()
        }

        for user in cls.objects.all():
            user.slackname = users[user.slackid]['name']
            user.save()


    def add_crossbucks(self, amount):
        """Add crossbucks to a user's account."""
        assert amount > 0

        # TODO: this doesn't actually give us consistency, even if we're
        #       operating in a transaction (I think) since we're operating on a
        #       stale version of the CBUser instance and this gets turned into a
        #       simple INSERT. Don't really know if we ever plan on running w/
        #       multiple threads, though. Other functions will have the same
        #       problem as this one.

        self.crossbucks += amount
        self.save()

    def remove_crossbucks(self, amount):
        """Add crossbucks to a user's account.

        Returns:
            Whether or not the crossbucks were deducted.
        """
        assert amount > 0

        if amount > self.crossbucks:
            return False
        self.crossbucks -= amount
        self.save()
        return True

    def give_crossbucks(self, other_user, amount):
        """Give crossbucks to another user.

        Returns:
            Whether or not the crossbucks were given.
        """
        assert isinstance(other_user, CBUser)
        assert amount > 0

        if not self.remove_crossbucks(amount):
            return False
        other_user.add_crossbucks(amount)
        return True

    def add_item(self, item, amount=1):
        """Add an item to this user's inventory.

        Args:
            item: An Item object.
            amount: An integer > 0.
        """
        assert isinstance(item, Item)
        assert amount > 0

        record, _ = ItemOwnershipRecord.objects.get_or_create(
            owner=self, item=item)
        record.quantity += amount
        record.save()

    def remove_item(self, item, amount=1):
        """Remove an item from this user's inventory.

        Args:
            item: The Item to remove.
            amount: An integer > 0.

        Returns:
            Whether or not the item was removed.
        """
        assert isinstance(item, Item)
        assert amount > 0

        try:
            record = ItemOwnershipRecord.objects.get(owner=self, item=item)
        except ItemOwnershipRecord.DoesNotExist:
            return False

        # Check to see if there are enough to safely delete
        if amount > (record.quantity + (1 if item == self.hat else 0)):
            return False

        record.quantity -= amount
        if record.quantity == 0:
            record.delete()
        else:
            record.save()
        return True

    def quantity_owned(self, item):
        """Return the amount of a given item this user owns."""
        assert isinstance(item, Item)
        try:
            return ItemOwnershipRecord.objects.get(
                owner=self, item=item).quantity
        except ItemOwnershipRecord.DoesNotExist:
            return 0

    def give_item(self, item, other_user, amount=1):
        """Give item(s) to another user.

        Args:
            item: The Item to give.
            other_user: A CBUser.
            amount: An integer > 0.

        Returns:
            Whether or not the items were sucessfully given.
        """
        assert isinstance(item, Item)
        assert isinstance(other_user, CBUser)
        assert amount > 0

        if not self.remove_item(item, amount):
            return False
        other_user.add_item(item, amount)
        return True

    def don(self, hat):
        """Put on a hat if the user owns at least one.

        Args:
            hat: A Hat.

        Returns:
            Whether or not the hat was sucessfully put on.
        """
        assert isinstance(hat, Item)
        assert hat.is_hat()

        if self.quantity_owned(hat) > 0:
            self.hat = hat
            self.save()
            return True
        return False

    def doff(self):
        """Take off hat.

        Returns:
            Whether you had a hat on in the first place.
        """
        if self.hat is not None:
            self.hat = None
            self.save()
            return True
        return False

    def get_time(self, time_model, date):
        """Get the time for this user for the given date.

        Args:
            time_model: Reference to the subclass of CommonTime to get.
            date: The date of the puzzle.

        Returns:
            An instance of time_model if it exists, None otherwise.
        """
        assert issubclass(time_model, CommonTime)
        assert isinstance(date, datetime.date)

        try:
            return time_model.objects.get(user=self, date=date,
                                          seconds__isnull=False)
        except time_model.DoesNotExist:
            return None

    # TODO: wrap this and other operations in transactions???
    def add_time(self, time_model, seconds, date):
        """Add a time for this user for the given date.

        Args:
            time_model: Reference to the subclass of CommonTime to add.
            seconds: An integer representing the seconds taken, -1 if user
                failed to solve.
            date: The date of the puzzle.

        Returns:
            A 4-tuple, (was_added, time, crossbucks_earned, item_dropped), where
            was_added denotes whether or not the time was successfully added,
            time is the instace of time_model for this user and date (the
            already existent one if was_added is False), crossbucks_earned is
            the number of crossbucks earned for this solve, and item_dropped is
            a reference to the Item object the user found (or None if there
            wasn't a drop).
        """
        assert issubclass(time_model, CommonTime)
        assert isinstance(seconds, int)
        assert isinstance(date, datetime.date)

        time = self.get_time(time_model, date)
        if time:
            return (False, time, 0, None)

        time, created = time_model.objects.update_or_create(
            user=self,
            date=date,
            defaults={'seconds': seconds,
                      'timestamp': datetime.datetime.now()})

        # Don't award prizes for fails or added-then-deleted entries
        if time.is_fail() or not created:
            crossbucks_earned = 0
            item = None
        else:
            crossbucks_earned = APP_SETTINGS['CROSSBUCKS_PER_SOLVE']
            crossbucks_earned += time_model.participation_streak_reward_diff(self, date)
            self.crossbucks += crossbucks_earned
            self.save()

            item = Item.choose_droppable()

            if item:
                self.add_item(item)

        # TODO question: should `crossbucks_earned` include the streak reward?
        return (True, time, crossbucks_earned, item)

    def remove_time(self, time_model, date):
        """Remove a time for this user.

        Removes a time record for this user. If the record is not a fail, does
        not delete the record entirely, to prevent people from cheating to get
        more crossbucks/items.

        Args:
            time_model: Reference to the subclass of CommonTime to remove.
            date: The date of the puzzle.
        """
        assert issubclass(time_model, CommonTime)
        assert isinstance(date, datetime.date)

        time = self.get_time(time_model, date)
        if time:
            if time.is_fail():
                time.delete()
            else:
                time.seconds = None
                time.save()

    def streaks(self, time_model, date):
        """Returns the full, forwards, and backwards streaks the user is on.

        Calculates the number of days in a row the user has completed a given
        puzzle, centered on a given date.

        Returns:
            (streak_length, old_streak_length, forwards_streak_length,
             backward_streak_length)
        """

        dates_completed = set(
            time_model.objects.filter(user=self).values_list('date', flat=True))

        # calculate the backwards streak
        check_date = copy(date) # why is this copied? Does -= change value?
        backward_streak_count = 0
        while check_date in dates_completed:
            backward_streak_count += 1
            check_date -= datetime.timedelta(days=1)

        # calculate the forwards streak
        check_date = copy(date)
        forward_streak_count = 0
        while check_date in dates_completed:
            forward_streak_count += 1
            check_date += datetime.timedelta(days=1)

        streak_count = forward_streak_count + backward_streak_count
        # Don't double-count date
        if streak_count > 0:
            streak_count -= 1

        old_streak_count = max(backward_streak_count, forward_streak_count)
        # Don't count date in the old_streak_count
        if old_streak_count > 0:
            old_streak_count -= 1

        return (streak_count, old_streak_count,
                forward_streak_count, backward_streak_count)

    def get_mini_crossword_time(self, *args, **kwargs):
        return self.get_time(MiniCrosswordTime, *args, **kwargs)

    def get_crossword_time(self, *args, **kwargs):
        return self.get_time(CrosswordTime, *args, **kwargs)

    def get_easy_sudoku_time(self, *args, **kwargs):
        return self.get_time(EasySudokuTime, *args, **kwargs)

    def add_mini_crossword_time(self, *args, **kwargs):
        return self.add_time(MiniCrosswordTime, *args, **kwargs)

    def add_crossword_time(self, *args, **kwargs):
        return self.add_time(CrosswordTime, *args, **kwargs)

    def add_easy_sudoku_time(self, *args, **kwargs):
        return self.add_time(EasySudokuTime, *args, **kwargs)

    def remove_mini_crossword_time(self, *args, **kwargs):
        return self.remove_time(MiniCrosswordTime, *args, **kwargs)

    def remove_crossword_time(self, *args, **kwargs):
        return self.remove_time(CrosswordTime, *args, **kwargs)

    def remove_easy_sudoku_time(self, *args, **kwargs):
        return self.remove_time(EasySudokuTime, *args, **kwargs)

    def __str__(self):
        return str(self.slackname if self.slackname else self.slackid)


class StreakReward:
    def __init__(self, *, length, messages):
        self.length = length
        self.messages = messages

    def crossbucks_reward(self):
        return self.length * APP_SETTINGS['CROSSBUCKS_PER_SOLVE'] * 0.5


STREAK_REWARDS = {
    # StreakReward(length = 1, messages = [
    #     ["First one in a while, {name}.",
    #      "Try it every day, ({name})." ]
    # ]),
    StreakReward(length = 3, messages = [
        "3 entries in a row! Keep it up {name}!",
        "Nice work, 3 in a row!"
    ]),
    StreakReward(length = 10, messages = [
        "{name}'s on a streak of 10 entries, way to go!"
    ]),
    StreakReward(length = 25, messages = [
        ":open_mouth:, 25 days in a row!"
    ]),
    StreakReward(length = 50, messages = [
        "50 in a row, here's a medal :sports_medal:!"
    ]),
    StreakReward(length = 100, messages = [
        ":100::100::100: {name}'s done 100 crosswords in a row! :100::100::100:"
    ]),
    StreakReward(length = 150, messages = [
        "{name}'s on a streak of 150 days... impressive!"
    ]),
    StreakReward(length = 200, messages = [
        ":two::zero::zero: days in a row!?! Wow! Great work {name}!"
    ]),
    StreakReward(length = 300, messages = [
        "Congrats {name} for doing 300 crosswords in a row!"
    ]),
    StreakReward(length = 365, messages = [
        "Whoa, {name} just finished a full *year of crosswords*! Congratulations! :calendar::partypopper:"
    ]),
    StreakReward(length = 500, messages = [
        "{name} just completed their 500th in a row! :partypopper:"
    ]),
}

def calculate_streak_rewards(streaks):

    total_reward = 0

    for streak in streaks:
        for reward in STREAK_REWARDS:
            if len(streak) >= reward.length:
                total_reward += reward.crossbucks_reward()

    return total_reward

class CommonTime(models.Model):
    class Meta:
        unique_together = ("user", "date")
        abstract = True

    user = models.ForeignKey(CBUser, on_delete=models.CASCADE)
    seconds = models.IntegerField(null=True)
    date = models.DateField()
    timestamp = models.DateTimeField(null=True, auto_now_add=True)

    @classmethod
    def non_null(cls):
        """Return a query set with non-null times (i.e., non-deleted)."""
        return cls.objects.filter(seconds__isnull=False)

    def is_fail(self):
        return self.seconds < 0

    def time_str(self):
        if self.is_fail():
            return 'fail'

        minutes, seconds = divmod(self.seconds, 60)

        return '{}:{:02}'.format(minutes, seconds)

    def __str__(self):
        return '{} - {} - {}'.format(self.user, self.time_str(), self.date)

    @staticmethod
    def streaks(qs):
        """Takes a query set times and returns the streaks clumped together."""

        streaks = []
        current_streak = []

        one_day = datetime.timedelta(days=1)

        for entry in qs.order_by('date'):
            if not current_streak or entry.date == current_streak[-1].date + one_day:
                # either there wasn't a streak so we should start one, or we maintained a streak
                current_streak.append(entry)
            else:
                # we broke it, create a new one
                streaks.append(current_streak)
                current_streak = [entry]

        if current_streak:
            streaks.append(current_streak)

        return streaks

    @classmethod
    def participation_streak_reward_diff(cls, user, *dates):
        """Calculates the reward that a user should be given for
        particular date (or list of dates) that is *already in* the database """

        streaks1 = cls.participation_streak(user)
        rewards1 = calculate_streak_rewards(streaks1)

        streaks2 = cls.participation_streak(user, filter_q=~Q(date__in=dates))
        rewards2 = calculate_streak_rewards(streaks2)

        assert rewards1 >= rewards2

        return rewards1 - rewards2

    @classmethod
    def participation_streak(cls, user, filter_q=None):
        times = cls.objects.filter(seconds__isnull=False, user_id=user)
        if filter_q:
            times = times.filter(filter_q)

        return cls.streaks(times)


class MiniCrosswordTime(CommonTime):
    pass

class CrosswordTime(CommonTime):
    pass

class EasySudokuTime(CommonTime):
    pass


class MiniCrosswordModel(models.Model):
    class Meta:
        managed = False
        db_table = 'mini_crossword_model'
        unique_together = (('userid', 'date'),)

    userid = models.TextField()
    date = models.IntegerField()
    prediction = models.IntegerField()
    residual = models.FloatField()

class ModelUser(models.Model):
    class Meta:
        managed = False
        db_table = 'model_users'

    uid = models.TextField(unique=True)
    nth = models.IntegerField()
    skill = models.FloatField()
    skill_25 = models.FloatField()
    skill_75 = models.FloatField()

class ModelDate(models.Model):
    class Meta:
        managed = False
        db_table = 'model_dates'

    date = models.IntegerField()
    difficulty = models.FloatField()
    difficulty_25 = models.FloatField()
    difficulty_75 = models.FloatField()

class ModelParams(models.Model):
    class Meta:
        managed = False
        db_table = 'model_params'
        verbose_name_plural = "ModelParams"

    time = models.FloatField()
    time_25 = models.FloatField()
    time_75 = models.FloatField()
    satmult = models.FloatField()
    satmult_25 = models.FloatField()
    satmult_75 = models.FloatField()
    bgain = models.FloatField()
    bgain_25 = models.FloatField()
    bgain_75 = models.FloatField()
    bdecay = models.FloatField()
    bdecay_25 = models.FloatField()
    bdecay_75 = models.FloatField()
    skill_dev = models.FloatField()
    date_dev = models.FloatField()
    sigma = models.FloatField()
    lp = models.FloatField()
    when_run = models.FloatField()


class QueryShorthand(models.Model):
    user = models.ForeignKey(CBUser, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=100)
    command = models.TextField()
    timestamp = models.DateTimeField(null=True)

    def __str__(self):
        return '{} - {}'.format(self.name, self.user)


class ItemOwnershipRecord(models.Model):
    class Meta:
        unique_together = (('owner', 'item'),)

    owner = models.ForeignKey(CBUser, models.CASCADE)
    item = models.CharField(max_length=20)
    quantity = models.IntegerField(default=0)


################################################################################
# Items are stored in YAML (not the DB) but loaded here for convenience
################################################################################

class Item:
    ITEMS = {}

    def __init__(self, key, options):
        self.key = key
        self.name = options['name']
        # use setattr and defaults in getter methods?
        self.droppable = options.get('droppable', True)
        self.image_name = options.get('image_name', None)
        self.rarity = options.get('rarity', 1.0)
        self.type = options.get('type', None)

    @classmethod
    def load_items(cls):
        with open('crossbot/items.yaml') as f:
            for key, options in yaml.load(f).items():
                cls.ITEMS[key] = Item(key, options)

    @classmethod
    def from_key(cls, key):
        return cls.ITEMS.get(key, None)

    @classmethod
    def choose_droppable(cls):
        """Drop a randomly chosen Item from this class, or None.

        First, selects whether or not to drop a randomly chosen Item based on
        the global drop rate, then selects from all droppable items weighted by
        their rarity.

        Does not create an ownership record.

        Returns:
            An Item or None.
        """

        if random.random() > APP_SETTINGS['ITEM_DROP_RATE']:
            return None

        print('blarg', cls.ITEMS)

        droppables = [item for item in cls.ITEMS.values() if item.droppable]

        if not droppables:
            return None

        return random.choices(droppables,
                              [item.rarity for item in droppables])[0]

    def image_url(self):
        if not self.image_name:
            return None
        return static('img/itemimages/%s' % self.image_name)

    def is_hat(self):
        return self.type == 'hat'

    def __str__(self):
        return self.name

# Load all the items into memory
Item.load_items()
