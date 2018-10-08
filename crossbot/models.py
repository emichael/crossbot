"""Crossbot Django models."""

from django.contrib.auth.models import User
from django.db import models


class _CBAuthUser(User):
    """Simple proxy to underlying auth users."""
    class Meta:
        proxy = True

    def __str__(self):
        try:
            return str(self.cb_user) # pylint: disable=no-member
        except CBUser.DoesNotExist:
            return str(self.username)

class CBUser(models.Model):
    """Main user model used by the rest of the app."""
    slackid = models.CharField(max_length=10, primary_key=True)
    slackname = models.CharField(max_length=100, blank=True)

    auth_user = models.OneToOneField(_CBAuthUser, null=True,
                                     on_delete=models.SET_NULL,
                                     related_name='cb_user')

    hat = models.ForeignKey('Hat', null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return str(self.slackname if self.slackname else self.slackid)


class CommonTime(models.Model):
    user = models.ForeignKey(CBUser, on_delete=models.CASCADE)
    seconds = models.IntegerField()
    date = models.DateField()
    timestamp = models.DateTimeField(null=True, auto_now_add=True)

    class Meta:
        unique_together = ("user", "date")
        abstract = True

    def time_str(self):
        if self.seconds < 0:
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


class QueryShorthands(models.Model):
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
    rarity = models.IntegerField()

class Hat(Item):
    pass

class Crate(Item):
    pass

class Key(Item):
    pass

class ItemOwnership(models.Model):
    owner = models.ForeignKey(CBUser, models.CASCADE)
    item = models.ForeignKey(Item, models.CASCADE)
    quantity = models.IntegerField()
