# Generated by Django 4.2.14 on 2025-07-09 04:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ImamFlex', '0006_imam_email_muazzin_email_siak_email'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaverequest',
            name='prayer_time',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
