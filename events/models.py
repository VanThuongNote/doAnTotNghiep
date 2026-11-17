from datetime import date, timedelta
import hashlib
from django.db import models
from django.db.models import Avg
from django.urls import reverse
from django.utils import timezone
from mapbox_location_field.models import LocationField
from ckeditor_uploader.fields import RichTextUploadingField


class EventCategory(models.Model):
    """
    Danh mục sự kiện.
    Mỗi sự kiện thuộc về một danh mục (VD: Công nghệ, Âm nhạc, Thể thao...).
    """

    name = models.CharField(max_length=255, unique=True, verbose_name='Tên danh mục')
    code = models.CharField(max_length=6, unique=True, verbose_name='Mã danh mục')
    image = models.ImageField(upload_to='event_category/', verbose_name='Ảnh đại diện')
    priority = models.IntegerField(unique=True, verbose_name='Thứ tự ưu tiên')
    created_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='created_user')
    updated_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='updated_user')
    created_date = models.DateField(auto_now_add=True)
    updated_date = models.DateField(auto_now_add=True)
    status_choice = (
        ('disabled', 'Vô hiệu hóa'),
        ('active', 'Hoạt động'),
        ('deleted', 'Đã xóa'),
        ('blocked', 'Đã khóa'),
        ('completed', 'Hoàn thành'),
    )
    status = models.CharField(choices=status_choice, max_length=10, verbose_name='Trạng thái')

    class Meta:
        verbose_name = 'Danh mục sự kiện'
        verbose_name_plural = 'Danh mục sự kiện'
        ordering = ['priority']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('event-category-list')

class JobCategory(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class Event(models.Model):
    category = models.ForeignKey(EventCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, unique=True)
    uid = models.PositiveIntegerField(unique=True)
    description = RichTextUploadingField()
    job_category = models.ForeignKey(JobCategory, on_delete=models.CASCADE)
    select_scheduled_status = (
        ('yet to scheduled', 'Chưa lên lịch'),
        ('scheduled', 'Đã lên lịch')
    )
    scheduled_status = models.CharField(max_length=25, choices=select_scheduled_status)
    venue = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    location = LocationField()
    points = models.PositiveIntegerField()
    maximum_attende = models.PositiveIntegerField()
    created_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, blank=True, null=True, related_name='event_created_user')
    updated_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, blank=True, null=True, related_name='event_updated_user')
    created_date = models.DateField(auto_now_add=True)
    updated_date = models.DateField(auto_now_add=True)
    status_choice = (
        ('disabled', 'Vô hiệu hóa'),
        ('active', 'Đang hoạt động'),
        ('deleted', 'Đã xóa'),
        ('time out', 'Hết hạn'),
        ('completed', 'Đã hoàn thành'),
        ('cancel', 'Đã hủy'),
    )
    status = models.CharField(choices=status_choice, max_length=10)

    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('event-list')
    
    def created_updated(model, request):
        obj = model.objects.latest('pk')
        if obj.created_by is None:
            obj.created_by = request.user
        obj.updated_by = request.user
        obj.save()

    @property
    def registered_count(self):
        return self.eventmember_set.exclude(attend_status='cancelled').count()

    @property
    def remaining_seats(self):
        return max(0, int(self.maximum_attende or 0) - self.registered_count)

    @property
    def occupancy_percent(self):
        if not self.maximum_attende:
            return 0
        return min(100, round(self.registered_count / self.maximum_attende * 100))

    @property
    def is_full(self):
        return self.registered_count >= int(self.maximum_attende or 0)

    @property
    def is_expired(self):
        return (self.end_date and self.end_date < date.today()) or self.status in ('completed', 'time out', 'cancel', 'deleted', 'disabled')

    @property
    def can_register(self):
        return self.status == 'active' and not self.is_expired and not self.is_full

    @property
    def average_rating(self):
        avg = self.feedbacks.aggregate(avg_val=Avg('rating'))['avg_val']
        return round(avg, 1) if avg else 0.0

    @property
    def feedback_count(self):
        return self.feedbacks.count()

    @property
    def coords(self):
        """
        Trả về tuple (lat, lng) từ LocationField hoặc tọa độ mặc định tại Đà Nẵng.
        Mapbox LocationField thường lưu dạng 'lng,lat' hoặc 'lat,lng'.
        """
        default_lat, default_lng = 16.047079, 108.220832  # ĐH Kiến Trúc Đà Nẵng
        if not self.location:
            return (default_lat, default_lng)
        try:
            parts = [float(p.strip()) for p in str(self.location).split(',')]
            if len(parts) == 2:
                a, b = parts[0], parts[1]
                if -90 <= a <= 90 and -180 <= b <= 180:
                    return (a, b)
                if -90 <= b <= 90 and -180 <= a <= 180:
                    return (b, a)
        except (ValueError, TypeError):
            pass
        return (default_lat, default_lng)

    @property
    def latitude(self):
        return self.coords[0]

    @property
    def longitude(self):
        return self.coords[1]

