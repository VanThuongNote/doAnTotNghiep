from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DetailView,
    DeleteView,
    View,
)
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

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

from .models import (
    EventCategory,
    Event,
    JobCategory,
    EventJobCategoryLinking,
    EventMember,
    EventUserWishList,
    UserCoin,
    EventImage,
    EventAgenda

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
)


# Event category list view
class EventCategoryListView(LoginRequiredMixin, ListView):
    login_url = 'login'
    model = EventCategory
    template_name = 'events/event_category.html'
    context_object_name = 'event_category'


class EventCategoryCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    login_url = 'login'
    model = EventCategory
    form_class = EventCategoryForm
    template_name = 'events/create_event_category.html'

    def form_valid(self, form):
        form.instance.created_user = self.request.user
        form.instance.updated_user = self.request.user
        return super().form_valid(form)


class EventCategoryUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    login_url = 'login'
    model = EventCategory
    form_class = EventCategoryForm
    template_name = 'events/edit_event_category.html'


class EventCategoryDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    login_url = 'login'
    model =  EventCategory
    template_name = 'events/event_category_delete.html'
    success_url = reverse_lazy('event-category-list')


class EventCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    login_url = 'login'
    form_class = EventCreateMultiForm
    template_name = 'events/create_event.html'
    success_url = reverse_lazy('event-list')

    def form_valid(self, form):
        evt = form['event'].save()
        event_image = form['event_image'].save(commit=False)
        event_image.event = evt
        event_image.save()

        event_agenda = form['event_agenda'].save(commit=False)
        event_agenda.event = evt
        event_agenda.save()

        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['ctg'] = EventCategory.objects.all()
        return context


class EventListView(LoginRequiredMixin, ListView):
    login_url = 'login'
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'


class EventUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    login_url = 'login'
    model = Event
    form_class = EventForm
    template_name = 'events/edit_event.html'


class EventDetailView(LoginRequiredMixin, DetailView):
    login_url = 'login'
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'


class EventDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    login_url = 'login'
    model = Event
    template_name = 'events/delete_event.html'
    success_url = reverse_lazy('event-list')


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

    def get_queryset(self):
        if not self.request.user.is_staff and not self.request.user.is_superuser:
            return EventMember.objects.filter(user=self.request.user)
        return EventMember.objects.all()


class RemoveEventMemberDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    login_url = 'login'
    model = EventMember
    template_name = 'events/remove_event_member.html'
    success_url = reverse_lazy('join-event-list')


class EventUserWishListView(LoginRequiredMixin, ListView):
    login_url = 'login'
    model = EventUserWishList
    template_name = 'events/event_user_wish_list.html'
    context_object_name = 'eventwish'

    def get_queryset(self):
        if not self.request.user.is_staff and not self.request.user.is_superuser:
            return EventUserWishList.objects.filter(user=self.request.user)
        return EventUserWishList.objects.all()


class AddEventUserWishListCreateView(LoginRequiredMixin, CreateView):
    login_url = 'login'
    model = EventUserWishList
    form_class = EventUserWishListForm
    template_name = 'events/add_event_user_wish.html'

    def form_valid(self, form):
        form.instance.created_user = self.request.user
        form.instance.updated_user = self.request.user
        return super().form_valid(form)


class RemoveEventUserWishDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    login_url = 'login'
    model = EventUserWishList
    template_name = 'events/remove_event_user_wish.html'
    success_url = reverse_lazy('event-wish-list')


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


from datetime import date
from django.db.models import Q

class CompleteEventList(LoginRequiredMixin, ListView):
    login_url = 'login'
    model = Event
    template_name = 'events/complete_event_list.html'
    context_object_name = 'events'

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

    def get_queryset(self):
        qs = EventMember.objects.filter(attend_status='absent')
        if not self.request.user.is_staff and not self.request.user.is_superuser:
            qs = qs.filter(user=self.request.user)
        return qs


