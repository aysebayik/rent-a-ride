# Generated by Django 3.1.4 on 2021-01-30 23:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('RAR', '0007_auto_20210110_1414'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reservation',
            name='carDealer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='RAR.cardealer'),
        ),
    ]
