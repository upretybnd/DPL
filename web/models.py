from django.utils import timezone
from django.db import models

from dpl.storage import private_storage

# Define a function to return the default value for the 'role' field
def get_default_role():
    return timezone.now().strftime('%Y-%m-%d %H:%M:%S')  # Format the current time as a string

class Carousel(models.Model):
    title = models.CharField(max_length=200)
    program_organized_by = models.CharField(max_length=200)
    image = models.ImageField(upload_to='banner_img/',blank=False, null=False)

    class Meta:
        verbose_name = "Landing page slide"
        verbose_name_plural = "Landing page slideshow (optional — replaces the hero images when added)"

    def __str__(self):
        return self.title


class HomePageMedia(models.Model):
    IMAGE_KEY_CHOICES = [
        ("hero_main", "Landing page — main hero image (large, portrait)"),
        ("hero_side", "Landing page — small side image (square)"),
        ("video_cover", "Landing page — video cover image (landscape)"),
        ("default_cover", "Default background photo — login/sign-up, social previews, and pages without their own photo"),
    ]

    key = models.CharField(max_length=50, choices=IMAGE_KEY_CHOICES, unique=True, verbose_name="position")
    image = models.ImageField(upload_to="homepage/")
    alt_text = models.CharField(max_length=255, blank=True, help_text="Describe the photo for screen readers and search engines.")

    class Meta:
        verbose_name = "Landing page image"
        verbose_name_plural = "Landing page images"

    def __str__(self):
        return self.get_key_display()


class AboutPage(models.Model):
    """Editable content of the About page. Only one row is used."""

    title = models.CharField(max_length=200, default="Empowering communities through education")
    lead = models.TextField(max_length=500, blank=True, help_text="Short intro under the title.")
    story = models.TextField(help_text="Main story. Separate paragraphs with a blank line.")
    image = models.ImageField(upload_to="about/", blank=True, help_text="Photo shown beside the figures.")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "About page"
        verbose_name_plural = "About page"

    def __str__(self):
        return "About page"

    @classmethod
    def load(cls):
        return cls.objects.prefetch_related("stats", "milestones", "pillars").first()

    def paragraphs(self):
        return [p.strip() for p in self.story.replace("\r\n", "\n").split("\n\n") if p.strip()]


class AboutStat(models.Model):
    page = models.ForeignKey(AboutPage, on_delete=models.CASCADE, related_name="stats")
    value = models.CharField(max_length=20, help_text="e.g. 15 or 18k+")
    label = models.CharField(max_length=80, help_text="e.g. chapters across Nepal")
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "figure"

    def __str__(self):
        return f"{self.value} {self.label}"


class AboutMilestone(models.Model):
    page = models.ForeignKey(AboutPage, on_delete=models.CASCADE, related_name="milestones")
    year = models.CharField(max_length=20, help_text="e.g. 2011 or Today")
    title = models.CharField(max_length=120)
    text = models.CharField(max_length=255, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "timeline entry"
        verbose_name_plural = "timeline"

    def __str__(self):
        return f"{self.year} — {self.title}"


class ContactMessage(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField(max_length=5000)
    is_handled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.subject or 'No subject'}"


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email


class Donation(models.Model):
    METHOD_CHOICES = [
        ("esewa", "eSewa"),
        ("khalti", "Khalti"),
        ("bank", "Bank transfer"),
    ]
    STATUS_PENDING = "pending"
    STATUS_VERIFIED = "verified"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending verification"),
        (STATUS_VERIFIED, "Verified"),
        (STATUS_REJECTED, "Rejected"),
    ]

    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    message = models.TextField(blank=True, max_length=2000)
    payment_proof = models.ImageField(upload_to="donation_proofs/", storage=private_storage, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} — NPR {self.amount}"


class AboutPillar(models.Model):
    page = models.ForeignKey(AboutPage, on_delete=models.CASCADE, related_name="pillars")
    icon = models.CharField(
        max_length=40, default="book-open",
        help_text='Icon name from lucide.dev/icons, e.g. "library", "users", "mic".',
    )
    title = models.CharField(max_length=80)
    text = models.CharField(max_length=255)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "'What we do' card"
        verbose_name_plural = "'What we do' cards"

    def __str__(self):
        return self.title
