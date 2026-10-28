from django import forms
from betterforms.multiform import MultiModelForm

from .models import (
    Event,
    EventImage,
    EventAgenda,
    EventCategory,
    EventMember,
    EventUserWishList,
    UserCoin
)


class EventForm(forms.ModelForm):

    class Meta:
        model = Event
        fields = ['category', 'name', 'uid', 'description', 'job_category', 'scheduled_status', 'venue', 'start_date', 'end_date', 'location', 'points', 'maximum_attende', 'status']
        labels = {
            'category': 'Danh mục sự kiện',
            'name': 'Tên sự kiện',
            'uid': 'Mã UID sự kiện',
            'description': 'Mô tả sự kiện',
            'job_category': 'Danh mục ngành nghề',
            'scheduled_status': 'Trạng thái lên lịch',
            'venue': 'Địa điểm tổ chức',
            'start_date': 'Ngày bắt đầu',
            'end_date': 'Ngày kết thúc',
            'location': 'Vị trí bản đồ',
            'points': 'Điểm thưởng tham gia',
            'maximum_attende': 'Số người tham gia tối đa',
            'status': 'Trạng thái hoạt động',
        }
        widgets = {
            'start_date': forms.TextInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.TextInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class EventImageForm(forms.ModelForm):

    class Meta:
        model = EventImage
        fields = ['image']
        labels = {
            'image': 'Hình ảnh banner sự kiện',
        }


class EventAgendaForm(forms.ModelForm):

    class Meta:
        model = EventAgenda
        fields = ['session_name', 'speaker_name', 'start_time', 'end_time', 'venue_name']
        labels = {
            'session_name': 'Tên phiên / Chủ đề',
            'speaker_name': 'Tên diễn giả',
            'start_time': 'Giờ bắt đầu',
            'end_time': 'Giờ kết thúc',
            'venue_name': 'Tên địa điểm / Phòng họp',
        }
        widgets = {
            'start_time': forms.TextInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TextInput(attrs={'class': 'form-control', 'type': 'time'}),
        }


class EventCreateMultiForm(MultiModelForm):
    form_classes = {
        'event': EventForm,
        'event_image': EventImageForm,
        'event_agenda': EventAgendaForm,
    }


class EventCategoryForm(forms.ModelForm):
    class Meta:
        model = EventCategory
        fields = ['name', 'code', 'image', 'priority', 'status']
        labels = {
            'name': 'Tên danh mục',
            'code': 'Mã danh mục',
            'image': 'Hình ảnh đại diện',
            'priority': 'Thứ tự ưu tiên',
            'status': 'Trạng thái hoạt động',
        }


class EventMemberForm(forms.ModelForm):
    class Meta:
        model = EventMember
        fields = ['event', 'user', 'attend_status', 'status']
        labels = {
            'event': 'Chọn sự kiện',
            'user': 'Chọn người dùng / thành viên',
            'attend_status': 'Trạng thái điểm danh',
            'status': 'Trạng thái tài khoản',
        }


class EventUserWishListForm(forms.ModelForm):
    class Meta:
        model = EventUserWishList
        fields = ['event', 'user', 'status']
        labels = {
            'event': 'Sự kiện yêu thích',
            'user': 'Người dùng',
            'status': 'Trạng thái',
        }


class UserCoinForm(forms.ModelForm):
    class Meta:
        model = UserCoin
        fields = ['user', 'gain_type', 'gain_coin', 'status']
        labels = {
            'user': 'Người dùng',
            'gain_type': 'Loại tích điểm',
            'gain_coin': 'Số điểm thưởng (Xu)',
            'status': 'Trạng thái',
        }