# Generated by Django 3.1.4 on 2021-02-01 17:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('RAR', '0015_auto_20210131_0000'),
    ]

    operations = [
        migrations.AddField(
            model_name='branch',
            name='rank',
            field=models.IntegerField(default=0),
        ),
    ]
