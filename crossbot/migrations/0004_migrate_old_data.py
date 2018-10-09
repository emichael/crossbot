from django.conf import settings
from django.db import migrations, models
from django.contrib.auth import get_user_model
import django.db.models.deletion


TIME_MODELS = ['CrosswordTime', 'MiniCrosswordTime', 'EasySudokuTime']


def make_users(apps, schema_editor):
    CBUser = apps.get_model('crossbot', 'CBUser')

    for model_name in TIME_MODELS + ['QueryShorthands']:
        for item in apps.get_model('crossbot', model_name).objects.all():
            CBUser(slackid=item.userid, slackname='').save()

def transfer_times(apps, schema_editor):
    for model_name in TIME_MODELS:
        CBUser = apps.get_model('crossbot', 'CBUser')
        Temp = apps.get_model('crossbot', 'Temp' + model_name)
        for item in apps.get_model('crossbot', model_name).objects.all():
            Temp(
                user=CBUser.objects.get(slackid=item.userid),
                seconds=item.seconds,
                date=item.date,
                timestamp=item.timestamp,
            ).save()

def transfer_queries(apps, schema_editor):
    CBUser = apps.get_model('crossbot', 'CBUser')
    Temp = apps.get_model('crossbot', 'TempQueryShorthand')
    for item in apps.get_model('crossbot', 'QueryShorthands').objects.all():
        Temp(
            user=CBUser.objects.get(pk=item.userid),
            name=item.name,
            command=item.command,
            timestamp=item.timestamp,
        ).save()


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('crossbot', '0003_create_new_schema'),
    ]

    operations = [
        migrations.RunPython(make_users),
        migrations.RunPython(transfer_times),
        migrations.RunPython(transfer_queries),
    ] + [
        migrations.DeleteModel(model_name) for model_name in TIME_MODELS
    ] + [
        migrations.RenameModel('Temp' + model_name, model_name)
        for model_name in TIME_MODELS
    ] + [
        migrations.DeleteModel('QueryShorthands'),
        migrations.RenameModel('TempQueryShorthand', 'QueryShorthand'),
        migrations.RenameModel('ModelDates', 'ModelDate'),
        migrations.RenameModel('ModelUsers', 'ModelUser'),
        migrations.AlterModelOptions(
            name='minicrosswordmodel',
            options={'managed': False},
        ),
        migrations.AlterModelOptions(
            name='modeldate',
            options={'managed': False},
        ),
        migrations.AlterModelOptions(
            name='modeluser',
            options={'managed': False},
        ),
    ]
