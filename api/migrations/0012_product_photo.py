# Generated by Django 4.1.2 on 2022-10-14 13:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_alter_product_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='photo',
            field=models.ImageField(default='none', upload_to='products'),
            preserve_default=False,
        ),
    ]
