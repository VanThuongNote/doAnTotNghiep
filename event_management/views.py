import json
import random
import threading
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Count

from django.contrib.auth.models import User
from events.models import (
    EventCategory,
    Event,
    EventMember,
    UserCoin,
    UserProfile,
    PasswordResetOTP,
)
from .forms import LoginForm, RegisterForm, ResetPasswordForm


@login_required(login_url='login')
def dashboard(request):
    """
    Trang tổng quan hệ thống.
    Hiển thị thống kê: số danh mục, số sự kiện, số người dùng, sự kiện hoàn thành,
    kèm biểu đồ thống kê thực tế (Chart.js) và danh sách sự kiện gần nhất.
    """
    user_count = User.objects.count()
    event_ctg = EventCategory.objects.count()
    event_count = Event.objects.count()
    complete_event = Event.objects.filter(status='completed').count()
    active_event = Event.objects.filter(status='active').count()
    events = Event.objects.select_related('category').order_by('-start_date')[:10]

    # Thống kê theo Danh mục sự kiện cho Bar Chart
    categories = EventCategory.objects.annotate(
        num_events=Count('event', distinct=True),
        num_members=Count('event__eventmember', distinct=True),
    ).order_by('priority')[:8]

    cat_labels = [c.name for c in categories]
    cat_event_counts = [c.num_events for c in categories]
    cat_member_counts = [c.num_members for c in categories]

    # Thống kê trạng thái điểm danh cho Doughnut Chart
    if request.user.is_staff or request.user.is_superuser:
        member_qs = EventMember.objects.all()
    else:
        member_qs = EventMember.objects.filter(user=request.user)

    attended_cnt = member_qs.filter(attend_status__in=['attending', 'completed', 'present']).count()
    waiting_cnt = member_qs.filter(attend_status='waiting').count()
    absent_cnt = member_qs.filter(attend_status='absent').count()

    context = {
        'user_count': user_count,
        'event_ctg': event_ctg,
        'event': event_count,
        'complete_event': complete_event,
        'active_event': active_event,
        'events': events,
        'chart_cat_labels': json.dumps(cat_labels, ensure_ascii=False),
        'chart_cat_events': json.dumps(cat_event_counts),
        'chart_cat_members': json.dumps(cat_member_counts),
        'chart_attend_data': json.dumps([attended_cnt, waiting_cnt, absent_cnt]),
        'attended_cnt': attended_cnt,
        'waiting_cnt': waiting_cnt,
        'absent_cnt': absent_cnt,
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
            else:
                messages.error(request, 'Tên đăng nhập hoặc mật khẩu không chính xác!')
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

    total_registered = EventMember.objects.filter(user=request.user).exclude(attend_status='cancelled').count()
    completed_count = EventMember.objects.filter(
        user=request.user, attend_status__in=['attending', 'completed', 'present']
    ).count()
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
    """Trang cài đặt: đổi mật khẩu + cài đặt thông báo email."""
    from events.models import NotificationSetting
    notif_setting, _ = NotificationSetting.objects.get_or_create(user=request.user)

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

        elif action == 'save_notification':
            notif_setting.email_notification = request.POST.get('email_notification') == 'on'
            notif_setting.event_reminder = request.POST.get('event_reminder') == 'on'
            notif_setting.points_notification = request.POST.get('points_notification') == 'on'
            notif_setting.save()
            messages.success(request, 'Đã lưu cài đặt thông báo!')
            return redirect('settings')

    context = {
        'notif_setting': notif_setting,
    }
    return render(request, 'settings.html', context)


@login_required(login_url='login')
def all_notifications(request):
    """Trang xem tất cả thông báo của user."""
    from events.models import Notification
    notifications = Notification.objects.filter(user=request.user).select_related('event')[:100]
    return render(request, 'notifications.html', {'notifications': notifications})


@login_required(login_url='login')
def mark_notification_read(request, pk):
    """AJAX: Đánh dấu 1 thông báo đã đọc."""
    from events.models import Notification
    from django.http import JsonResponse
    if request.method == 'POST':
        try:
            notif = Notification.objects.get(pk=pk, user=request.user)
            notif.is_read = True
            notif.save()
            unread = Notification.objects.filter(user=request.user, is_read=False).count()
            return JsonResponse({'status': 'ok', 'unread_count': unread})
        except Notification.DoesNotExist:
            return JsonResponse({'status': 'error'}, status=404)
    return JsonResponse({'status': 'error'}, status=405)


@login_required(login_url='login')
def mark_all_notifications_read(request):
    """AJAX: Đánh dấu tất cả thông báo đã đọc."""
    from events.models import Notification
    from django.http import JsonResponse
    if request.method == 'POST':
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'status': 'ok', 'unread_count': 0})
    return JsonResponse({'status': 'error'}, status=405)


@login_required(login_url='login')
def delete_notification(request, pk):
    """Xóa thông báo."""
    from events.models import Notification
    from django.http import JsonResponse
    if request.method == 'POST':
        Notification.objects.filter(pk=pk, user=request.user).delete()
        unread = Notification.objects.filter(user=request.user, is_read=False).count()
        return JsonResponse({'status': 'ok', 'unread_count': unread})
    return JsonResponse({'status': 'error'}, status=405)


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


