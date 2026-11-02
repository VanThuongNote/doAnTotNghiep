"""
Context processor cung cấp thông báo cho tất cả các template.
Mỗi trang đều có biến `unread_notifications` và `unread_count`.
"""
from .models import Notification


def notifications_context(request):
    """Inject thông báo chưa đọc vào mọi template."""
    if request.user.is_authenticated:
        unread_notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).select_related('event')[:20]
        unread_count = unread_notifications.count()
        return {
            'unread_notifications': unread_notifications,
            'unread_count': unread_count,
        }
    return {
        'unread_notifications': [],
        'unread_count': 0,
    }
