from django import forms
from betterforms.multiform import MultiModelForm

from .models import (
    Event,
    EventImage,
    EventAgenda,
    EventCategory,
    EventMember,
    EventUserWishList,
    UserCoin,
    EventFeedback,
)


class EventForm(forms.ModelForm):

    class Meta:
        model = Event
        fields = [
            'category', 'name', 'uid', 'description', 'job_category',
            'scheduled_status', 'venue', 'start_date', 'end_date',
            'location', 'points', 'maximum_attende', 'status'
        ]
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
            'start_date': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['location'].required = False
        if not self.initial.get('location'):
            self.fields['location'].initial = '108.220832,16.047079'
        self.fields['location'].widget.attrs.pop('readonly', None)
        self.fields['location'].widget.attrs['placeholder'] = '108.220832,16.047079 (Mặc định: ĐH Kiến Trúc Đà Nẵng)'

    def clean_location(self):
        location = self.cleaned_data.get('location')
        if not location:
            return '108.220832,16.047079'
        return location

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'Ngày kết thúc không được nhỏ hơn ngày bắt đầu!')
        return cleaned_data


class EventImageForm(forms.ModelForm):
    image = forms.ImageField(required=False, label='Hình ảnh banner sự kiện')

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
            'start_time': forms.TimeInput(format='%H:%M', attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(format='%H:%M', attrs={'class': 'form-control', 'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

    def clean(self):
        cleaned_data = super().clean()
        fields = ['session_name', 'speaker_name', 'start_time', 'end_time', 'venue_name']
        has_any = any(cleaned_data.get(f) for f in fields)
        if has_any:
            for f in fields:
                if not cleaned_data.get(f):
                    self.add_error(f, 'Vui lòng điền đầy đủ thông tin lịch trình hoặc để trống tất cả.')
        return cleaned_data


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
            'gain_coin': 'Số điểm thưởng cộng thêm (Xu)',
            'status': 'Trạng thái',
        }

    def validate_unique(self):
        # Cho phép chọn user đã có bản ghi UserCoin để cộng dồn điểm
        exclude = self._get_validation_exclusions()
        if isinstance(exclude, set):
            exclude.add('user')
        elif 'user' not in exclude:
            exclude.append('user')
        try:
            self.instance.validate_unique(exclude=exclude)
        except forms.ValidationError as e:
            self._update_errors(e)


class EventFeedbackForm(forms.ModelForm):
    class Meta:
        model = EventFeedback
        fields = ['rating', 'comment']
        labels = {
            'rating': 'Đánh giá chất lượng (1 - 5 sao)',
            'comment': 'Nhận xét & góp ý của bạn',
        }
        widgets = {
            'rating': forms.Select(
                choices=[
                    (5, '⭐⭐⭐⭐⭐ (5 sao - Tuyệt vời)'),
                    (4, '⭐⭐⭐⭐ (4 sao - Rất tốt)'),
                    (3, '⭐⭐⭐ (3 sao - Bình thường)'),
                    (2, '⭐⭐ (2 sao - Cần cải thiện)'),
                    (1, '⭐ (1 sao - Chưa hài lòng)'),
                ],
                attrs={'class': 'form-control'}
            ),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Chia sẻ cảm nhận của bạn về nội dung, diễn giả, công tác tổ chức...'
            }),
        }
