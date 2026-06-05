from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Profile(models.Model):
    TIER_CHOICES = [
        ('FREE', 'Free'),
        ('PAID_MONTH', 'Paid - 1 Month'),
        ('PAID_YEAR', 'Paid - 1 Year'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    tier = models.CharField(max_length=15, choices=TIER_CHOICES, default='FREE')
    tier_expires_at = models.DateTimeField(null=True, blank=True)
    headline = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    tech_stack = models.CharField(max_length=500, blank=True)
    theme_color = models.CharField(max_length=7, default='#6366f1')
    portfolio_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def is_tier_active(self):
        if self.tier == 'FREE':
            return True
        if self.tier_expires_at and timezone.now() > self.tier_expires_at:
            self.tier = 'FREE'
            self.save()
            return False
        return True
    
    def __str__(self):
        return f"{self.user.username} - {self.tier}"

class Course(models.Model):
    LEVEL_CHOICES = [(i, f'Level {i}') for i in range(1, 6)]
    TIER_CHOICES = [('FREE', 'Free'), ('PAID', 'Paid')]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    level = models.IntegerField(choices=LEVEL_CHOICES)
    tier_required = models.CharField(max_length=10, choices=TIER_CHOICES, default='FREE')
    thumbnail_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['level', 'title']
    
    def __str__(self):
        return self.title

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    content = models.TextField()
    code_example = models.TextField(blank=True)
    video_url = models.URLField(blank=True)
    order = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['course', 'order']
        unique_together = ['course', 'order']
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"

class StudentProgress(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='student_progress')
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['student', 'lesson']
    
    def __str__(self):
        return f"{self.student.username} - {self.lesson.title}"

class Submission(models.Model):
    LANGUAGE_CHOICES = [
        ('lua', 'Lua'),
        ('python', 'Python'),
        ('c', 'C'),
        ('javascript', 'JavaScript'),
        ('bash', 'Bash'),
        ('html', 'HTML'),
        ('css', 'CSS'),
        ('flask', 'Flask'),
        ('django', 'Django'),
    ]
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='submissions')
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES)
    code = models.TextField()
    output = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='PENDING')
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.student.username} - {self.lesson.title} ({self.language})"

class CodeExecution(models.Model):
    STATUS_CHOICES = [('RUNNING', 'Running'), ('SUCCESS', 'Success'), ('ERROR', 'Error')]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='executions')
    language = models.CharField(max_length=20)
    code = models.TextField()
    output = models.TextField(blank=True)
    error = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RUNNING')
    execution_time = models.FloatField(null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    session_id = models.CharField(max_length=100)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def __str__(self):
        return f"{self.user.username} - {self.language} - {self.status}"

class PaymentVerification(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    tier = models.CharField(max_length=15)
    duration = models.CharField(max_length=20)
    transaction_id = models.CharField(max_length=200, unique=True)
    screenshot_url = models.URLField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    submitted_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.tier} ({self.status})"

class Addon(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    permanent = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class UserAddon(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addons')
    addon = models.ForeignKey(Addon, on_delete=models.CASCADE)
    purchased_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'addon']
    
    def __str__(self):
        return f"{self.user.username} - {self.addon.name}"