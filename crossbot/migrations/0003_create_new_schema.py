from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('crossbot', '0002_fix_old_schema'),
    ]

    operations = [
        migrations.CreateModel(
            name='ModelDate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.IntegerField()),
                ('difficulty', models.FloatField()),
                ('difficulty_25', models.FloatField()),
                ('difficulty_75', models.FloatField()),
            ],
            options={
                'db_table': 'model_dates',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='ModelUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uid', models.TextField(unique=True)),
                ('nth', models.IntegerField()),
                ('skill', models.FloatField()),
                ('skill_25', models.FloatField()),
                ('skill_75', models.FloatField()),
            ],
            options={
                'db_table': 'model_users',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='CBUser',
            fields=[
                ('slackid', models.CharField(max_length=10, primary_key=True, serialize=False)),
                ('slackname', models.CharField(blank=True, max_length=100)),
                ('auth_user', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cb_user', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'CBUser',
                'verbose_name_plural': 'CBUsers',
            },
        ),
        migrations.CreateModel(
            name='CrossbotSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_drop_rate', models.FloatField(default=0.1)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Item',
            fields=[
                ('name', models.CharField(max_length=100, primary_key=True, serialize=False)),
                ('emoji_str', models.CharField(max_length=100)),
                ('droppable', models.BooleanField(default=True)),
                ('rarity', models.FloatField(default=1.0)),
            ],
        ),
        migrations.CreateModel(
            name='ItemOwnershipRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='TempQueryShorthand',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('command', models.TextField()),
                ('timestamp', models.DateTimeField(null=True)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='crossbot.CBUser')),
            ],
        ),
        migrations.CreateModel(
            name='TempCrosswordTime',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('seconds', models.IntegerField()),
                ('date', models.DateField()),
                ('timestamp', models.DateTimeField(auto_now_add=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crossbot.CBUser')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TempEasySudokuTime',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('seconds', models.IntegerField()),
                ('date', models.DateField()),
                ('timestamp', models.DateTimeField(auto_now_add=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crossbot.CBUser')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TempMiniCrosswordTime',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('seconds', models.IntegerField()),
                ('date', models.DateField()),
                ('timestamp', models.DateTimeField(auto_now_add=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crossbot.CBUser')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterModelOptions(
            name='modelparams',
            options={'managed': False, 'verbose_name_plural': 'ModelParams'},
        ),
        migrations.CreateModel(
            name='Hat',
            fields=[
                ('item_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='crossbot.Item')),
            ],
            bases=('crossbot.item',),
        ),
        migrations.AddField(
            model_name='itemownershiprecord',
            name='item',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crossbot.Item'),
        ),
        migrations.AddField(
            model_name='itemownershiprecord',
            name='owner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crossbot.CBUser'),
        ),
        migrations.AlterUniqueTogether(
            name='tempminicrosswordtime',
            unique_together={('user', 'date')},
        ),
        migrations.AlterUniqueTogether(
            name='tempeasysudokutime',
            unique_together={('user', 'date')},
        ),
        migrations.AlterUniqueTogether(
            name='tempcrosswordtime',
            unique_together={('user', 'date')},
        ),
        migrations.AlterUniqueTogether(
            name='itemownershiprecord',
            unique_together={('owner', 'item')},
        ),
        migrations.AddField(
            model_name='cbuser',
            name='hat',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='crossbot.Hat'),
        ),
    ]
