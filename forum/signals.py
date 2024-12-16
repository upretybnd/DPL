# signals.py
from django.contrib.auth import user_logged_in
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Thread, Reply, UserPostCount, UserProfile, UserVisitStreak


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

# Update post count when a thread is created
@receiver(post_save, sender=Thread)
def update_user_post_count_on_thread_create(sender, instance, created, **kwargs):
    if created:
        user_post_count, created = UserPostCount.objects.get_or_create(user=instance.author)
        user_post_count.update_total_count()

# Update post count when a reply is created
@receiver(post_save, sender=Reply)
def update_user_post_count_on_reply_create(sender, instance, created, **kwargs):
    if created:
        user_post_count, created = UserPostCount.objects.get_or_create(user=instance.author)
        user_post_count.update_total_count()

# Update post count when a thread is deleted
@receiver(post_delete, sender=Thread)
def update_user_post_count_on_thread_delete(sender, instance, **kwargs):
    user_post_count, created = UserPostCount.objects.get_or_create(user=instance.author)
    user_post_count.update_total_count()

# Update post count when a reply is deleted
@receiver(post_delete, sender=Reply)
def update_user_post_count_on_reply_delete(sender, instance, **kwargs):
    user_post_count, created = UserPostCount.objects.get_or_create(user=instance.author)
    user_post_count.update_total_count()

@receiver(post_save, sender=User)
def create_user_post_count(sender, instance, created, **kwargs):
    if created:
        UserPostCount.objects.create(user=instance)


@receiver(user_logged_in)
def update_user_streak(sender, request, user, **kwargs):
    # Fetch or create UserVisitStreak record
    user_streak, created = UserVisitStreak.objects.get_or_create(user=user)

    # Update the streak count
    user_streak.update_streak()
