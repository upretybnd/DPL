from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class BranchQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def chapters(self):
        return self.active().filter(branch_type=ParentBranch.TYPE_CHAPTER)

    def boards(self):
        return self.active().filter(branch_type__in=ParentBranch.BOARD_TYPES)

    def about_menu(self):
        return self.active().filter(in_about_menu=True)


class ParentBranch(models.Model):
    TYPE_CHAPTER = "chapter"
    TYPE_TEENS = "teens"
    TYPE_NATIONAL_BOARD = "national_board"
    TYPE_SENATE = "senate"
    TYPE_ORGANISATION = "organisation"
    TYPE_CHOICES = [
        (TYPE_CHAPTER, "Chapter"),
        (TYPE_TEENS, "Teens Wing"),
        (TYPE_NATIONAL_BOARD, "National Board"),
        (TYPE_SENATE, "DPL Senate"),
        (TYPE_ORGANISATION, "Organisation"),
    ]
    BOARD_TYPES = [TYPE_NATIONAL_BOARD, TYPE_SENATE]

    PROVINCE_CHOICES = [
        ("koshi", "Koshi"),
        ("madhesh", "Madhesh"),
        ("bagmati", "Bagmati"),
        ("gandaki", "Gandaki"),
        ("lumbini", "Lumbini"),
        ("karnali", "Karnali"),
        ("sudurpashchim", "Sudurpashchim"),
    ]

    branch_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=120, unique=True, help_text="Used in the web address, e.g. /chapters/damak/")
    branch_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_CHAPTER)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wings",
        help_text="For a Teens wing, the chapter it belongs to.",
    )
    tagline = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    main_image = models.ImageField(upload_to='branches/', blank=True)
    established_date = models.DateField(null=True, blank=True)

    address = models.CharField(max_length=255, blank=True)
    district = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=20, choices=PROVINCE_CHOICES, blank=True)
    map_url = models.URLField(blank=True, help_text="Google Maps link to the library")
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    opening_hours = models.CharField(max_length=120, blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)

    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_branches"
    )
    is_active = models.BooleanField(default=True, help_text="Inactive branches are hidden from the public site.")
    in_about_menu = models.BooleanField(
        default=False,
        help_text="List this page under the About menu (e.g. DPL, DPL Nepal, boards).",
    )
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    objects = BranchQuerySet.as_manager()

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = "Branch"
        verbose_name_plural = "Branches"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)

    def _unique_slug(self):
        base = slugify(self.name)[:110] or "branch"
        slug, n = base, 1
        while ParentBranch.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            n += 1
            slug = f"{base}-{n}"
        return slug

    def get_absolute_url(self):
        if self.branch_type == self.TYPE_ORGANISATION:
            return reverse("about_page", kwargs={"slug": self.slug})
        return reverse("branch_detail", kwargs={"slug": self.slug})

    @property
    def is_organisation(self):
        return self.branch_type == self.TYPE_ORGANISATION

    @property
    def is_board(self):
        return self.branch_type in self.BOARD_TYPES


class BranchTeam(models.Model):
    TYPE_BOARD = "board"
    TYPE_CHARTER_PRESIDENT = "charter_president"
    TYPE_PAST_PRESIDENT = "past_president"
    TYPE_ADVISOR = "advisor"
    MEMBER_TYPE_CHOICES = [
        (TYPE_BOARD, "Current Board"),
        (TYPE_CHARTER_PRESIDENT, "Charter President"),
        (TYPE_PAST_PRESIDENT, "Past President"),
        (TYPE_ADVISOR, "Advisor"),
    ]

    branch = models.ForeignKey(
        ParentBranch,
        on_delete=models.CASCADE,
        related_name='branch_teams'
    )
    member_name = models.CharField(max_length=255)
    designation = models.CharField(max_length=255)
    member_type = models.CharField(max_length=20, choices=MEMBER_TYPE_CHOICES, default=TYPE_BOARD)
    term = models.CharField(max_length=50, blank=True, help_text="e.g. 2024-2026")
    bio = models.TextField(blank=True)
    member_image = models.ImageField(upload_to='branch_team/', blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return f'{self.member_name} - {self.designation}'


class BranchGalleryImage(models.Model):
    branch = models.ForeignKey(ParentBranch, on_delete=models.CASCADE, related_name="gallery")
    image = models.ImageField(upload_to="branch_gallery/")
    caption = models.CharField(max_length=255, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "-uploaded_at"]

    def __str__(self):
        return f"{self.branch.name} - {self.caption or 'Photo'}"


class Program(models.Model):
    branch = models.ForeignKey(
        ParentBranch,
        on_delete=models.CASCADE,
        related_name='programs'
    )  # Link programs to a specific branch
    title = models.CharField(max_length=255)  # Program title
    description = models.TextField()  # Detailed description
    program_date = models.DateField()  # Program date
    coordinator_name = models.CharField(max_length=255)  # Coordinator's name
    image = models.ImageField(upload_to='programs/')  # Program image

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("program_detail", kwargs={"program_id": self.pk})


class ProgramImage(models.Model):
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name='sub_images'
    )  # Link sub-images to a specific program
    image = models.ImageField(upload_to='program_sub_images/')  # Sub-image upload
    caption = models.CharField(max_length=255, blank=True, null=True)  # Optional caption for each sub-image

    def __str__(self):
        return f"Image for {self.program.title} - {self.caption if self.caption else 'No Caption'}"
