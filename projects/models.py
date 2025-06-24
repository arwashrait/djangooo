from django.db import models
from django.contrib.auth import get_user_model

#
from django.utils import timezone
from django.urls import reverse
from django.db.models import Sum, Avg
import os


User = get_user_model()

# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=50)
    
    def __str__(self):
        return self.name
    
    
class Project(models.Model):
    # title = models.CharField(max_length=200)
    # details = models.TextField()
    # category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    # total_target = models.DecimalField(max_digits=10, decimal_places=2)
    # start_time = models.DateTimeField()
    # end_time = models.DateTimeField()
    # created_at = models.DateTimeField(auto_now_add=True)
    # tags = models.ManyToManyField(Tag)
    # creator = models.ForeignKey(User, on_delete=models.CASCADE)
    # is_cancelled = models.BooleanField(default=False)
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
    )
    
    title = models.CharField(max_length=200)
    details = models.TextField()
    total_target = models.PositiveIntegerField()
    
    # Relationships
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    
    # Timing
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Status
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    # average_rating = models.FloatField(default=0.0)
    rating_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('project-detail', kwargs={'pk': self.pk})
    
    @property
    def total_donations(self):
        result = self.donations.aggregate(total=Sum('amount'))
        return result['total'] if result['total'] is not None else 0
    @property
    def percent_funded(self):
        if self.total_target > 0:
            return min(100, (self.total_donations / self.total_target) * 100)
        return 0
    
    def can_be_canceled(self):
        return self.total_donations < (self.total_target * 0.25)


    # @property
    # def current_fund_calculated(self):
    #     # Calculates total donations for this project
    #     return self.donations.aggregate(Sum('amount'))['amount__sum'] or 0

    @property
    def average_rating_calculated(self):
        # Calculates average rating for this project
        return self.ratings.aggregate(Avg('value'))['value__avg'] or 0

  
    
class ProjectPicture(models.Model):
    project = models.ForeignKey(Project, related_name='pictures', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='projects/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
       return f"Image for {self.project.title}"
   
class Donation(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='donations')
    amount = models.PositiveIntegerField(help_text="Donation amount in EGP")
    donated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amount} EGP to {self.project.title}"
    
class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  # For comment moderation
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')

    # def __str__(self):
    
    #     return f"Comment by {self.user.username}"
           
    @property
    def is_reply(self):
        return self.parent is not None
    
    
    def get_replies(self):
        return self.replies.filter(is_active=True)
    
class Report(models.Model):
    """Base model for reports (abstract)"""
    REPORT_STATUS = (
        ('pending', 'Pending Review'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected'),
    )
    
    reporter = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10, 
        choices=REPORT_STATUS, 
        default='pending'
    )
    admin_notes = models.TextField(blank=True, null=True)

    class Meta:
        abstract = True    
        
        
        
class Rating(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    value = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')])
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('project', 'user')
    
    def __str__(self):
        return f"{self.value} stars by {self.user.username}"        