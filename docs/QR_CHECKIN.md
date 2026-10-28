# Feature: Ve QR va Diem Danh (QR Ticket & Check-in)

## Files lien quan
- events/models.py                            - Model EventMember (ticket_code, attend_status)
- events/views.py                             - join_event_direct, event_ticket, my_tickets, checkin_view
- events/urls.py                              - /events/join/ /events/ticket/ /events/checkin/
- templates/events/event_ticket.html          - Hien thi ve QR ca nhan
- templates/events/my_tickets.html            - Danh sach ve cua toi
- templates/events/checkin.html               - Giao dien diem danh bang QR
- templates/events/joinevent_list.html        - Danh sach dang ky tham gia
- templates/events/complete_event_user_list.html - Nguoi tham du da hoan thanh
- templates/events/absense_user_list.html     - Nguoi vang mat

## Chuc nang da cai dat
- Dang ky tham gia su kien 1 cham (khong dang ky trung)
- Tu dong phat ve QR sau khi dang ky
- Hien thi ve QR ca nhan voi ma duy nhat
- Diem danh bang quet ma QR hoac nhap ma thu cong
- Thong ke: tong dang ky / da diem danh / cho / vang mat
- Bao mat: nguoi dung chi diem danh ve cua chinh minh
