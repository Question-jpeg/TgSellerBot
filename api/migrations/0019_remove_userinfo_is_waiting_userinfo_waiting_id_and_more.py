# Generated by Django 4.1.2 on 2022-10-16 07:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0018_userinfo_is_waiting'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userinfo',
            name='is_waiting',
        ),
        migrations.AddField(
            model_name='userinfo',
            name='waiting_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='userinfo',
            name='chat_id',
            field=models.CharField(max_length=255),
        ),
    ]
