# Generated by Django 4.2.16 on 2024-12-12 07:19

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('forum', '0006_userprofile_address_userprofile_wall'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserPostCount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_posts', models.PositiveIntegerField(default=0)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='post_count_profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
