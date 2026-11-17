from datetime import date, timedelta
import io
import openpyxl

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User

from .models import (
    EventCategory,
    JobCategory,
    Event,
    EventAgenda,
    EventMember,
    EventUserWishList,
    UserCoin,
    EventFeedback,
    PasswordResetOTP,
)
from .qr_utils import generate_qr_base64


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class EventManagementAllPhasesTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin_test', email='admin@dau.edu.vn', password='password123'
        )
        self.user1 = User.objects.create_user(
            username='sv_thuong', email='thuong@dau.edu.vn', password='password123',
            first_name='Văn Thương', last_name='Nguyễn'
        )
        self.user2 = User.objects.create_user(
            username='sv_hai', email='hai@dau.edu.vn', password='password123'
        )

        self.cat = EventCategory.objects.create(
            name='Hội thảo CNTT',
            code='IT01',
            image='event_category/test.jpg',
            priority=1,
            created_user=self.admin,
            updated_user=self.admin,
            status='active',
        )
        self.job_cat = JobCategory.objects.create(name='Công nghệ phần mềm')

        self.event = Event.objects.create(
            category=self.cat,
            name='Hội thảo AI & Cloud 2026',
            uid=1001,
            description='<p>Hội thảo chuyên đề AI</p>',
            job_category=self.job_cat,
            scheduled_status='scheduled',
            venue='Hội trường A - ĐH Kiến Trúc Đà Nẵng',
            start_date=date.today() + timedelta(days=2),
            end_date=date.today() + timedelta(days=3),
            location='108.220832,16.047079',
            points=25,
            maximum_attende=1,  # Giới hạn 1 chỗ để kiểm thử chống Overbooking
            created_user=self.admin,
            updated_user=self.admin,
            status='active',
        )
        self.agenda = EventAgenda.objects.create(
            event=self.event,
            session_name='Khai mạc & Keynote AI',
            speaker_name='TS. Đoàn Duy Bình',
            start_time='08:00',
            end_time='10:00',
            venue_name='Phòng 301',
        )

    def test_phase1_offline_qr_and_overbooking_and_cancel(self):
        # 1. Kiểm tra tạo QR offline Base64
        qr_uri = generate_qr_base64("EVT0001-MEM0001")
        self.assertTrue(qr_uri.startswith("data:image/png;base64,"))

        # 2. User 1 đăng ký thành công (1/1 chỗ)
        self.client.login(username='sv_thuong', password='password123')
        res = self.client.get(reverse('join-event', args=[self.event.pk]))
        self.assertEqual(res.status_code, 302)
        self.assertEqual(self.event.registered_count, 1)
        self.assertTrue(self.event.is_full)

        # 3. User 2 đăng ký khi đã đầy (1/1) -> bị chặn Overbooking
        self.client.login(username='sv_hai', password='password123')
        res2 = self.client.get(reverse('join-event', args=[self.event.pk]))
        self.assertEqual(EventMember.objects.filter(event=self.event).count(), 1)

        # 4. User 1 tự hủy đăng ký -> nhường chỗ
        self.client.login(username='sv_thuong', password='password123')
        mem1 = EventMember.objects.get(event=self.event, user=self.user1)
        self.client.get(reverse('cancel-event-registration', args=[mem1.pk]))
        self.assertEqual(self.event.registered_count, 0)

    def test_phase1_and_2_ajax_checkin_and_auto_points(self):
        mem = EventMember.objects.create(
            event=self.event, user=self.user1, attend_status='waiting',
            status='active', created_user=self.user1, updated_user=self.user1
        )
        self.client.login(username='admin_test', password='password123')

        # AJAX Check-in
        res = self.client.post(
            reverse('event-checkin'),
            {'action': 'checkin', 'ticket_code': mem.ticket_code},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['stats']['total_attended'], 1)

        # Kiểm tra tự động cộng 25 điểm vào UserCoin
        coin = UserCoin.objects.get(user=self.user1)
        self.assertEqual(coin.gain_coin, 25)

        # Admin đánh dấu Vắng mặt (mark_absent) -> tự động thu hồi 25 điểm
        res_abs = self.client.post(
            reverse('event-checkin'),
            {'action': 'mark_absent', 'member_id': mem.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(res_abs.status_code, 200)
        mem.refresh_from_db()
        self.assertEqual(mem.attend_status, 'absent')
        coin.refresh_from_db()
        self.assertEqual(coin.gain_coin, 0)

        # Điểm danh lại -> cộng lại 25 điểm
        self.client.post(
            reverse('event-checkin'),
            {'action': 'checkin', 'member_id': mem.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        coin.refresh_from_db()
        self.assertEqual(coin.gain_coin, 25)

        # Admin cộng thêm 15 điểm qua CreateUserMark (không bị lỗi trùng OneToOne)
        res_mark = self.client.post(reverse('create-user-mark'), {
            'user': self.user1.id,
            'gain_type': 'others',
            'gain_coin': 15,
            'status': 'active',
        })
        self.assertEqual(res_mark.status_code, 302)
        coin.refresh_from_db()
        self.assertEqual(coin.gain_coin, 40)

    def test_phase3_certificate_excel_ics_feedback_and_otp(self):
        mem = EventMember.objects.create(
            event=self.event, user=self.user1, attend_status='attending',
            status='active', created_user=self.user1, updated_user=self.user1
        )
        self.client.login(username='sv_thuong', password='password123')

        # 1. Xem Giấy chứng nhận
        cert_res = self.client.get(reverse('event-certificate', args=[mem.pk]))
        self.assertEqual(cert_res.status_code, 200)
        self.assertContains(cert_res, 'GIẤY CHỨNG NHẬN')
        self.assertContains(cert_res, mem.certificate_code)

        # 2. Xuất file lịch .ICS
        ics_res = self.client.get(reverse('export-event-ics', args=[self.event.pk]))
        self.assertEqual(ics_res.status_code, 200)
        self.assertIn(b'BEGIN:VCALENDAR', ics_res.content)

        # 3. Gửi đánh giá 5 sao (Feedback)
        fb_res = self.client.post(reverse('submit-event-feedback', args=[self.event.pk]), {
            'rating': 5,
            'comment': 'Sự kiện rất bổ ích và chuyên nghiệp!'
        })
        self.assertEqual(fb_res.status_code, 302)
        self.assertEqual(self.event.average_rating, 5.0)
        self.assertEqual(self.event.feedback_count, 1)

        # 4. Xuất báo cáo Excel (.xlsx)
        self.client.login(username='admin_test', password='password123')
        xls_res = self.client.get(reverse('export-event-members-excel'))
        self.assertEqual(xls_res.status_code, 200)
        wb = openpyxl.load_workbook(io.BytesIO(xls_res.content))
        ws = wb.active
        self.assertEqual(ws['B5'].value, mem.ticket_code)

        # 5. Quên mật khẩu bảo mật 2 bước bằng OTP
        self.client.logout()
        step1 = self.client.post(reverse('forgot-password'), {
            'step': 'request_otp',
            'username': 'sv_thuong',
            'email': 'thuong@dau.edu.vn',
        })
        self.assertEqual(step1.status_code, 200)
        otp_obj = PasswordResetOTP.objects.filter(user=self.user1, is_used=False).first()
        self.assertIsNotNone(otp_obj)

        step2 = self.client.post(reverse('forgot-password'), {
            'step': 'verify_otp',
            'username': 'sv_thuong',
            'email': 'thuong@dau.edu.vn',
            'otp_code': otp_obj.otp_code,
            'new_password': 'newpassword999',
            'confirm_password': 'newpassword999',
        })
        self.assertEqual(step2.status_code, 302)
        self.user1.refresh_from_db()
        self.assertTrue(self.user1.check_password('newpassword999'))

    def test_create_event_with_and_without_optional_fields(self):
        self.client.login(username='admin_test', password='password123')

        # 1. GET trang tạo sự kiện
        get_res = self.client.get(reverse('event-create'))
        self.assertEqual(get_res.status_code, 200)

        # 2. POST tạo sự kiện không cần ảnh, không cần location, không cần agenda
        res = self.client.post(reverse('event-create'), {
            'event-category': self.cat.id,
            'event-name': 'Sự kiện Test Tạo Thành Công',
            'event-uid': 202601,
            'event-description': '<p>Nội dung mô tả sự kiện test</p>',
            'event-job_category': self.job_cat.id,
            'event-scheduled_status': 'scheduled',
            'event-venue': 'Phòng 401 - ĐH Kiến Trúc Đà Nẵng',
            'event-start_date': (date.today() + timedelta(days=5)).strftime('%Y-%m-%d'),
            'event-end_date': (date.today() + timedelta(days=6)).strftime('%Y-%m-%d'),
            'event-location': '',
            'event-points': 30,
            'event-maximum_attende': 100,
            'event-status': 'active',
        }, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(Event.objects.filter(name='Sự kiện Test Tạo Thành Công').exists())
        self.assertContains(res, "Đã tạo sự kiện &#x27;Sự kiện Test Tạo Thành Công&#x27; thành công!")

        # 3. Kiểm tra trang Lịch & Bản đồ sự kiện (/events/calendar/) và JSON API
        cal_res = self.client.get(reverse('event-calendar'))
        self.assertEqual(cal_res.status_code, 200)
        self.assertContains(cal_res, 'Sự kiện Test Tạo Thành Công')
        cal_json = self.client.get(reverse('event-calendar') + '?format=json')
        self.assertEqual(cal_json.status_code, 200)
        self.assertGreaterEqual(len(cal_json.json()['events']), 2)

