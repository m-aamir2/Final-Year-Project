from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=20)
    semester = models.CharField(max_length=10, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    must_change_password = models.BooleanField(default=True)
    is_suspended = models.BooleanField(default=False)
    expertise = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    github_account = models.URLField(blank=True, null=True)  
    bachelors_from = models.CharField(max_length=255, blank=True, null=True)  
    masters_from = models.CharField(max_length=255, blank=True, null=True)  
    phd_from = models.CharField(max_length=255, blank=True, null=True)  
    office_location = models.CharField(max_length=255, blank=True, null=True)  
    office_hours = models.CharField(max_length=255, blank=True, null=True)  
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)  


class Proposal(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('supervisor_approved', 'Supervisor Approved'),
        ('approved', 'Fully Approved'),
        ('rejected', 'Rejected'),
    )
    
    title = models.CharField(max_length=255)
    domain = models.CharField(max_length=255)
    document = models.FileField(upload_to='proposals/')
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='proposals')
    group_members = models.ManyToManyField(User, related_name='group_proposals')
    supervisors = models.ManyToManyField(User, related_name='supervised_proposals')
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, null=True)
    coordinator_rejection_reason = models.TextField(blank=True, null=True)  # Separate field for coordinator rejection
    keywords = models.JSONField(null=True, blank=True)
    similarity_score = models.FloatField(null=True, blank=True)
    extracted_text = models.TextField(blank=True, null=True)
    embedding = models.JSONField(blank=True, null=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['submitted_by', 'status']),
        ]

    def __str__(self):
        return self.title
    
class Meeting(models.Model):
    PLATFORM_CHOICES = [
        ('zoom', 'Zoom'),
        ('google_meet', 'Google Meet'),
        ('microsoft_teams', 'Microsoft Teams'),
        ('in_person', 'In Person'),
    ]
    
    supervisor = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(Proposal, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    date_time = models.DateTimeField()
    duration = models.PositiveIntegerField(help_text="Duration in minutes")
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    meeting_link = models.URLField(blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.date_time.strftime('%Y-%m-%d %H:%M')}"

from django.db import models
from django.contrib.auth.models import User

class Announcement(models.Model):
    title = models.CharField(max_length=255)
    message = models.TextField()
    post_date = models.DateField()
    deadline = models.DateField(null=True, blank=True)
    file = models.FileField(upload_to='announcements/', null=True, blank=True) 
    type = models.CharField(
        max_length=50,
        choices=[
            ('Proposal Deadline', 'Proposal Deadline'),
            ('Phase 1', 'Phase 1'),
            ('Phase 2', 'Phase 2'),
            ('Others', 'Others'),
        ]
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title

class Phase1Submission(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    title = models.CharField(max_length=255)
    document = models.FileField(upload_to='phase1/')
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='phase1_submissions')
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Phase 1 - {self.title}"


class Phase2Submission(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    title = models.CharField(max_length=255)
    document = models.FileField(upload_to='phase2/')
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='phase2_submissions')
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Phase 2 - {self.title}"
