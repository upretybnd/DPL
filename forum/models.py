from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse


# Category Model
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)


    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("category_threads", kwargs={"slug": self.slug})


class Thread(models.Model):
    title = models.CharField(max_length=255)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="threads")
    content = models.TextField()
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name="threads")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    view_count = models.PositiveIntegerField(default=0)
    likes = models.ManyToManyField(User, related_name="liked_threads", blank=True)
    views = models.IntegerField(default=0)
    last_reply = models.ForeignKey('Reply', on_delete=models.SET_NULL, null=True, blank=True, related_name="last_replied_thread")

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("thread_detail", kwargs={"thread_pk": self.pk})

    def total_likes(self):
        return self.likes.count()

    def get_last_reply_username(self):
        if self.last_reply:
            return self.last_reply.author.username
        return "No replies yet"



# Reply Model
class Reply(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="replies")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="replies")
    content = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name="child_replies")
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name="liked_replies", blank=True)
    updated_at = models.DateTimeField(auto_now=True)


    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)



    def __str__(self):
        return f"Reply by {self.author} on {self.thread.title}"

    def total_likes(self):
        return self.likes.count()



# UserProfile Model
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=255, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to="profile_pictures/", blank=True, null=True)
    gender = models.CharField(max_length=10, choices=[("Male", "Male"), ("Female", "Female"), ("Other", "Other")],
                              blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    wall = models.TextField(blank=True, null=True)
    custom_title = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def get_title_based_on_post_count(self):
        """Returns the title based on the post count from UserPostCount."""
        # Fetch the post count from UserPostCount
        try:
            post_count = self.user.userpostcount.total_count
        except UserPostCount.DoesNotExist:
            post_count = 0  # Default to 0 if no UserPostCount record exists

        # Check if the user is a superuser
        if self.user.is_superuser:
            return '<span class="text-danger">Admin</span>'

        titles = [
            ((0, 10), 'Newbie', 'text-muted'),
            ((11, 50), 'Beginner', 'text-primary'),
            ((51, 100), 'Intermediate', 'text-info'),
            ((101, 200), 'Senior Member', 'text-success'),
            ((201, 500), 'Advanced', 'text-warning'),
            ((501, 1000), 'Expert', 'text-danger'),
            ((1001, 2000), 'Dazzler', 'text-dark'),
            ((2001, 5000), 'Viewbie', 'text-light'),
            ((5001, 10000), 'Master', 'text-secondary'),
            ((10001, 20000), 'Grandmaster', 'text-success'),
        ]

        for (min_count, max_count), title, color in titles:
            if min_count <= post_count <= max_count:
                return f'<span class="{color}">{title}</span>'

        return 'Member'  # Default title

    def update_custom_title(self):
        """Updates the custom title based on the UserPostCount."""
        self.custom_title = self.get_title_based_on_post_count()
        self.save()


# Wall Posts (Optional Feature for User Profiles)
class WallPost(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wall_posts")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wall_posts_received")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Wall Post by {self.author} to {self.receiver}"

# models.py


class UserPostCount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_count = models.PositiveIntegerField(default=0)

    def update_total_count(self):
        # Count threads and replies
        self.total_count = self.user.threads.count() + self.user.replies.count()  # Corrected to use 'replies'
        self.save()

class UserVisitStreak(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    last_login_date = models.DateField(null=True, blank=True)
    visit_streak = models.PositiveIntegerField(default=0)

    def update_streak(self):
        # Get today's date
        today = timezone.now().date()

        if self.last_login_date is None:
            # First time login or if no record exists
            self.visit_streak = 1
        else:
            # Check if the last login was the previous day
            if self.last_login_date == today - timezone.timedelta(days=1):
                self.visit_streak += 1
            else:
                self.visit_streak = 1  # reset streak if there is a break

        # Update last login date to today
        self.last_login_date = today
        self.save()