def _send_otp_email_async(user_email: str, username: str, otp_code: str):
    """Gửi mã OTP 6 chữ số qua Email (bất đồng bộ)."""
    def _worker():
        try:
            html_msg = f"""
            <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 520px; margin: 0 auto; border:1px solid #e2e8f0; border-radius:16px; overflow:hidden;">
                <div style="background: linear-gradient(135deg, #4f46e5, #7c3aed); padding: 24px; color:#fff; text-align:center;">
                    <h2 style="margin:0;">🔐 Mã xác thực đặt lại mật khẩu</h2>
                </div>
                <div style="padding: 28px; background:#fff; color:#1e293b;">
                    <p>Xin chào <strong>{username}</strong>,</p>
                    <p>Bạn vừa yêu cầu đặt lại mật khẩu trên Hệ thống Quản lý Sự kiện. Đây là mã xác thực OTP của bạn (hiệu lực trong 10 phút):</p>
                    <div style="background:#f8fafc; border:2px dashed #6366f1; border-radius:12px; padding:18px; text-align:center; font-size:32px; font-weight:900; letter-spacing:8px; color:#4f46e5; margin:20px 0;">
                        {otp_code}
                    </div>
                    <p style="font-size:12px; color:#64748b;">Nếu bạn không thực hiện yêu cầu này, vui lòng bỏ qua email này.</p>
                </div>
            </div>
            """
            send_mail(
                subject=f"[Mã OTP: {otp_code}] Đặt lại mật khẩu - Quản lý Sự kiện",
                message=f"Mã OTP đặt lại mật khẩu của bạn là: {otp_code} (hiệu lực 10 phút).",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                html_message=html_msg,
                fail_silently=True,
            )
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def forgot_password_page(request):
    """
    Trang quên mật khẩu bảo mật 2 bước với mã OTP 6 số gửi qua Email:
    - Bước 1 (step = 'request_otp'): Nhập username + email -> gửi mã OTP 6 số.
    - Bước 2 (step = 'verify_otp'): Nhập mã OTP + mật khẩu mới -> đổi mật khẩu.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    step = request.POST.get('step', 'request_otp')
    form = ResetPasswordForm(request.POST or None)

    if request.method == 'POST':
        if step == 'request_otp':
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip()

            user = None
            if username and email:
                user = User.objects.filter(username__iexact=username, email__iexact=email).first()
                if not user:
                    # Nếu tài khoản tồn tại nhưng trước đó chưa lưu email thì cập nhật email cho tài khoản
                    candidate = User.objects.filter(username__iexact=username).first()
                    if candidate and not candidate.email:
                        candidate.email = email
                        candidate.save(update_fields=['email'])
                        user = candidate
            elif username:
                user = User.objects.filter(username__iexact=username).first()
            elif email:
                user = User.objects.filter(email__iexact=email).first()

            if user:
                target_email = user.email or email
                PasswordResetOTP.objects.filter(user=user, is_used=False).update(is_used=True)
                otp_code = f"{random.randint(100000, 999999)}"
                PasswordResetOTP.objects.create(user=user, otp_code=otp_code)
                if target_email:
                    _send_otp_email_async(target_email, user.username, otp_code)

                if settings.DEBUG or not settings.EMAIL_HOST_USER:
                    messages.info(
                        request,
                        f"Đã gửi mã xác thực OTP đến {target_email or 'hệ thống'}. (Mã OTP xác thực của bạn là: {otp_code})"
                    )
                else:
                    messages.success(
                        request,
                        f"Mã xác thực OTP 6 chữ số đã được gửi tới email {target_email}. Vui lòng kiểm tra hộp thư!"
                    )
                return render(request, 'forgot_password.html', {
                    'form': ResetPasswordForm(initial={'username': user.username, 'email': target_email}),
                    'step': 'verify_otp',
                    'username_val': user.username,
                    'email_val': target_email,
                })
            else:
                messages.error(request, 'Tên đăng nhập hoặc email không đúng! Vui lòng kiểm tra lại.')

        elif step == 'verify_otp':
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip()
            otp_input = request.POST.get('otp_code', '').strip()
            new_pw = request.POST.get('new_password', '')
            confirm_pw = request.POST.get('confirm_password', '')

            user = (
                User.objects.filter(username__iexact=username).first()
                if username
                else User.objects.filter(email__iexact=email).first()
            )
            if not user:
                messages.error(request, 'Thông tin tài khoản không hợp lệ!')
                return render(request, 'forgot_password.html', {'form': form, 'step': 'request_otp'})

            otp_record = PasswordResetOTP.objects.filter(
                user=user, otp_code=otp_input, is_used=False
            ).order_by('-created_at').first()

            if not otp_record or not otp_record.is_valid():
                messages.error(request, 'Mã OTP không chính xác hoặc đã hết hạn (10 phút)!')
                return render(request, 'forgot_password.html', {
                    'form': form,
                    'step': 'verify_otp',
                    'username_val': user.username,
                    'email_val': user.email or email,
                    'otp_val': otp_input,
                })

            if len(new_pw) < 6:
                messages.error(request, 'Mật khẩu mới phải có ít nhất 6 ký tự!')
                return render(request, 'forgot_password.html', {
                    'form': form,
                    'step': 'verify_otp',
                    'username_val': user.username,
                    'email_val': user.email or email,
                    'otp_val': otp_input,
                })

            if new_pw != confirm_pw:
                messages.error(request, 'Mật khẩu xác nhận không khớp!')
                return render(request, 'forgot_password.html', {
                    'form': form,
                    'step': 'verify_otp',
                    'username_val': user.username,
                    'email_val': user.email or email,
                    'otp_val': otp_input,
                })

            otp_record.is_used = True
            otp_record.save()
            user.set_password(new_pw)
            user.save()
            messages.success(request, '🎉 Đặt lại mật khẩu thành công! Hãy đăng nhập với mật khẩu mới.')
            return redirect('login')

    return render(request, 'forgot_password.html', {'form': form, 'step': 'request_otp'})
