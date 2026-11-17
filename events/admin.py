from django.contrib import admin
from mapbox_location_field.admin import MapAdmin

from .models import (
    EventCategory,
    Event,
    EventImage,
    EventAgenda,
    JobCategory,
    EventJobCategoryLinking,
    EventMember,
    EventUserWishList,
    UserCoin,
    UserProfile,
    Notification,
    NotificationSetting,
    EventFeedback,
    PasswordResetOTP,
)


@admin.register(EventCategory)
class EventCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'priority', 'status', 'created_date')
    search_fields = ('name', 'code')
    list_filter = ('status',)


@admin.register(Event)
class EventAdmin(MapAdmin):
    list_display = ('name', 'category', 'venue', 'start_date', 'end_date', 'maximum_attende', 'points', 'status')
    search_fields = ('name', 'venue')
    list_filter = ('status', 'category', 'scheduled_status')


@admin.register(EventMember)
class EventMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'attend_status', 'status', 'created_date')
    list_editable = ('attend_status', 'status')
    search_fields = ('user__username', 'user__email', 'event__name')
    list_filter = ('attend_status', 'status', 'event')
    actions = ['mark_as_attending', 'mark_as_absent', 'mark_as_waiting']

    @admin.action(description='✅ Đánh dấu Đã điểm danh (Attending)')
    def mark_as_attending(self, request, queryset):
        queryset.update(attend_status='attending')

    @admin.action(description='⚠️ Đánh dấu Vắng mặt (Absent)')
    def mark_as_absent(self, request, queryset):
        queryset.update(attend_status='absent')

    @admin.action(description='⏳ Đặt lại Chờ điểm danh (Waiting)')
    def mark_as_waiting(self, request, queryset):
        queryset.update(attend_status='waiting')


@admin.register(EventFeedback)
class EventFeedbackAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'event')
    search_fields = ('user__username', 'event__name', 'comment')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'notif_type', 'is_read', 'created_at')
    list_filter = ('notif_type', 'is_read')
    search_fields = ('title', 'message', 'user__username')


admin.site.register(JobCategory)
admin.site.register(EventJobCategoryLinking)
admin.site.register(EventImage)
admin.site.register(EventAgenda)
admin.site.register(EventUserWishList)
admin.site.register(UserCoin)
admin.site.register(UserProfile)
admin.site.register(NotificationSetting)
admin.site.register(PasswordResetOTP)
