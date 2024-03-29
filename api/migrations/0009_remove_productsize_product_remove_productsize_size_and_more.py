# Generated by Django 4.1.2 on 2022-10-13 20:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_categorysize'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='productsize',
            name='product',
        ),
        migrations.RemoveField(
            model_name='productsize',
            name='size',
        ),
        migrations.AddField(
            model_name='product',
            name='size',
            field=models.CharField(default=1, max_length=5),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='userinfo',
            name='size',
            field=models.CharField(blank=True, max_length=5, null=True),
        ),
        migrations.DeleteModel(
            name='CategorySize',
        ),
        migrations.DeleteModel(
            name='ProductSize',
        ),
        migrations.DeleteModel(
            name='Size',
        ),
    ]
