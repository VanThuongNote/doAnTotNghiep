# Feature: Xac Thuc Nguoi Dung (Authentication)

## Files lien quan
- templates/login.html           - Trang dang nhap
- templates/register.html        - Trang dang ky tai khoan moi
- templates/forgot_password.html - Trang quen mat khau / dat lai mat khau
- event_management/forms.py      - LoginForm, RegisterForm, ResetPasswordForm
- event_management/views.py      - login_page, logout_page, register_page, forgot_password_page
- event_management/urls.py       - /login/ /logout/ /register/ /forgot-password/

## Chuc nang da cai dat
- Dang nhap bang username + password
- Dang ky tai khoan moi (kiem tra trung username/email)
- Quen mat khau: xac minh username + email, dat lai mat khau moi
- Phan quyen: Admin (is_staff/is_superuser) va Nguoi dung thuong
