# Generated by Django 4.1.2 on 2022-10-16 07:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0019_remove_userinfo_is_waiting_userinfo_waiting_id_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userinfo',
            name='chat_id',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='userinfo',
            name='waiting_id',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
