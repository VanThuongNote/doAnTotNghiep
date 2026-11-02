from django.db import models
from django.urls import reverse
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
    def ticket_code(self):
        return f"EVT{self.event.id:04d}-MEM{self.id:04d}"


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









