# Generated by Django 4.2.16 on 2024-12-11 15:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('forum', '0004_thread_last_reply'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='category',
            name='slug',
        ),
    ]
