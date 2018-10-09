"""Crossbot Django models."""

from django.contrib.auth.models import User
from django.db import models
from solo.models import SingletonModel


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

    auth_user = models.OneToOneField(User, null=True,
                                     on_delete=models.SET_NULL,
                                     related_name='cb_user')

    hat = models.ForeignKey('Hat', null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return str(self.slackname if self.slackname else self.slackid)


class CommonTime(models.Model):
    class Meta:
        unique_together = ("user", "date")
        abstract = True

    user = models.ForeignKey(CBUser, on_delete=models.CASCADE)
    seconds = models.IntegerField()
    date = models.DateField()
    timestamp = models.DateTimeField(null=True, auto_now_add=True)

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
    rarity = models.IntegerField()

class Hat(Item):
    pass

class ItemOwnershipRecord(models.Model):
    owner = models.ForeignKey(CBUser, models.CASCADE)
    item = models.ForeignKey(Item, models.CASCADE)
    quantity = models.IntegerField()