class EventImage(models.Model):
    event = models.OneToOneField(Event, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='event_image/')


class EventAgenda(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    session_name = models.CharField(max_length=120)
    speaker_name = models.CharField(max_length=120)
    start_time = models.TimeField()
    end_time = models.TimeField()
    venue_name = models.CharField(max_length=255)


class EventJobCategoryLinking(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    job_category = models.ForeignKey(JobCategory, on_delete=models.CASCADE)
    status_choice = (
        ('disabled', 'Vô hiệu hóa'),
        ('active', 'Hoạt động'),
        ('deleted', 'Đã xóa'),
        ('blocked', 'Đã khóa'),
        ('completed', 'Hoàn thành'),
    )
    status = models.CharField(choices=status_choice, max_length=10)

    def __str__(self):
        return str(self.event)


class EventMember(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    attend_status_choice = (
        ('waiting', 'Chờ điểm danh'),
        ('attending', 'Đã điểm danh'),
        ('completed', 'Hoàn thành'),
        ('absent', 'Vắng mặt'),
        ('cancelled', 'Đã hủy'),
    )
    attend_status = models.CharField(choices=attend_status_choice, max_length=10)
    created_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='eventmember_created_user')
    updated_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='eventmember_updated_user')
    created_date = models.DateField(auto_now_add=True)
    updated_date = models.DateField(auto_now_add=True)
    status_choice = (
        ('disabled', 'Vô hiệu hóa'),
        ('active', 'Hoạt động'),
        ('deleted', 'Đã xóa'),
        ('blocked', 'Đã khóa'),
        ('completed', 'Hoàn thành'),
    )
    status = models.CharField(choices=status_choice, max_length=10)


    class Meta:
        unique_together = ['event', 'user']

    def __str__(self):
        return str(self.user)
    
    def get_absolute_url(self):
        return reverse('join-event-list')

    @property
    def security_token(self):
        raw = f"DAU-EVT-{self.event_id}-MEM-{self.id}-USR-{self.user_id}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:4].upper()

    @property
    def ticket_code(self):
        return f"EVT{self.event.id:04d}-MEM{self.id:04d}"

    @property
    def secure_ticket_code(self):
        return f"EVT{self.event.id:04d}-MEM{self.id:04d}-{self.security_token}"

    @property
    def certificate_code(self):
        return f"CERT-DAU-{self.event.id:04d}-{self.id:04d}-{self.security_token}"

    @property
    def is_checked_in(self):
        return self.attend_status in ('attending', 'completed', 'present')


class EventUserWishList(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='eventwishlist_created_user')
    updated_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='eventwishlist_updated_user')
    created_date = models.DateField(auto_now_add=True)
    updated_date = models.DateField(auto_now_add=True)
    status_choice = (
        ('disabled', 'Disabled'),
        ('active', 'Active'),
        ('deleted', 'Deleted'),
        ('blocked', 'Blocked'),
        ('completed', 'Completed'),
    )
    status = models.CharField(choices=status_choice, max_length=10)


    class Meta:
        unique_together = ['event', 'user']

    def __str__(self):
        return str(self.event)
    
    def get_absolute_url(self):
        return reverse('event-wish-list')


