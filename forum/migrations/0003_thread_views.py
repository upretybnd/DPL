# Generated by Django 4.2.16 on 2024-12-11 10:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forum', '0002_reply_likes'),
    ]

    operations = [
        migrations.AddField(
            model_name='thread',
            name='views',
            field=models.IntegerField(default=0),
        ),
    ]
