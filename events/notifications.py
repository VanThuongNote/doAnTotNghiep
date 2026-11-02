"""
Hệ thống thông báo - Tạo thông báo và gửi email tự động.

Sử dụng:
    from events.notifications import create_notification
    create_notification(
        user=request.user,
        title='Đăng ký thành công',
        message='Bạn đã đăng ký sự kiện ABC',
        notif_type='registration',
        event=event,
        link='/events/ticket/123/',
    )
"""
import threading
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def create_notification(user, title, message, notif_type='system', event=None, link=None, send_email=True):
    """
    Tạo thông báo trong DB và gửi email nếu user bật cài đặt.
    
    Args:
        user: User nhận thông báo
        title: Tiêu đề thông báo
        message: Nội dung chi tiết
        notif_type: Loại thông báo (registration, reminder, checkin, system, event_new)
        event: Sự kiện liên quan (optional)
        link: Đường dẫn khi click vào thông báo (optional)
        send_email: Có gửi email hay không (mặc định True)
    """
    from .models import Notification, NotificationSetting

    # Tạo thông báo trong DB
    notif = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notif_type=notif_type,
        event=event,
        link=link,
    )

    # Kiểm tra cài đặt email của user
    if send_email:
        notif_setting, _ = NotificationSetting.objects.get_or_create(user=user)
        should_send = False

        if notif_type in ('registration', 'event_new') and notif_setting.email_notification:
            should_send = True
        elif notif_type == 'reminder' and notif_setting.event_reminder:
            should_send = True
        elif notif_type == 'checkin' and notif_setting.email_notification:
            should_send = True
        elif notif_type == 'system':
            should_send = True  # Luôn gửi thông báo hệ thống

        if should_send and user.email:
            # Gửi email bất đồng bộ để không blocking request
            thread = threading.Thread(
                target=_send_notification_email,
                args=(user, title, message, notif_type, event)
            )
            thread.daemon = True
            thread.start()

    return notif


def _send_notification_email(user, title, message, notif_type, event=None):
    """Gửi email thông báo (chạy trong thread riêng)."""
    try:
        # Tạo nội dung email HTML
        icon_map = {
            'registration': '🎫',
            'reminder': '⏰',
            'checkin': '✅',
            'system': '🔔',
            'event_new': '🎉',
        }
        icon = icon_map.get(notif_type, '🔔')

        html_content = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #4f46e5, #6366f1); padding: 30px; border-radius: 16px 16px 0 0;">
                <h1 style="color: #fff; margin: 0; font-size: 24px;">{icon} Quản lý sự kiện</h1>
                <p style="color: rgba(255,255,255,0.8); margin: 8px 0 0 0; font-size: 14px;">Thông báo mới cho bạn</p>
            </div>
            <div style="background: #fff; padding: 30px; border: 1px solid #e2e8f0; border-top: none;">
                <h2 style="color: #1e293b; margin: 0 0 12px 0; font-size: 18px;">{title}</h2>
                <p style="color: #475569; font-size: 14px; line-height: 1.6; margin: 0 0 20px 0;">{message}</p>
                {'<div style="background: #f8fafc; border-radius: 8px; padding: 16px; margin-bottom: 20px;"><strong style="color: #4f46e5;">📌 Sự kiện:</strong> <span style="color: #1e293b;">' + str(event.name) + '</span><br><strong style="color: #4f46e5;">📅 Ngày:</strong> <span style="color: #1e293b;">' + str(event.start_date) + ' → ' + str(event.end_date) + '</span></div>' if event else ''}
                <p style="color: #94a3b8; font-size: 12px; margin: 20px 0 0 0;">
                    Bạn nhận được email này vì đã bật thông báo email trong cài đặt.
                    Để tắt, vào Cài đặt → Thông báo.
                </p>
            </div>
            <div style="background: #f8fafc; padding: 16px; border-radius: 0 0 16px 16px; border: 1px solid #e2e8f0; border-top: none; text-align: center;">
                <p style="color: #94a3b8; font-size: 12px; margin: 0;">© Hệ thống quản lý sự kiện</p>
            </div>
        </div>
        """

        send_mail(
            subject=f"[Thông báo] {title}",
            message=strip_tags(html_content),  # Fallback text
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_content,
            fail_silently=True,
        )
    except Exception as e:
        print(f"[EMAIL ERROR] Không gửi được email cho {user.email}: {e}")


def notify_admins_new_registration(member):
    """
    Thông báo cho tất cả admin khi có người đăng ký sự kiện.
    """
    from django.contrib.auth.models import User
    admins = User.objects.filter(is_staff=True)
    for admin in admins:
        create_notification(
            user=admin,
            title=f"Đăng ký mới: {member.event.name}",
            message=f"Người dùng {member.user.get_full_name() or member.user.username} vừa đăng ký tham gia sự kiện \"{member.event.name}\".",
            notif_type='registration',
            event=member.event,
            link=f'/events/join-event-list/',
        )
