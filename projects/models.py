from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from django.db.models import Sum, Avg,Count # Make sure Sum and Avg are imported
import os


User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categories" # Good practice for admin display

    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True) # Tags should ideally be unique

    def __str__(self):
        return self.name

class Project(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
        ('expired', 'Expired'), # Add an expired status for campaigns past end_time
    )

    title = models.CharField(max_length=200)
    details = models.TextField()
    total_target = models.PositiveIntegerField(help_text="Target amount in EGP")

    # Relationships
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)

    # Timing
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Status & Cached Aggregates
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    is_featured = models.BooleanField(default=False) # Added as per API views usage

    # Cached average rating and count (updated via signals or custom save)
    average_rating = models.FloatField(default=0.0) # Un-commented and explicitly added
    rating_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('projects:detail', kwargs={'pk': self.pk})

    @property
    def total_donations_collected(self): # Renamed for clarity and to avoid conflict if 'total_donations' annotation is used
        # Calculates total donations for this project
        result = self.donations.aggregate(total=Sum('amount'))
        return result['total'] if result['total'] is not None else 0

    @property
    def percent_funded(self):
        # Uses the total_donations_collected property for calculation
        if self.total_target > 0:
            return min(100, (self.total_donations_collected / self.total_target) * 100)
        return 0

    @property
    def is_active_campaign(self):
        # Checks if the campaign is active and not past its end time
        return self.status == 'active' and self.end_time > timezone.now()

    def update_rating_summary(self):
        # Method to update cached average_rating and rating_count
        agg = self.ratings.aggregate(avg_value=Avg('value'), count_value=Count('value'))
        self.average_rating = agg['avg_value'] if agg['avg_value'] is not None else 0.0
        self.rating_count = agg['count_value'] if agg['count_value'] is not None else 0
        self.save(update_fields=['average_rating', 'rating_count'])


class ProjectPicture(models.Model):
    project = models.ForeignKey(Project, related_name='pictures', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='projects/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
       return f"Image for {self.project.title} ({self.id})"

class Donation(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='donations') # Added related_name
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='donations')
    amount = models.PositiveIntegerField(help_text="Donation amount in EGP")
    donated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ordering donations by most recent first
        ordering = ['-donated_at']

    def __str__(self):
        return f"{self.amount} EGP to {self.project.title} by {self.user.username if self.user else 'Anonymous'}"


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments') # Added related_name
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='comments') # Changed to project_comments for distinct
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  # For comment moderation
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')

    class Meta:
        # Ordering comments by oldest first, then by parent for replies
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.project.title}"

    @property
    def is_reply(self):
        return self.parent is not None

    def get_replies(self):
        return self.replies.filter(is_active=True).order_by('created_at')


class Report(models.Model):
    """Base model for reports (abstract)"""
    REPORT_STATUS = (
        ('pending', 'Pending Review'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected'),
    )
    REPORT_TYPES = (
        ('spam', 'Spam'),
        ('hateful_content', 'Hateful Content'),
        ('misleading', 'Misleading Information'),
        ('other', 'Other'),
    )

    reporter = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.TextField(max_length=500, blank=True)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES, default='other') # Added explicit report type
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10,
        choices=REPORT_STATUS,
        default='pending'
    )
    admin_notes = models.TextField(blank=True, null=True)

    class Meta:
        abstract = True
        ordering = ['-created_at'] # Most recent reports first


class ProjectReport(Report): # Concrete model for project reports
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_reports')

    class Meta:
        # Ensure a user can only report a project once
        unique_together = ('project', 'reporter')
        verbose_name = "Project Report"
        verbose_name_plural = "Project Reports"

    def __str__(self):
        return f"Report on Project '{self.project.title}' by {self.reporter.username}"

class CommentReport(Report): # Concrete model for comment reports
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='comment_reports')

    class Meta:
        # Ensure a user can only report a comment once
        unique_together = ('comment', 'reporter')
        verbose_name = "Comment Report"
        verbose_name_plural = "Comment Reports"

    def __str__(self):
        return f"Report on Comment by {self.comment.user.username} on '{self.comment.project.title}'"


class Rating(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='ratings') # ADDED related_name='ratings'
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_ratings') # Added related_name
    value = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)]) # More concise choices
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'user') # User can only rate a project once
        ordering = ['-created_at'] # Most recent ratings first

    def __str__(self):
        return f"{self.value} stars by {self.user.username} for {self.project.title}"

# Optional: Signals to update average_rating and rating_count on Project
# You'd typically put this in a separate file (e.g., projects/signals.py) and import in projects/apps.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver([post_save, post_delete], sender=Rating)
def update_project_rating_summary(sender, instance, **kwargs):
    """
    Signal to update Project's cached average_rating and rating_count
    whenever a Rating is saved or deleted.
    """
    if instance.project:
        instance.project.update_rating_summary()

