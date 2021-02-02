# Generated by Django 3.1.4 on 2021-02-01 22:51

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('RAR', '0018_auto_20210201_2158'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='customer_name',
            field=models.CharField(blank=True, max_length=36, null=True),
        ),
        migrations.AlterField(
            model_name='notifications',
            name='date',
            field=models.DateTimeField(default=datetime.datetime(2021, 2, 1, 22, 51, 1, 199177)),
        ),
    ]