class CompleteEventUserList(LoginRequiredMixin, ListView):
    login_url = 'login'
    model = EventMember
    template_name = 'events/complete_event_user_list.html'
    context_object_name = 'completeuser'

    def get_queryset(self):
        qs = EventMember.objects.filter(
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


class CreateUserMark(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    login_url = 'login'
    model = UserCoin
    form_class = UserCoinForm
    template_name = 'events/create_user_mark.html'

    def form_valid(self, form):
        form.instance.created_user = self.request.user
        form.instance.updated_user = self.request.user
        return super().form_valid(form)


class UserMarkList(LoginRequiredMixin, ListView):
    login_url = 'login'
    model = UserCoin
    template_name = 'events/user_mark_list.html'
    context_object_name = 'usermark'

    def get_queryset(self):
        if not self.request.user.is_staff and not self.request.user.is_superuser:
            return UserCoin.objects.filter(user=self.request.user)
        return UserCoin.objects.all()


@login_required(login_url='login')
def search_event_category(request):
    if request.method == 'POST':
       data = request.POST['search']
       event_category = EventCategory.objects.filter(name__icontains=data)
       context = {
           'event_category': event_category
       }
       return render(request, 'events/event_category.html', context)
    return render(request, 'events/event_category.html')

@login_required(login_url='login')
def search_event(request):
    if request.method == 'POST':
       data = request.POST['search']
       events = Event.objects.filter(name__icontains=data)
       context = {
           'events': events
       }
       return render(request, 'events/event_list.html', context)
    return render(request, 'events/event_list.html')


@login_required(login_url='login')
def join_event_direct(request, pk):
    event = get_object_or_404(Event, pk=pk)
    member, created = EventMember.objects.get_or_create(
        event=event,
        user=request.user,
        defaults={
            'attend_status': 'waiting',
            'status': 'active',
            'created_user': request.user,
            'updated_user': request.user
        }
    )
    if created:
        messages.success(request, f"Đăng ký tham gia thành công sự kiện: {event.name}! Đã phát vé QR cho bạn.")
    else:
        messages.info(request, f"Bạn đã đăng ký tham gia sự kiện này trước đó.")
    return redirect('event-ticket', pk=member.pk)


@login_required(login_url='login')
def event_ticket(request, pk):
    member = get_object_or_404(EventMember, pk=pk)
    if member.user != request.user and not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Bạn không có quyền xem vé này.")
        return redirect('event-list')
    context = {
        'member': member,
        'event': member.event,
        'ticket_code': member.ticket_code
    }
    return render(request, 'events/event_ticket.html', context)


@login_required(login_url='login')
def my_tickets(request):
    tickets = EventMember.objects.filter(user=request.user).select_related('event', 'event__category').order_by('-created_date')
    context = {
        'tickets': tickets
    }
    return render(request, 'events/my_tickets.html', context)


@login_required(login_url='login')
def checkin_view(request):
    event_id = request.GET.get('event_id')
    search_ticket = request.GET.get('ticket', '').strip()
    is_admin = request.user.is_staff or request.user.is_superuser
    
    if request.method == 'POST':
        action = request.POST.get('action')
        member_id = request.POST.get('member_id')
        code_input = request.POST.get('ticket_code', '').strip()
        
        target_member = None
        if member_id:
            target_member = EventMember.objects.filter(pk=member_id).first()
        elif code_input:
            if 'MEM' in code_input.upper():
                try:
                    mem_pk = int(code_input.upper().split('MEM')[-1])
                    target_member = EventMember.objects.filter(pk=mem_pk).first()
                except ValueError:
                    pass
            if not target_member and code_input.isdigit():
                target_member = EventMember.objects.filter(pk=code_input).first()
        
        if target_member:
            # Enforce self-only check-in for normal users
            if not is_admin and target_member.user != request.user:
                messages.error(request, "❌ Bạn chỉ có thể điểm danh vé cho chính tài khoản của bạn!")
                return redirect('event-checkin')

            if action == 'cancel_checkin':
                if not is_admin:
                    messages.error(request, "❌ Chỉ Quản trị viên (Admin) mới có thể hủy điểm danh!")
                    return redirect('event-checkin')
                target_member.attend_status = 'waiting'
                target_member.updated_user = request.user
                target_member.save()
                messages.info(request, f"Đã hủy điểm danh cho: {target_member.user.get_full_name() or target_member.user.username}")
            else:
                target_member.attend_status = 'attending'
                target_member.updated_user = request.user
                target_member.save()
                messages.success(request, f"✅ Điểm danh thành công! {target_member.user.get_full_name() or target_member.user.username} - Vé #{target_member.ticket_code}")
            return redirect(f"{request.path}?event_id={target_member.event.id}" if target_member else request.path)
        else:
            messages.error(request, "Không tìm thấy mã vé hoặc thành viên hợp lệ!")

    scanned_member = None
    if search_ticket:
        if 'MEM' in search_ticket.upper():
            try:
                mem_pk = int(search_ticket.upper().split('MEM')[-1])
                scanned_member = EventMember.objects.filter(pk=mem_pk).first()
            except ValueError:
                pass
        if not scanned_member and search_ticket.isdigit():
            scanned_member = EventMember.objects.filter(pk=search_ticket).first()
        
        if scanned_member and not is_admin and scanned_member.user != request.user:
            scanned_member = None
            messages.error(request, "❌ Bạn không thể quét hoặc điểm danh vé của tài khoản khác.")

    if is_admin:
        queryset = EventMember.objects.select_related('event', 'user').all()
        events = Event.objects.all()
    else:
        queryset = EventMember.objects.select_related('event', 'user').filter(user=request.user)
        events = Event.objects.filter(eventmember__user=request.user).distinct()

    if event_id and event_id.isdigit():
        queryset = queryset.filter(event_id=int(event_id))
    
    total_registered = queryset.count()
    total_attended = queryset.filter(attend_status__in=['attending', 'completed']).count()
    total_waiting = queryset.filter(attend_status='waiting').count()
    total_absent = queryset.filter(attend_status='absent').count()
    
    attendance_rate = round((total_attended / total_registered * 100), 1) if total_registered > 0 else 0
    
    context = {
        'event_members': queryset.order_by('-id'),
        'events': events,
        'selected_event_id': int(event_id) if event_id and event_id.isdigit() else None,
        'scanned_member': scanned_member,
        'search_ticket': search_ticket,
        'total_registered': total_registered,
        'total_attended': total_attended,
        'total_waiting': total_waiting,
        'total_absent': total_absent,
        'attendance_rate': attendance_rate,
        'is_admin': is_admin,
    }
    return render(request, 'events/checkin.html', context)


