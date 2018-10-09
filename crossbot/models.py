"""Crossbot Django models."""

import datetime
import random

from django.contrib.auth.models import User
from django.db import models
from solo.models import SingletonModel

from crossbot.settings import CROSSBUCKS_PER_SOLVE


class CrossbotSettings(SingletonModel):
    """Crossbot settings, editable through the admin interface."""
    item_drop_rate = models.FloatField(default=0.1)


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

    hat = models.ForeignKey('Hat', null=True, blank=True,
                            on_delete=models.SET_NULL)
    crossbucks = models.IntegerField(default=0)

    @classmethod
    def from_slackid(cls, slackid, slackname=None):
        """Gets or creates the user with slackid, updating slackname."""
        if slackname:
            return cls.objects.update_or_create(
                slackid=slackid, defaults={'slackname': slackname})[0]
        return cls.objects.get_or_create(slackid=slackid)[0]

    def add_crossbucks(self, amount):
        """Add crossbucks to a user's account."""
        self.crossbucks += amount
        self.save()

    def add_item(self, item, amount=1):
        """Add an item to this user's inventory.

        Args:
            item: An Item object.
            amount: An integer.
        """
        assert isinstance(item, Item)

        record, _ = ItemOwnershipRecord.objects.get_or_create(
            owner=self, item=item)
        record.quantity += amount
        record.save()

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
            crossbucks_earned = CROSSBUCKS_PER_SOLVE
            self.crossbucks += crossbucks_earned
            self.save()

            item = Item.choose_droppable()

            if item:
                self.add_item(item)

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


class CommonTime(models.Model):
    class Meta:
        unique_together = ("user", "date")
        abstract = True

    user = models.ForeignKey(CBUser, on_delete=models.CASCADE)
    seconds = models.IntegerField(null=True)
    date = models.DateField()
    timestamp = models.DateTimeField(null=True, auto_now_add=True)

    def is_fail(self):
        return self.seconds < 0

    def time_str(self):
        if self.is_fail():
            return 'fail'

        minutes, seconds = divmod(self.seconds, 60)

        return '{}:{:02}'.format(minutes, seconds)

    def __str__(self):
        return '{} - {} - {}'.format(self.user, self.time_str(), self.date)


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


class Item(models.Model):
    name = models.CharField(max_length=100, primary_key=True)
    emoji_str = models.CharField(max_length=100)
    droppable = models.BooleanField(default=True)
    rarity = models.FloatField(default=1.0)

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
        if random.random() > CrossbotSettings.get_solo().item_drop_rate:
            return None

        droppables = cls.objects.filter(droppable=True)

        if not droppables.exists():
            return None

        return random.choices(droppables, [item.rarity for item in droppables])

    def __str__(self):
        return self.name

class Hat(Item):
    pass

class ItemOwnershipRecord(models.Model):
    class Meta:
        unique_together = (('owner', 'item'),)

    owner = models.ForeignKey(CBUser, models.CASCADE)
    item = models.ForeignKey(Item, models.CASCADE)
    quantity = models.IntegerField(default=0)
