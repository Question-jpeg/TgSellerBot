# Generated by Django 4.1.2 on 2022-10-16 20:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0020_alter_userinfo_chat_id_alter_userinfo_waiting_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userinfo',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='api.category'),
        ),
    ]
