# Generated by Django 4.2.16 on 2024-12-11 05:25

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('forum', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='reply',
            name='likes',
            field=models.ManyToManyField(blank=True, related_name='liked_replies', to=settings.AUTH_USER_MODEL),
        ),
    ]
