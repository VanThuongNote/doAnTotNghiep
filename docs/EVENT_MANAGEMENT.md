# Feature: Quan Ly Su Kien (Event Management)

## Files lien quan
- events/models.py                          - Model: Event, EventCategory, EventImage, EventAgenda
- events/views.py                           - CRUD su kien, danh muc
- events/urls.py                            - /events/event-list/ /events/event-create/ ...
- events/forms.py                           - EventForm, EventImageForm, EventCategoryForm
- templates/events/event_list.html          - Danh sach su kien
- templates/events/create_event.html        - Tao su kien moi
- templates/events/edit_event.html          - Chinh sua su kien
- templates/events/delete_event.html        - Xoa su kien
- templates/events/event_detail.html        - Chi tiet su kien
- templates/events/event_category.html      - Danh muc su kien
- templates/events/update_event_status.html - Cap nhat trang thai

## Chuc nang da cai dat
- Xem danh sach su kien (co tim kiem)
- Tao / Sua / Xoa su kien (chi Admin)
- Quan ly danh muc su kien
- Cap nhat trang thai su kien: Hoat dong / Hoan thanh / Time Out
- Xem chi tiet su kien, dang ky tham gia
