from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Profile, Course, Lesson, StudentProgress, Submission, CodeExecution, PaymentVerification, Addon, UserAddon
from supabase import create_client, Client
from django.conf import settings
from datetime import timedelta

# Use SECRET KEY for deletions (backend only)
supabase = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SECRET_KEY
)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'tier', 'location', 'portfolio_public', 'created_at')
    list_filter = ('tier', 'created_at')
    search_fields = ('user__username', 'user__email')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'level', 'tier_required', 'lesson_count')
    list_filter = ('level', 'tier_required')
    search_fields = ('title', 'description')
    
    def lesson_count(self, obj):
        return obj.lessons.count()

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'has_video')
    list_filter = ('course', 'created_at')
    search_fields = ('title', 'course__title')
    
    def has_video(self, obj):
        return '✓' if obj.video_url else '✗'

@admin.register(StudentProgress)
class StudentProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'lesson', 'completed_badge', 'completed_at')
    list_filter = ('completed', 'completed_at')
    search_fields = ('student__username', 'lesson__title')
    
    def completed_badge(self, obj):
        return '✓' if obj.completed else '✗'

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'lesson', 'language', 'status', 'submitted_at')
    list_filter = ('language', 'status', 'submitted_at')
    search_fields = ('student__username', 'lesson__title')
    readonly_fields = ('submitted_at', 'code', 'output')

@admin.register(CodeExecution)
class CodeExecutionAdmin(admin.ModelAdmin):
    list_display = ('user', 'language', 'status', 'created_at')
    list_filter = ('language', 'status', 'created_at')
    search_fields = ('user__username',)

@admin.register(PaymentVerification)
class PaymentVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'tier', 'duration', 'status_badge', 'submitted_at', 'approve_action')
    list_filter = ('status', 'tier', 'submitted_at')
    search_fields = ('user__username', 'transaction_id')
    readonly_fields = ('submitted_at', 'approved_at')
    actions = ['approve_payment']
    
    def status_badge(self, obj):
        colors = {'PENDING': 'orange', 'APPROVED': 'green', 'REJECTED': 'red'}
        color = colors.get(obj.status, 'gray')
        return format_html(f'<span style="color: {color}; font-weight: bold;">{obj.status}</span>')
    
    def approve_action(self, obj):
        return 'Approve' if obj.status == 'PENDING' else '—'
    
    def approve_payment(self, request, queryset):
        updated = 0
        for payment in queryset.filter(status='PENDING'):
            # Delete screenshot from Supabase Storage FIRST
            try:
                file_path = payment.screenshot_url.split('/payments/')[-1]
                supabase.storage.from_('payments').remove([file_path])
            except Exception as e:
                self.message_user(request, f'Warning: Could not delete file: {str(e)}', level='WARNING')
            
            # THEN approve payment
            payment.status = 'APPROVED'
            payment.approved_at = timezone.now()
            
            if payment.duration == '1 Month':
                payment.user.profile.tier = payment.tier
                payment.user.profile.tier_expires_at = timezone.now() + timedelta(days=30)
            elif payment.duration == '1 Year':
                payment.user.profile.tier = payment.tier
                payment.user.profile.tier_expires_at = timezone.now() + timedelta(days=365)
            
            payment.user.profile.save()
            payment.save()
            updated += 1
        
        self.message_user(request, f'{updated} payment(s) approved. Screenshots deleted.')

@admin.register(UserAddon)
class UserAddonAdmin(admin.ModelAdmin):
    list_display = ('user', 'addon', 'purchased_at')
    list_filter = ('addon', 'purchased_at')
    search_fields = ('user__username', 'addon__name')