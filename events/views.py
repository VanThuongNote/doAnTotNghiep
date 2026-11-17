from datetime import date, datetime, timedelta
import io
import json
from urllib.parse import quote

from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DetailView,
    DeleteView,
)
from django.conf import settings
from django.urls import reverse, reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q, Avg, Count

from .models import (
    EventCategory,
    Event,
    JobCategory,
    EventJobCategoryLinking,
    EventMember,
    EventUserWishList,
    UserCoin,
    EventImage,
    EventAgenda,
    EventFeedback,
)
from .forms import (
    EventForm,
    EventImageForm,
    EventAgendaForm,
    EventCreateMultiForm,
    EventCategoryForm,
    EventMemberForm,
    EventUserWishListForm,
    UserCoinForm,
    EventFeedbackForm,
)
from .qr_utils import generate_qr_base64


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and (self.request.user.is_staff or self.request.user.is_superuser)

    def handle_no_permission(self):
        messages.error(self.request, "Chỉ tài khoản Quản trị viên (Admin) mới có quyền thực hiện thao tác này!")
        return redirect('dashboard')


def admin_required(view_func):
    @login_required(login_url='login')
    def _wrapped_view(request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, "Chỉ tài khoản Quản trị viên (Admin) mới có quyền thực hiện thao tác này!")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def _build_google_calendar_url(event: Event) -> str:
    """Tạo link thêm nhanh sự kiện vào Google Calendar."""
    start_str = event.start_date.strftime('%Y%m%d') if event.start_date else ''
    end_dt = (event.end_date + timedelta(days=1)) if event.end_date else date.today()
    end_str = end_dt.strftime('%Y%m%d')
    title = quote(event.name or 'Sự kiện')
    location = quote(event.venue or '')
    details = quote(f"Sự kiện: {event.name} | Địa điểm: {event.venue}")
    return (
        f"https://calendar.google.com/calendar/render?action=TEMPLATE"
        f"&text={title}&dates={start_str}/{end_str}&details={details}&location={location}"
    )


def _award_or_revoke_event_points(member: EventMember, actor_user, revoke: bool = False) -> int:
    """
    Tự động cộng hoặc thu hồi điểm thưởng (UserCoin) khi điểm danh / hủy điểm danh.
    Trả về số điểm thay đổi.
    """
    points = int(member.event.points or 0)
    if points <= 0:
        return 0

    coin_obj, created = UserCoin.objects.get_or_create(
        user=member.user,
        defaults={
            'gain_type': 'event',
            'gain_coin': 0,
            'status': 'active',
            'created_user': actor_user,
            'updated_user': actor_user,
        }
    )
    if revoke:
        coin_obj.gain_coin = max(0, int(coin_obj.gain_coin or 0) - points)
        coin_obj.updated_user = actor_user
        coin_obj.save()
        return -points
    else:
        coin_obj.gain_coin = int(coin_obj.gain_coin or 0) + points
        coin_obj.gain_type = 'event'
        coin_obj.status = 'active'
        coin_obj.updated_user = actor_user
        coin_obj.save()
        return points


# ── Event Category Views ─────────────────────────────────────────────────────
class EventCategoryListView(LoginRequiredMixin, ListView):
    login_url = 'login'
    model = EventCategory
    template_name = 'events/event_category.html'
    context_object_name = 'event_category'
    paginate_by = 12


class EventCategoryCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    login_url = 'login'
    model = EventCategory
    form_class = EventCategoryForm
    template_name = 'events/create_event_category.html'

    def form_valid(self, form):
        form.instance.created_user = self.request.user
        form.instance.updated_user = self.request.user
        messages.success(self.request, f"Đã tạo danh mục '{form.instance.name}' thành công!")
        return super().form_valid(form)


class EventCategoryUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    login_url = 'login'
    model = EventCategory
    form_class = EventCategoryForm
    template_name = 'events/edit_event_category.html'

    def form_valid(self, form):
        form.instance.updated_user = self.request.user
        messages.success(self.request, f"Đã cập nhật danh mục '{form.instance.name}' thành công!")
        return super().form_valid(form)


class EventCategoryDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    login_url = 'login'
    model = EventCategory
    template_name = 'events/event_category_delete.html'
    success_url = reverse_lazy('event-category-list')


