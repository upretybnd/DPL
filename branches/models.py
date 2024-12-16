from django.contrib.auth.models import User
from django.db import models

class ParentBranch(models.Model):
    branch_id = models.AutoField(primary_key=True)  # Auto-generated primary key
    name = models.CharField(max_length=255)  # Name of the branch
    main_image = models.ImageField(upload_to='branches/')  # Image upload directory for branches
    description = models.TextField()  # Branch description
    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_branches"
    )  # Assign a manager to the branch

    def __str__(self):
        return self.name  # Display the branch name in admin and shell

class BranchTeam(models.Model):
    branch = models.ForeignKey(
        ParentBranch,
        on_delete=models.CASCADE,
        related_name='branch_teams'
    )  # Link team members to a specific branch
    member_name = models.CharField(max_length=255)  # Team member's name
    designation = models.CharField(max_length=255)  # Member's designation
    member_image = models.ImageField(upload_to='branch_team/')  # Team member image upload directory

    def __str__(self):
        return f'{self.member_name} - {self.designation}'  # Display member name and designation

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