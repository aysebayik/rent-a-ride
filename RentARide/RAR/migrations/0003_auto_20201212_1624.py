# Generated by Django 3.1.4 on 2020-12-12 13:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('RAR', '0002_admin_user'),
    ]

    operations = [
        migrations.CreateModel(
            name='Branch',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('branch_name', models.CharField(default='', max_length=100)),
                ('branch_location', models.TextField()),
            ],
        ),
        migrations.AlterField(
            model_name='reservation',
            name='carID',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='RAR.car'),
        ),
        migrations.AlterField(
            model_name='reservation',
            name='customerID',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='RAR.user'),
        ),
        migrations.AlterField(
            model_name='car',
            name='branchId',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='RAR.branch'),
        ),
    ]