# ── Event CRUD Views ─────────────────────────────────────────────────────────
class EventCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    login_url = 'login'
    form_class = EventCreateMultiForm
    template_name = 'events/create_event.html'
    success_url = reverse_lazy('event-list')

    def form_valid(self, form):
        evt = form['event'].save(commit=False)
        evt.created_user = self.request.user
        evt.updated_user = self.request.user
        evt.save()

        image_form = form['event_image']
        if image_form.cleaned_data.get('image'):
            event_image = image_form.save(commit=False)
            event_image.event = evt
            event_image.save()

        agenda_form = form['event_agenda']
        if agenda_form.cleaned_data.get('session_name'):
            event_agenda = agenda_form.save(commit=False)
            event_agenda.event = evt
            event_agenda.save()

        self.object = evt
        messages.success(self.request, f"Đã tạo sự kiện '{evt.name}' thành công!")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        error_details = []
        for subform in form.forms.values():
            for field_name, errs in subform.errors.items():
                label = subform.fields[field_name].label if field_name in subform.fields else field_name
                for err in errs:
                    error_details.append(f"{label}: {err}")
        if error_details:
            messages.error(self.request, "Không thể tạo sự kiện — " + " | ".join(error_details))
        else:
            messages.error(self.request, "Không thể tạo sự kiện. Vui lòng kiểm tra lại các trường thông tin bị lỗi bên dưới.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ctg'] = EventCategory.objects.all()
        context['mapbox_key'] = getattr(settings, 'MAPBOX_KEY', '')
        return context


class EventListView(LoginRequiredMixin, ListView):
    login_url = 'login'
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'
    paginate_by = 12

    def get_queryset(self):
        return Event.objects.select_related('category', 'eventimage').order_by('-start_date', '-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['wished_event_ids'] = set(
                EventUserWishList.objects.filter(user=self.request.user).values_list('event_id', flat=True)
            )
            context['joined_event_ids'] = set(
                EventMember.objects.filter(user=self.request.user)
                .exclude(attend_status='cancelled')
                .values_list('event_id', flat=True)
            )
        else:
            context['wished_event_ids'] = set()
            context['joined_event_ids'] = set()
        return context


class EventUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    login_url = 'login'
    model = Event
    form_class = EventForm
    template_name = 'events/edit_event.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event_image_instance = EventImage.objects.filter(event=self.object).first()
        event_agenda_instance = EventAgenda.objects.filter(event=self.object).first()
        if self.request.POST:
            context['image_form'] = EventImageForm(
                self.request.POST, self.request.FILES, instance=event_image_instance, prefix='img'
            )
            context['agenda_form'] = EventAgendaForm(
                self.request.POST, instance=event_agenda_instance, prefix='agd'
            )
        else:
            context['image_form'] = EventImageForm(instance=event_image_instance, prefix='img')
            context['agenda_form'] = EventAgendaForm(instance=event_agenda_instance, prefix='agd')
        return context

    def form_valid(self, form):
        form.instance.updated_user = self.request.user
        response = super().form_valid(form)

        # Cập nhật ảnh banner nếu có gửi kèm
        event_image_instance = EventImage.objects.filter(event=self.object).first()
        if 'img-image' in self.request.FILES:
            img_form = EventImageForm(
                self.request.POST, self.request.FILES, instance=event_image_instance, prefix='img'
            )
            if img_form.is_valid():
                img_obj = img_form.save(commit=False)
                img_obj.event = self.object
                img_obj.save()

        # Cập nhật lịch trình (Agenda) nếu có dữ liệu
        if any(k.startswith('agd-') for k in self.request.POST.keys()):
            event_agenda_instance = EventAgenda.objects.filter(event=self.object).first()
            agenda_form = EventAgendaForm(self.request.POST, instance=event_agenda_instance, prefix='agd')
            if agenda_form.is_valid():
                agd_obj = agenda_form.save(commit=False)
                agd_obj.event = self.object
                agd_obj.save()

        messages.success(self.request, f"Đã cập nhật sự kiện '{self.object.name}' thành công!")
        return response


class EventDetailView(LoginRequiredMixin, DetailView):
    login_url = 'login'
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object
        user = self.request.user

        user_member = EventMember.objects.filter(
            event=event, user=user
        ).exclude(attend_status='cancelled').first()

        context['agendas'] = EventAgenda.objects.filter(event=event)
        context['user_member'] = user_member
        context['is_joined'] = user_member is not None
        context['is_wished'] = EventUserWishList.objects.filter(event=event, user=user).exists()
        context['feedbacks'] = EventFeedback.objects.filter(event=event).select_related('user')
        user_fb = EventFeedback.objects.filter(event=event, user=user).first()
        context['user_feedback'] = user_fb
        context['feedback_form'] = EventFeedbackForm(instance=user_fb)
        context['google_calendar_url'] = _build_google_calendar_url(event)
        return context


class EventDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    login_url = 'login'
    model = Event
    template_name = 'events/delete_event.html'
    success_url = reverse_lazy('event-list')


# ── Event Member & Registration Views ────────────────────────────────────────
class AddEventMemberCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    login_url = 'login'
    model = EventMember
    form_class = EventMemberForm
    template_name = 'events/add_event_member.html'

    def form_valid(self, form):
        form.instance.created_user = self.request.user
        form.instance.updated_user = self.request.user
        return super().form_valid(form)


class JoinEventListView(LoginRequiredMixin, ListView):
    login_url = 'login'
    model = EventMember
    template_name = 'events/joinevent_list.html'
    context_object_name = 'eventmember'
    paginate_by = 15

    def get_base_queryset(self):
        qs = EventMember.objects.select_related('event', 'user').exclude(attend_status='cancelled').order_by('-id')
        if not self.request.user.is_staff and not self.request.user.is_superuser:
            qs = qs.filter(user=self.request.user)
        event_id = self.request.GET.get('event_id')
        if event_id and str(event_id).isdigit():
            qs = qs.filter(event_id=int(event_id))
        return qs

    def get_queryset(self):
        qs = self.get_base_queryset()
        attend_status = self.request.GET.get('attend_status', '').strip()
        if attend_status:
            if attend_status == 'attending':
                qs = qs.filter(attend_status__in=['attending', 'completed', 'present'])
            else:
                qs = qs.filter(attend_status=attend_status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs = self.get_base_queryset()
        event_id = self.request.GET.get('event_id', '')
        context['events'] = Event.objects.all().order_by('-start_date', '-id')
        context['selected_event_id'] = int(event_id) if event_id and str(event_id).isdigit() else None
        context['selected_status'] = self.request.GET.get('attend_status', '').strip()
        context['total_count'] = base_qs.count()
        context['attended_count'] = base_qs.filter(attend_status__in=['attending', 'completed', 'present']).count()
        context['waiting_count'] = base_qs.filter(attend_status='waiting').count()
        context['absent_count'] = base_qs.filter(attend_status='absent').count()
        return context


class RemoveEventMemberDeleteView(LoginRequiredMixin, DeleteView):
    login_url = 'login'
    model = EventMember
    template_name = 'events/remove_event_member.html'
    success_url = reverse_lazy('join-event-list')

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return EventMember.objects.all()
        return EventMember.objects.filter(user=self.request.user)


# ── Wishlist Views ───────────────────────────────────────────────────────────
class EventUserWishListView(LoginRequiredMixin, ListView):
    login_url = 'login'
    model = EventUserWishList
    template_name = 'events/event_user_wish_list.html'
    context_object_name = 'eventwish'
    paginate_by = 15

    def get_queryset(self):
        qs = EventUserWishList.objects.select_related('event', 'user').order_by('-id')
        if not self.request.user.is_staff and not self.request.user.is_superuser:
            return qs.filter(user=self.request.user)
        return qs


class AddEventUserWishListCreateView(LoginRequiredMixin, CreateView):
    login_url = 'login'
    model = EventUserWishList
    form_class = EventUserWishListForm
    template_name = 'events/add_event_user_wish.html'

    def form_valid(self, form):
        form.instance.created_user = self.request.user
        form.instance.updated_user = self.request.user
        return super().form_valid(form)


class RemoveEventUserWishDeleteView(LoginRequiredMixin, DeleteView):
    """Cho phép người dùng tự xóa sự kiện khỏi danh sách yêu thích của mình (hoặc Admin xóa bất kỳ)."""
    login_url = 'login'
    model = EventUserWishList
    template_name = 'events/remove_event_user_wish.html'
    success_url = reverse_lazy('event-wish-list')

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return EventUserWishList.objects.all()
        return EventUserWishList.objects.filter(user=self.request.user)


@login_required(login_url='login')
def toggle_event_wishlist(request, pk):
    """Thả tim / Bỏ yêu thích sự kiện chỉ với 1 chạm (hỗ trợ cả AJAX và redirect)."""
    event = get_object_or_404(Event, pk=pk)
    wish_obj = EventUserWishList.objects.filter(event=event, user=request.user).first()
    if wish_obj:
        wish_obj.delete()
        wished = False
        msg = f"Đã xóa '{event.name}' khỏi danh sách yêu thích."
    else:
        EventUserWishList.objects.create(
            event=event,
            user=request.user,
            status='active',
            created_user=request.user,
            updated_user=request.user,
        )
        wished = True
        msg = f"Đã thêm '{event.name}' vào danh sách sự kiện yêu thích ❤️"

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok', 'wished': wished, 'message': msg})

    messages.success(request, msg)
    next_url = request.META.get('HTTP_REFERER') or reverse('event-detail', args=[event.pk])
    return redirect(next_url)


# ── Event Status & Completion Views ──────────────────────────────────────────
class UpdateEventStatusView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    login_url = 'login'
    model = Event
    fields = ['status']
    template_name = 'events/update_event_status.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"✅ Đã cập nhật trạng thái sự kiện '{self.object.name}' thành công!")
        if self.object.status in ['completed', 'time out']:
            return redirect('complete-event')
        return response


class CompleteEventList(LoginRequiredMixin, ListView):
    login_url = 'login'
    model = Event
    template_name = 'events/complete_event_list.html'
    context_object_name = 'events'
    paginate_by = 12

    def get_queryset(self):
        return Event.objects.filter(
            Q(status__iexact='completed') |
            Q(status__iexact='time out') |
            Q(status__icontains='hoàn thành') |
            Q(end_date__lte=date.today()) |
            Q(eventmember__attend_status__in=['completed', 'attending', 'present'])
        ).distinct().order_by('-id')


class AbsenseUserList(LoginRequiredMixin, ListView):
    login_url = 'login'
    model = EventMember
    template_name = 'events/absense_user_list.html'
    context_object_name = 'absenseuser'
    paginate_by = 15

    def get_queryset(self):
        qs = EventMember.objects.select_related('event', 'user').filter(attend_status='absent').order_by('-id')
        if not self.request.user.is_staff and not self.request.user.is_superuser:
            qs = qs.filter(user=self.request.user)
        event_id = self.request.GET.get('event_id')
        if event_id and str(event_id).isdigit():
            qs = qs.filter(event_id=int(event_id))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event_id = self.request.GET.get('event_id', '')
        context['events'] = Event.objects.all().order_by('-start_date', '-id')
        context['selected_event_id'] = int(event_id) if event_id and str(event_id).isdigit() else None
        return context


class CompleteEventUserList(LoginRequiredMixin, ListView):
    login_url = 'login'
    model = EventMember
    template_name = 'events/complete_event_user_list.html'
    context_object_name = 'completeuser'
    paginate_by = 15

    def get_queryset(self):
        qs = EventMember.objects.select_related('event', 'user').filter(
            Q(attend_status__iexact='completed') |
            Q(attend_status__iexact='attending') |
            Q(attend_status__iexact='present') |
            Q(attend_status__icontains='hoàn thành') |
            Q(attend_status__icontains='điểm danh') |
            Q(status__iexact='completed') |
            Q(event__status__iexact='completed') |
            Q(event__status__iexact='time out') |
            Q(event__end_date__lte=date.today())
        ).distinct().order_by('-id')
        if not self.request.user.is_staff and not self.request.user.is_superuser:
            qs = qs.filter(user=self.request.user)
        return qs


# ── Gamification / UserCoin Views ────────────────────────────────────────────
class CreateUserMark(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    login_url = 'login'
    model = UserCoin
    form_class = UserCoinForm
    template_name = 'events/create_user_mark.html'

    def form_valid(self, form):
        # Extract cleaned data
        target_user = form.cleaned_data['user']
        added_coins = int(form.cleaned_data.get('gain_coin') or 0)
        gain_type = form.cleaned_data.get('gain_type')
        status_val = form.cleaned_data.get('status')

        # Create or update UserCoin
        coin_obj, created = UserCoin.objects.get_or_create(
            user=target_user,
            defaults={
                'gain_type': gain_type,
                'gain_coin': added_coins,
                'status': status_val,
                'created_user': self.request.user,
                'updated_user': self.request.user,
            },
        )
        if not created:
            coin_obj.gain_coin = int(coin_obj.gain_coin or 0) + added_coins
            coin_obj.gain_type = gain_type
            coin_obj.status = status_val
            coin_obj.updated_user = self.request.user
            coin_obj.save()

        self.object = coin_obj
        messages.success(
            self.request,
            f"Đã cộng +{added_coins} điểm thưởng cho {target_user.username} (Tổng: {coin_obj.gain_coin} xu)!",
        )
        return redirect('user-mark')


class UserMarkList(LoginRequiredMixin, ListView):
    login_url = 'login'
    model = UserCoin
    template_name = 'events/user_mark_list.html'
    context_object_name = 'usermark'

    def get_queryset(self):
        if not self.request.user.is_staff and not self.request.user.is_superuser:
            return UserCoin.objects.filter(user=self.request.user)
        return UserCoin.objects.select_related('user').order_by('-gain_coin')


# ── Search Views ─────────────────────────────────────────────────────────────
@login_required(login_url='login')
def search_event_category(request):
    if request.method == 'POST':
        data = request.POST.get('search', '').strip()
        event_category = EventCategory.objects.filter(name__icontains=data)
        return render(request, 'events/event_category.html', {'event_category': event_category})
    return redirect('event-category-list')


@login_required(login_url='login')
def search_event(request):
    if request.method == 'POST':
        data = request.POST.get('search', '').strip()
        events = Event.objects.filter(
            Q(name__icontains=data) | Q(venue__icontains=data) | Q(category__name__icontains=data)
        ).distinct()
        return render(request, 'events/event_list.html', {'events': events})
    return redirect('event-list')


# ── Registration, QR Ticket & Check-in Views ─────────────────────────────────
@login_required(login_url='login')
def join_event_direct(request, pk):
    """
    Đăng ký tham gia sự kiện và phát vé QR.
    - Kiểm tra nếu đã đăng ký trước đó thì mở trang vé.
    - Kiểm tra trạng thái sự kiện, hạn đăng ký và giới hạn chỗ ngồi (maximum_attende).
    """
    event = get_object_or_404(Event, pk=pk)
    existing = EventMember.objects.filter(event=event, user=request.user).first()

    if existing and existing.attend_status != 'cancelled':
        messages.info(request, "Bạn đã đăng ký tham gia sự kiện này trước đó. Đây là vé QR của bạn.")
        return redirect('event-ticket', pk=existing.pk)

    # Kiểm tra trạng thái hoạt động và thời hạn của sự kiện
    if event.status != 'active' or event.is_expired:
        messages.error(
            request,
            f"Rất tiếc! Sự kiện '{event.name}' hiện không mở đăng ký (đã kết thúc hoặc đã đóng)."
        )
        return redirect('event-detail', pk=event.pk)

    # Kiểm tra số lượng chỗ tối đa (tránh Overbooking)
    if event.is_full:
        messages.error(
            request,
            f"Rất tiếc! Sự kiện '{event.name}' đã đủ số lượng tối đa ({event.maximum_attende} người tham gia)."
        )
        return redirect('event-detail', pk=event.pk)

    if existing and existing.attend_status == 'cancelled':
        existing.attend_status = 'waiting'
        existing.status = 'active'
        existing.updated_user = request.user
        existing.save()
        member = existing
    else:
        member = EventMember.objects.create(
            event=event,
            user=request.user,
            attend_status='waiting',
            status='active',
            created_user=request.user,
            updated_user=request.user,
        )

    messages.success(request, f"🎉 Đăng ký thành công sự kiện: {event.name}! Đã phát hành vé điện tử QR cho bạn.")

    from .notifications import create_notification, notify_admins_new_registration
    create_notification(
        user=request.user,
        title=f"Đăng ký thành công: {event.name}",
        message=f"Bạn đã đăng ký tham gia sự kiện \"{event.name}\" thành công. Mã vé: {member.ticket_code}.",
        notif_type='registration',
        event=event,
        link=f'/events/ticket/{member.pk}/',
    )
    notify_admins_new_registration(member)
    return redirect('event-ticket', pk=member.pk)


@login_required(login_url='login')
def cancel_event_registration(request, pk):
    """Cho phép người dùng tự hủy đăng ký tham gia khi chưa điểm danh."""
    member = get_object_or_404(EventMember, pk=pk)
    is_admin = request.user.is_staff or request.user.is_superuser

    if member.user != request.user and not is_admin:
        messages.error(request, "Bạn không có quyền hủy vé của người khác!")
        return redirect('my-tickets')

    if member.attend_status in ('attending', 'completed', 'present') and not is_admin:
        messages.warning(request, "Vé đã được điểm danh tham dự nên không thể hủy!")
        return redirect('event-ticket', pk=member.pk)

    event_name = member.event.name
    event_obj = member.event
    target_user = member.user
    member.delete()

    from .notifications import create_notification
    create_notification(
        user=target_user,
        title=f"Đã hủy đăng ký: {event_name}",
        message=f"Bạn đã hủy đăng ký tham gia sự kiện \"{event_name}\". Chỗ ngồi đã được hoàn trả cho hệ thống.",
        notif_type='system',
        event=event_obj,
        send_email=False,
    )
    messages.info(request, f"Đã hủy đăng ký tham gia sự kiện '{event_name}' thành công.")
    return redirect('my-tickets')


@login_required(login_url='login')
def event_ticket(request, pk):
    member = get_object_or_404(EventMember.objects.select_related('event', 'event__category', 'user'), pk=pk)
    if member.user != request.user and not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Bạn không có quyền xem vé này.")
        return redirect('event-list')

    checkin_url = f"{request.scheme}://{request.get_host()}{reverse('event-checkin')}?ticket={member.ticket_code}"
    qr_code_base64 = generate_qr_base64(checkin_url, box_size=8, border=3)

    context = {
        'member': member,
        'event': member.event,
        'ticket_code': member.ticket_code,
        'secure_ticket_code': member.secure_ticket_code,
        'qr_code_base64': qr_code_base64,
        'google_calendar_url': _build_google_calendar_url(member.event),
    }
    return render(request, 'events/event_ticket.html', context)


@login_required(login_url='login')
def event_certificate(request, pk):
    """
    Cấp Giấy chứng nhận tham gia sự kiện (Certificate of Attendance) cho thành viên đã điểm danh.
    """
    member = get_object_or_404(EventMember.objects.select_related('event', 'event__category', 'user'), pk=pk)
    if member.user != request.user and not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Bạn không có quyền truy cập giấy chứng nhận này.")
        return redirect('my-tickets')

    if not member.is_checked_in:
        messages.warning(
            request,
            "Giấy chứng nhận chỉ được cấp sau khi bạn đã điểm danh tham dự sự kiện!"
        )
        return redirect('event-ticket', pk=member.pk)

    verify_url = f"{request.scheme}://{request.get_host()}{reverse('event-certificate', args=[member.pk])}"
    qr_code_base64 = generate_qr_base64(verify_url, box_size=6, border=2)

    context = {
        'member': member,
        'event': member.event,
        'certificate_code': member.certificate_code,
        'qr_code_base64': qr_code_base64,
        'issued_date': member.updated_date or date.today(),
    }
    return render(request, 'events/event_certificate.html', context)


@login_required(login_url='login')
def my_tickets(request):
    tickets = (
        EventMember.objects.filter(user=request.user)
        .exclude(attend_status='cancelled')
        .select_related('event', 'event__category')
        .order_by('-created_date', '-id')
    )
    return render(request, 'events/my_tickets.html', {'tickets': tickets})


def _resolve_member_from_code(code_input: str):
    """Tìm EventMember từ mã vé dạng EVT0001-MEM0005(-XXXX) hoặc ID số."""
    if not code_input:
        return None
    raw = code_input.strip().upper()
    if 'MEM' in raw:
        after_mem = raw.split('MEM')[-1]
        num_part = after_mem.split('-')[0]
        if num_part.isdigit():
            return EventMember.objects.select_related('event', 'user').filter(pk=int(num_part)).first()
    if raw.isdigit():
        return EventMember.objects.select_related('event', 'user').filter(pk=int(raw)).first()
    return None


def _compute_checkin_stats(user, is_admin: bool, event_id=None):
    if is_admin:
        qs = EventMember.objects.all()
    else:
        qs = EventMember.objects.filter(user=user)
    if event_id and str(event_id).isdigit():
        qs = qs.filter(event_id=int(event_id))
    total_reg = qs.count()
    total_att = qs.filter(attend_status__in=['attending', 'completed', 'present']).count()
    total_wait = qs.filter(attend_status='waiting').count()
    total_abs = qs.filter(attend_status='absent').count()
    rate = round((total_att / total_reg * 100), 1) if total_reg > 0 else 0
    return {
        'total_registered': total_reg,
        'total_attended': total_att,
        'total_waiting': total_wait,
        'total_absent': total_abs,
        'attendance_rate': rate,
    }


@login_required(login_url='login')
def checkin_view(request):
    event_id = request.GET.get('event_id') or request.POST.get('event_id')
    search_ticket = request.GET.get('ticket', '').strip()
    is_admin = request.user.is_staff or request.user.is_superuser
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        action = request.POST.get('action', 'checkin')
        member_id = request.POST.get('member_id')
        code_input = request.POST.get('ticket_code', '').strip()
        next_url = request.POST.get('next', '').strip()

        # Đánh dấu vắng mặt hàng loạt cho tất cả thành viên đang ở trạng thái 'waiting'
        if action == 'mark_all_waiting_absent':
            if not is_admin:
                err_msg = "❌ Chỉ Quản trị viên (Admin) mới có quyền đánh dấu vắng mặt hàng loạt!"
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': err_msg}, status=403)
                messages.error(request, err_msg)
                return redirect(next_url or 'event-checkin')

            waiting_qs = EventMember.objects.filter(attend_status='waiting')
            if event_id and str(event_id).isdigit():
                waiting_qs = waiting_qs.filter(event_id=int(event_id))
            updated_count = waiting_qs.update(attend_status='absent')
            ok_msg = f"⚠️ Đã đánh dấu VẮNG MẶT cho {updated_count} thành viên chưa điểm danh!"
            if is_ajax:
                stats = _compute_checkin_stats(request.user, is_admin, event_id=event_id)
                return JsonResponse({'status': 'ok', 'message': ok_msg, 'stats': stats})
            messages.warning(request, ok_msg)
            if next_url:
                return redirect(next_url)
            return redirect(f"{request.path}?event_id={event_id}" if event_id else request.path)

        target_member = None
        if member_id and str(member_id).isdigit():
            target_member = EventMember.objects.select_related('event', 'user').filter(pk=int(member_id)).first()
        elif code_input:
            target_member = _resolve_member_from_code(code_input)

        if not target_member:
            err_msg = "Không tìm thấy mã vé hoặc thành viên hợp lệ!"
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': err_msg}, status=404)
            messages.error(request, err_msg)
        else:
            if not is_admin and target_member.user != request.user:
                err_msg = "❌ Bạn chỉ có thể điểm danh vé cho chính tài khoản của bạn!"
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': err_msg}, status=403)
                messages.error(request, err_msg)
                return redirect('event-checkin')

            was_checked_in = target_member.attend_status in ('attending', 'completed', 'present')
            points_delta = 0

            if action == 'cancel_checkin':
                if not is_admin:
                    err_msg = "❌ Chỉ Quản trị viên (Admin) mới có thể đặt lại trạng thái chờ!"
                    if is_ajax:
                        return JsonResponse({'status': 'error', 'message': err_msg}, status=403)
                    messages.error(request, err_msg)
                    return redirect('event-checkin')

                target_member.attend_status = 'waiting'
                target_member.updated_user = request.user
                target_member.save()
                if was_checked_in:
                    points_delta = _award_or_revoke_event_points(target_member, request.user, revoke=True)
                ok_msg = f"Đã chuyển về trạng thái Chờ điểm danh cho: {target_member.user.get_full_name() or target_member.user.username}"
                if not is_ajax:
                    messages.info(request, ok_msg)

            elif action == 'mark_absent':
                if not is_admin:
                    err_msg = "❌ Chỉ Quản trị viên (Admin) mới có thể đánh dấu vắng mặt!"
                    if is_ajax:
                        return JsonResponse({'status': 'error', 'message': err_msg}, status=403)
                    messages.error(request, err_msg)
                    return redirect('event-checkin')

                target_member.attend_status = 'absent'
                target_member.updated_user = request.user
                target_member.save()
                if was_checked_in:
                    points_delta = _award_or_revoke_event_points(target_member, request.user, revoke=True)
                ok_msg = f"⚠️ Đã đánh dấu VẮNG MẶT cho: {target_member.user.get_full_name() or target_member.user.username} (Vé #{target_member.ticket_code})"
                if not is_ajax:
                    messages.warning(request, ok_msg)

            else:
                target_member.attend_status = 'attending'
                target_member.updated_user = request.user
                target_member.save()

                if not was_checked_in:
                    points_delta = _award_or_revoke_event_points(target_member, request.user, revoke=False)
                    from .notifications import create_notification
                    pts_note = f" Bạn nhận được +{points_delta} điểm thưởng!" if points_delta > 0 else ""
                    create_notification(
                        user=target_member.user,
                        title=f"Điểm danh thành công: {target_member.event.name}",
                        message=(
                            f"Bạn đã điểm danh sự kiện \"{target_member.event.name}\" thành công. "
                            f"Mã vé: {target_member.ticket_code}.{pts_note}"
                        ),
                        notif_type='checkin',
                        event=target_member.event,
                        link=f'/events/certificate/{target_member.pk}/',
                    )
                pts_str = f" (+{points_delta} điểm thưởng)" if points_delta > 0 else ""
                ok_msg = (
                    f"✅ Điểm danh thành công! "
                    f"{target_member.user.get_full_name() or target_member.user.username} - "
                    f"Vé #{target_member.ticket_code}{pts_str}"
                )
                if not is_ajax:
                    messages.success(request, ok_msg)

            if is_ajax:
                stats = _compute_checkin_stats(request.user, is_admin, event_id=event_id)
                return JsonResponse({
                    'status': 'ok',
                    'message': ok_msg,
                    'member': {
                        'id': target_member.id,
                        'ticket_code': target_member.ticket_code,
                        'full_name': target_member.user.get_full_name() or target_member.user.username,
                        'username': target_member.user.username,
                        'event_name': target_member.event.name,
                        'attend_status': target_member.attend_status,
                        'points_delta': points_delta,
                    },
                    'stats': stats,
                })

            if next_url:
                return redirect(next_url)
            return redirect(f"{request.path}?event_id={target_member.event.id}" if target_member else request.path)

    scanned_member = None
    if search_ticket:
        scanned_member = _resolve_member_from_code(search_ticket)
        if scanned_member and not is_admin and scanned_member.user != request.user:
            scanned_member = None
            messages.error(request, "❌ Bạn không thể quét hoặc điểm danh vé của tài khoản khác.")

    if is_admin:
        queryset = EventMember.objects.select_related('event', 'user').all()
        events = Event.objects.all()
    else:
        queryset = EventMember.objects.select_related('event', 'user').filter(user=request.user)
        events = Event.objects.filter(eventmember__user=request.user).distinct()

    if event_id and str(event_id).isdigit():
        queryset = queryset.filter(event_id=int(event_id))

    stats = _compute_checkin_stats(request.user, is_admin, event_id=event_id)

    context = {
        'event_members': queryset.order_by('-id'),
        'events': events,
        'selected_event_id': int(event_id) if event_id and str(event_id).isdigit() else None,
        'scanned_member': scanned_member,
        'search_ticket': search_ticket,
        'total_registered': stats['total_registered'],
        'total_attended': stats['total_attended'],
        'total_waiting': stats['total_waiting'],
        'total_absent': stats['total_absent'],
        'attendance_rate': stats['attendance_rate'],
        'is_admin': is_admin,
    }
    return render(request, 'events/checkin.html', context)


# ── Export Excel (.xlsx) & Calendar (.ics) & Feedback Views (Phase 3) ────────
@login_required(login_url='login')
def export_event_members_excel(request):
    """
    Xuất danh sách người đăng ký & điểm danh ra file Excel (.xlsx) phục vụ báo cáo.
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    event_id = request.GET.get('event_id')
    is_admin = request.user.is_staff or request.user.is_superuser

    if is_admin:
        qs = EventMember.objects.select_related('event', 'event__category', 'user').all().order_by('event_id', 'id')
    else:
        qs = EventMember.objects.select_related('event', 'event__category', 'user').filter(user=request.user).order_by('-id')

    selected_event = None
    if event_id and str(event_id).isdigit():
        selected_event = Event.objects.filter(pk=int(event_id)).first()
        qs = qs.filter(event_id=int(event_id))

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Danh sach diem danh"

    # Styles
    title_font = Font(name='Arial', size=14, bold=True, color='FFFFFF')
    title_fill = PatternFill(start_color='4F46E5', end_color='4F46E5', fill_type='solid')
    header_font = Font(name='Arial', size=11, bold=True, color='1E293B')
    header_fill = PatternFill(start_color='E0E7FF', end_color='E0E7FF', fill_type='solid')
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1'),
    )

    # Dòng tiêu đề báo cáo
    ws.merge_cells('A1:J1')
    report_title = f"BÁO CÁO DANH SÁCH ĐĂNG KÝ & ĐIỂM DANH - {selected_event.name.upper()}" if selected_event else "BÁO CÁO TỔNG HỢP DANH SÁCH ĐĂNG KÝ & ĐIỂM DANH SỰ KIỆN"
    ws['A1'] = report_title
    ws['A1'].font = title_font
    ws['A1'].fill = title_fill
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 30

    ws.merge_cells('A2:J2')
    ws['A2'] = f"Ngày xuất báo cáo: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Người xuất: {request.user.get_full_name() or request.user.username}"
    ws['A2'].font = Font(name='Arial', size=10, italic=True, color='475569')
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[2].height = 20

    headers = [
        'STT', 'Mã Vé', 'Họ và Tên', 'Tài khoản', 'Email',
        'Sự kiện', 'Danh mục', 'Ngày bắt đầu', 'Trạng thái điểm danh', 'Ngày đăng ký'
    ]
    ws.append([])  # Row 3 trống
    ws.append(headers)  # Row 4 header
    ws.row_dimensions[4].height = 24

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=4, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = thin_border

    status_map = {
        'waiting': 'Chờ điểm danh',
        'attending': 'Đã điểm danh',
        'completed': 'Hoàn thành',
        'present': 'Đã điểm danh',
        'absent': 'Vắng mặt',
        'cancelled': 'Đã hủy',
    }

    for idx, m in enumerate(qs, start=1):
        row_data = [
            idx,
            m.ticket_code,
            m.user.get_full_name() or m.user.username,
            m.user.username,
            m.user.email or '',
            m.event.name,
            m.event.category.name if m.event.category else '',
            m.event.start_date.strftime('%d/%m/%Y') if m.event.start_date else '',
            status_map.get(m.attend_status, m.attend_status),
            m.created_date.strftime('%d/%m/%Y') if m.created_date else '',
        ]
        ws.append(row_data)
        row_num = 4 + idx
        for col_idx in range(1, len(headers) + 1):
            c = ws.cell(row=row_num, column=col_idx)
            c.border = thin_border
            c.font = Font(name='Arial', size=10)
            if col_idx in (1, 2, 8, 9, 10):
                c.alignment = Alignment(horizontal='center', vertical='center')

    # Tự động căn chỉnh độ rộng cột
    col_widths = [6, 18, 24, 16, 26, 32, 18, 14, 18, 14]
    for i, w in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"diem_danh_su_kien_{selected_event.id}.xlsx" if selected_event else "danh_sach_diem_danh_su_kien.xlsx"
    response = HttpResponse(
        buf.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required(login_url='login')
def export_event_ics(request, pk):
    """Xuất file lịch chuẩn iCalendar (.ics) để thêm vào Apple Calendar / Outlook / Google Calendar."""
    event = get_object_or_404(Event, pk=pk)
    dt_start = event.start_date.strftime('%Y%m%d') if event.start_date else date.today().strftime('%Y%m%d')
    dt_end = ((event.end_date or event.start_date) + timedelta(days=1)).strftime('%Y%m%d')
    now_stamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')

    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//DAU Event Management//VN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:event-{event.id}-uid-{event.uid}@dau-events.local",
        f"DTSTAMP:{now_stamp}",
        f"DTSTART;VALUE=DATE:{dt_start}",
        f"DTEND;VALUE=DATE:{dt_end}",
        f"SUMMARY:{event.name}",
        f"LOCATION:{event.venue}",
        f"DESCRIPTION:Sự kiện: {event.name} - Địa điểm: {event.venue} (+{event.points} điểm thưởng)",
        "STATUS:CONFIRMED",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    ics_content = "\r\n".join(ics_lines)
    response = HttpResponse(ics_content, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="event_{event.id}.ics"'
    return response


@login_required(login_url='login')
def submit_event_feedback(request, pk):
    """Gửi hoặc cập nhật đánh giá sao & nhận xét cho sự kiện."""
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        existing_fb = EventFeedback.objects.filter(event=event, user=request.user).first()
        form = EventFeedbackForm(request.POST, instance=existing_fb)
        if form.is_valid():
            fb = form.save(commit=False)
            fb.event = event
            fb.user = request.user
            fb.save()
            messages.success(request, f"⭐ Cảm ơn bạn đã gửi đánh giá ({fb.rating} sao) cho sự kiện '{event.name}'!")
        else:
            messages.error(request, "Vui lòng kiểm tra lại thông tin đánh giá.")
    return redirect('event-detail', pk=event.pk)


@login_required(login_url='login')
def event_calendar_view(request):
    """
    Trang Lịch Sự Kiện Tương Tác (FullCalendar) & Bản Đồ Tổng Thể (Leaflet OpenStreetMap).
    Hiển thị trực quan toàn bộ sự kiện theo Tháng/Tuần/Danh sách và vị trí địa lý trên bản đồ.
    """
    events_qs = Event.objects.select_related('category', 'job_category', 'eventimage').order_by('start_date', 'id')
    categories = EventCategory.objects.filter(status='active').order_by('priority', 'id')

    joined_ids = set(
        EventMember.objects.filter(user=request.user)
        .exclude(attend_status='cancelled')
        .values_list('event_id', flat=True)
    )
    wished_ids = set(
        EventUserWishList.objects.filter(user=request.user).values_list('event_id', flat=True)
    )

    palette = [
        '#4f46e5', '#0ea5e9', '#10b981', '#8b5cf6',
        '#f59e0b', '#ec4899', '#ef4444', '#14b8a6',
    ]
    cat_colors = {}
    for idx, cat in enumerate(categories):
        cat_colors[cat.id] = palette[idx % len(palette)]

    events_data = []
    for idx, ev in enumerate(events_qs):
        color = cat_colors.get(ev.category_id, palette[idx % len(palette)])
        start_str = ev.start_date.strftime('%Y-%m-%d') if ev.start_date else date.today().strftime('%Y-%m-%d')
        end_exclusive = ((ev.end_date or ev.start_date or date.today()) + timedelta(days=1)).strftime('%Y-%m-%d')
        img_url = ''
        try:
            if hasattr(ev, 'eventimage') and ev.eventimage and ev.eventimage.image:
                img_url = ev.eventimage.image.url
        except Exception:
            img_url = ''

        # Nếu nhiều sự kiện có cùng tọa độ mặc định thì dịch nhẹ vài trăm mét để các ghim trên bản đồ không đè khít lên nhau
        lat, lng = ev.latitude, ev.longitude
        if abs(lat - 16.047079) < 0.0001 and abs(lng - 108.220832) < 0.0001 and idx > 0:
            offsets = [
                (0.0, 0.0), (0.0045, 0.0035), (-0.0038, 0.0042), (0.0052, -0.0030),
                (-0.0045, -0.0038), (0.0070, 0.0015), (-0.0060, 0.0025), (0.0025, -0.0055),
            ]
            dlat, dlng = offsets[idx % len(offsets)]
            lat = round(lat + dlat, 6)
            lng = round(lng + dlng, 6)

        events_data.append({
            'id': ev.id,
            'title': ev.name,
            'start': start_str,
            'end': end_exclusive,
            'start_display': ev.start_date.strftime('%d/%m/%Y') if ev.start_date else '',
            'end_display': ev.end_date.strftime('%d/%m/%Y') if ev.end_date else '',
            'category_id': ev.category_id,
            'category_name': ev.category.name if ev.category else 'Khác',
            'category_code': ev.category.code if ev.category else 'EVT',
            'color': color,
            'venue': ev.venue,
            'lat': lat,
            'lng': lng,
            'points': ev.points,
            'registered_count': ev.registered_count,
            'maximum_attende': ev.maximum_attende,
            'remaining_seats': ev.remaining_seats,
            'is_full': ev.is_full,
            'is_expired': ev.is_expired,
            'can_register': ev.can_register,
            'status': ev.status,
            'is_joined': ev.id in joined_ids,
            'is_wished': ev.id in wished_ids,
            'image_url': img_url,
            'detail_url': reverse('event-detail', args=[ev.id]),
            'join_url': reverse('join-event', args=[ev.id]),
            'ics_url': reverse('export-event-ics', args=[ev.id]),
            'google_calendar_url': _build_google_calendar_url(ev),
            'maps_url': f"https://www.google.com/maps/search/?api=1&query={lat},{lng}",
        })

    if request.GET.get('format') == 'json':
        return JsonResponse({'events': events_data})

    context = {
        'events': events_qs,
        'categories': categories,
        'events_json': json.dumps(events_data, ensure_ascii=False),
        'total_events': len(events_data),
        'open_events_count': sum(1 for e in events_data if e['can_register']),
        'joined_events_count': len(joined_ids),
    }
    return render(request, 'events/event_calendar.html', context)
