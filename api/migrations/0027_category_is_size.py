# Generated by Django 4.1.2 on 2022-10-18 17:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0026_productcreationcache'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='is_size',
            field=models.BooleanField(default=False),
        ),
    ]
