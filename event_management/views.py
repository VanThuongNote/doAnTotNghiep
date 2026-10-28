from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from django.contrib.auth.models import User
from events.models import EventCategory, Event, EventMember, UserCoin, UserProfile
from .forms import LoginForm, RegisterForm, ResetPasswordForm

@login_required(login_url='login')
def dashboard(request):
    """
    Trang tổng quan hệ thống.
    Hiển thị thống kê: số danh mục, số sự kiện, số người dùng, sự kiện hoàn thành.
    Danh sách sự kiện đang hoạt động gần nhất.
    """
    user = User.objects.count()
    event_ctg = EventCategory.objects.count()
    event = Event.objects.count()
    complete_event = Event.objects.filter(status='completed').count()
    active_event = Event.objects.filter(status='active').count()
    events = Event.objects.all().order_by('-start_date')[:10]
    context = {
        'user_count': user,
        'event_ctg': event_ctg,
        'event': event,
        'complete_event': complete_event,
        'active_event': active_event,
        'events': events,
    }
    return render(request, 'dashboard.html', context)

def login_page(request):
    forms = LoginForm()
    if request.method == 'POST':
        forms = LoginForm(request.POST)
        if forms.is_valid():
            username = forms.cleaned_data['username']
            password = forms.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                return redirect('dashboard')
    context = {
        'form': forms
    }
    return render(request, 'login.html', context)

def logut_page(request):
    logout(request)
    return redirect('login')

@login_required(login_url='login')
def profile_page(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()

        profile.phone = request.POST.get('phone', profile.phone)
        profile.address = request.POST.get('address', profile.address)
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
        profile.save()

        messages.success(request, 'Cập nhật hồ sơ thành công!')
        return redirect('profile')

    total_registered = EventMember.objects.filter(user=request.user).count()
    completed_count = EventMember.objects.filter(user=request.user, attend_status__in=['attending', 'completed']).count()
    user_coin = UserCoin.objects.filter(user=request.user).first()
    points = user_coin.gain_coin if user_coin else 0

    context = {
        'profile': profile,
        'total_registered': total_registered,
        'completed_count': completed_count,
        'points': points
    }
    return render(request, 'profile.html', context)

@login_required(login_url='login')
def settings_page(request):
    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'change_password':
            old_password = request.POST.get('old_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')
            user = request.user
            if not user.check_password(old_password):
                messages.error(request, 'Mật khẩu cũ không đúng!')
            elif new_password != confirm_password:
                messages.error(request, 'Mật khẩu mới không khớp!')
            elif len(new_password) < 6:
                messages.error(request, 'Mật khẩu mới phải có ít nhất 6 ký tự!')
            else:
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Đổi mật khẩu thành công!')
            return redirect('settings')
    return render(request, 'settings.html', {})


def register_page(request):
    """Trang đăng ký tài khoản mới cho người dùng."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegisterForm()
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data.get('first_name', ''),
                last_name=form.cleaned_data.get('last_name', ''),
            )
            messages.success(request, f'Đăng ký thành công! Chào mừng {user.username}. Hãy đăng nhập.')
            return redirect('login')
    return render(request, 'register.html', {'form': form})


def forgot_password_page(request):
    """Trang quên mật khẩu: xác minh username + email rồi đặt mật khẩu mới."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = ResetPasswordForm()
    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(username=username, email=email)
                user.set_password(form.cleaned_data['new_password'])
                user.save()
                messages.success(request, 'Đặt lại mật khẩu thành công! Hãy đăng nhập với mật khẩu mới.')
                return redirect('login')
            except User.DoesNotExist:
                messages.error(request, 'Tên đăng nhập hoặc email không đúng!')
    return render(request, 'forgot_password.html', {'form': form})