class UserCoin(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    CHOICE_GAIN_TYPE = (
        ('event', 'Event'),
        ('others', 'Others'),
    )
    gain_type = models.CharField(max_length=6, choices=CHOICE_GAIN_TYPE)
    gain_coin = models.PositiveIntegerField()
    created_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='usercoin_created_user')
    updated_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='usercoin_updated_user')
    created_date = models.DateField(auto_now_add=True)
    updated_date = models.DateField(auto_now_add=True)
    status_choice = (
        ('disabled', 'Disabled'),
        ('active', 'Active'),
        ('deleted', 'Deleted'),
        ('blocked', 'Blocked'),
        ('completed', 'Completed'),
    )
    status = models.CharField(choices=status_choice, max_length=10)

    def __str__(self):
        return str(self.user)
    
    def get_absolute_url(self):
        return reverse('user-mark')


class UserProfile(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

    @property
    def avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            try:
                return self.avatar.url
            except ValueError:
                pass
        return '/static/img/user.jpg'


class Notification(models.Model):
    """
    Thông báo hệ thống cho người dùng.
    Được tạo tự động khi có sự kiện: đăng ký tham gia, nhắc nhở, điểm danh, v.v.
    """
    NOTIF_TYPE_CHOICES = (
        ('registration', 'Đăng ký sự kiện'),
        ('reminder', 'Nhắc nhở sự kiện'),
        ('checkin', 'Điểm danh'),
        ('system', 'Hệ thống'),
        ('event_new', 'Sự kiện mới'),
    )

    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255, verbose_name='Tiêu đề')
    message = models.TextField(verbose_name='Nội dung')
    notif_type = models.CharField(max_length=20, choices=NOTIF_TYPE_CHOICES, default='system', verbose_name='Loại')
    is_read = models.BooleanField(default=False, verbose_name='Đã đọc')
    link = models.CharField(max_length=500, blank=True, null=True, verbose_name='Đường dẫn')
    event = models.ForeignKey('Event', on_delete=models.SET_NULL, blank=True, null=True, verbose_name='Sự kiện liên quan')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')

    class Meta:
        verbose_name = 'Thông báo'
        verbose_name_plural = 'Thông báo'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_notif_type_display()}] {self.title} → {self.user.username}"


class NotificationSetting(models.Model):
    """
    Cài đặt nhận thông báo email cho từng người dùng.
    """
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='notification_setting')
    email_notification = models.BooleanField(default=True, verbose_name='Thông báo email')
    event_reminder = models.BooleanField(default=True, verbose_name='Nhắc nhở sự kiện')
    points_notification = models.BooleanField(default=False, verbose_name='Thông báo điểm thưởng')

    class Meta:
        verbose_name = 'Cài đặt thông báo'
        verbose_name_plural = 'Cài đặt thông báo'

    def __str__(self):
        return f"NotifSetting of {self.user.username}"


class EventFeedback(models.Model):
    """
    Đánh giá & Phản hồi của người tham dự sau khi tham gia sự kiện.
    """
    event = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='feedbacks', verbose_name='Sự kiện')
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='event_feedbacks', verbose_name='Người đánh giá')
    rating = models.PositiveSmallIntegerField(default=5, verbose_name='Số sao (1-5)')
    comment = models.TextField(verbose_name='Nhận xét / Góp ý')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày đánh giá')

    class Meta:
        verbose_name = 'Đánh giá sự kiện'
        verbose_name_plural = 'Đánh giá sự kiện'
        unique_together = ['event', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.event.name} ({self.rating}★)"


class PasswordResetOTP(models.Model):
    """
    Mã xác thực OTP 6 chữ số gửi qua email khi người dùng quên mật khẩu.
    """
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='reset_otps', verbose_name='Người dùng')
    otp_code = models.CharField(max_length=6, verbose_name='Mã OTP')
    is_used = models.BooleanField(default=False, verbose_name='Đã sử dụng')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian tạo')

    class Meta:
        verbose_name = 'Mã OTP đặt lại mật khẩu'
        verbose_name_plural = 'Mã OTP đặt lại mật khẩu'
        ordering = ['-created_at']

    def is_valid(self):
        return (not self.is_used) and (timezone.now() - self.created_at <= timedelta(minutes=10))

    def __str__(self):
        return f"OTP {self.otp_code} cho {self.user.username}"










