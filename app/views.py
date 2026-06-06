from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from datetime import timedelta
import json

from .models import (
    Profile, Course, Lesson, StudentProgress, 
    Submission, CodeExecution, PaymentVerification, Addon, UserAddon
)
from .execution import PistonExecutor
from django.conf import settings

TIER_WEIGHTS = {'FREE': 0, 'PAID_MONTH': 1, 'PAID_YEAR': 1}

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def register_view(request):
    if request.user.is_authenticated:
        return redirect('course_list')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('course_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserCreationForm()
    
    return render(request, 'app/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('course_list')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not hasattr(user, 'profile'):
                Profile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            next_url = request.GET.get('next', 'course_list')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'app/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('login')

@login_required
def course_list(request):
    if not hasattr(request.user, 'profile'):
        Profile.objects.get_or_create(user=request.user)
    
    courses = Course.objects.all().order_by('level')
    user_tier = request.user.profile.tier
    
    for course in courses:
        can_access = (course.tier_required == 'FREE') or (user_tier != 'FREE')
        course.is_locked = not can_access
        course.first_lesson = course.lessons.first()
    
    context = {
        'courses': courses,
        'user_tier': user_tier,
    }
    return render(request, 'app/course_list.html', context)

@login_required
def lesson_detail(request, course_id, lesson_id):
    course = get_object_or_404(Course, id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)
    
    user_tier = request.user.profile.tier
    can_access = (course.tier_required == 'FREE') or (user_tier != 'FREE')
    
    if not can_access:
        messages.error(request, "This course requires paid access.")
        return redirect('course_list')
    
    lessons_in_course = course.lessons.all().order_by('order')
    progress_record = StudentProgress.objects.filter(student=request.user, lesson=lesson).first()
    is_completed = progress_record.completed if progress_record else False
    
    context = {
        'course': course,
        'lesson': lesson,
        'lessons': lessons_in_course,
        'is_completed': is_completed,
    }
    return render(request, 'app/lesson_detail.html', context)

@login_required
@require_POST
def mark_lesson_complete(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    progress, created = StudentProgress.objects.get_or_create(student=request.user, lesson=lesson)
    
    if not progress.completed:
        progress.completed = True
        progress.completed_at = timezone.now()
        progress.save()
        messages.success(request, f'✓ {lesson.title} completed!')
    
    next_lesson = Lesson.objects.filter(course=lesson.course, order__gt=lesson.order).first()
    if next_lesson:
        return redirect('lesson_detail', course_id=lesson.course.id, lesson_id=next_lesson.id)
    
    messages.success(request, f'🎉 Course {lesson.course.title} completed!')
    return redirect('course_list')

@login_required
def pset_submit(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = lesson.course
    
    user_tier = request.user.profile.tier
    can_access = (course.tier_required == 'FREE') or (user_tier != 'FREE')
    
    if not can_access:
        messages.error(request, "No access to this lesson.")
        return redirect('course_list')
    
    if request.method == 'POST':
        language = request.POST.get('language')
        code = request.POST.get('code')
        
        if not language or not code:
            messages.error(request, "Language and code required.")
            return redirect('pset_submit', lesson_id=lesson_id)
        
        submission = Submission.objects.create(
            student=request.user,
            lesson=lesson,
            language=language,
            code=code,
            status='PENDING'
        )
        
        return redirect('code_editor', submission_id=submission.id)
    
    submissions = Submission.objects.filter(student=request.user, lesson=lesson).order_by('-submitted_at')
    
    context = {
        'lesson': lesson,
        'course': course,
        'submissions': submissions,
    }
    return render(request, 'app/pset_submit.html', context)

@login_required
def code_editor(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id, student=request.user)
    lesson = submission.lesson
    
    if request.method == 'POST':
        code = request.POST.get('code', submission.code)
        submission.code = code
        submission.save()
        messages.success(request, 'Code saved!')
    
    context = {
        'submission': submission,
        'lesson': lesson,
        'languages': [
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
    }
    return render(request, 'app/code_editor.html', context)

@login_required
@require_POST
def execute_code(request):
    try:
        data = json.loads(request.body)
        submission_id = data.get('submission_id')
        code = data.get('code')
        
        submission = get_object_or_404(Submission, id=submission_id, student=request.user)
        
        if submission.language in ['flask', 'django']:
            return JsonResponse({
                'status': 'error',
                'message': 'Flask/Django requires server setup. Coming soon!'
            })
        
        result = PistonExecutor.execute(submission.language, code)
        
        submission.output = result['output']
        submission.status = result['status']
        submission.save()
        
        return JsonResponse({
            'status': 'success',
            'output': result['output'],
            'error': result['error'],
            'exec_status': result['status']
        })
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def payment_page(request):
    if request.method == 'POST':
        tier = request.POST.get('tier')
        duration = request.POST.get('duration')
        transaction_id = request.POST.get('transaction_id')
        screenshot_url = request.POST.get('screenshot_url')
        
        if not all([tier, duration, transaction_id, screenshot_url]):
            messages.error(request, 'All fields required.')
            return redirect('payment_page')
        
        try:
            PaymentVerification.objects.create(
                user=request.user,
                tier=tier,
                duration=duration,
                transaction_id=transaction_id,
                screenshot_file = request.FILES.get('screenshot')

if screenshot_file:
    # Upload to Supabase Storage
    file_path = f"payments/{request.user.id}/{screenshot_file.name}"
    supabase.storage.from_('payments').upload(
        file_path,
        screenshot_file.read()
    )
    
    # Get public URL
    screenshot_url = supabase.storage.from_('payments').get_public_url(file_path)
            )
            messages.success(request, 'Payment submitted! Awaiting approval.')
            return redirect('payment_pending')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('payment_page')
    
    context = {
        'current_tier': request.user.profile.tier,
        'paid_month_price': settings.PAID_MONTH_PRICE,
        'paid_year_price': settings.PAID_YEAR_PRICE,
    }
    return render(request, 'app/payment.html', context)

@login_required
def payment_pending(request):
    latest = request.user.payments.order_by('-submitted_at').first()
    context = {'submission': latest}
    return render(request, 'app/payment_pending.html', context)

def portfolio(request, username):
    user = get_object_or_404(User, username=username)
    profile = user.profile
    
    if not profile.portfolio_public:
        messages.error(request, "This portfolio is private.")
        return redirect('course_list') if request.user.is_authenticated else redirect('login')
    
    completed_lessons = StudentProgress.objects.filter(
        student=user,
        completed=True
    ).select_related('lesson__course').order_by('-completed_at')
    
    courses = Course.objects.filter(lessons__student_progress__student=user).distinct()
    courses_completed = set()
    
    for course in courses:
        total = course.lessons.count()
        completed = StudentProgress.objects.filter(
            student=user,
            lesson__course=course,
            completed=True
        ).count()
        if total > 0 and completed == total:
            courses_completed.add(course)
    
    context = {
        'profile': profile,
        'completed_lessons': completed_lessons,
        'courses_completed': courses_completed,
        'portfolio_user': user,
    }
    return render(request, 'app/portfolio.html', context)

@login_required
def my_portfolio(request):
    return redirect('portfolio', username=request.user.username)

@login_required
def addons(request):
    available_addons = Addon.objects.all()
    user_addons = UserAddon.objects.filter(user=request.user).values_list('addon_id', flat=True)
    
    context = {
        'addons': available_addons,
        'user_addon_ids': list(user_addons),
    }
    return render(request, 'app/addons.html', context)