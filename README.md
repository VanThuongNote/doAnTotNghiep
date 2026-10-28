# Hệ Thống Quản Lý Sự Kiện

Đề tài tốt nghiệp của sinh viên **Nguyễn Văn Thương** – MSSV: 2251220272 – Lớp 22CT4  
Trường Đại học Kiến Trúc Đà Nẵng – Khoa Công Nghệ Thông Tin  
Giáo viên hướng dẫn: TS. Đoàn Duy Bình

---

## Giới Thiệu

Ứng dụng web quản lý sự kiện được xây dựng bằng **Django** và **MySQL**, hỗ trợ:

- Tạo và quản lý sự kiện (thời gian, địa điểm, số lượng người tham gia)
- Đăng ký tham gia sự kiện trực tuyến
- Phát hành vé điện tử tích hợp mã QR
- Điểm danh người tham dự bằng mã QR
- Thống kê số lượng đăng ký và điểm danh theo từng sự kiện
- Phân quyền: Admin / Người tham gia

---

## Công Nghệ Sử Dụng

| Thành phần | Công nghệ |
|---|---|
| Backend | Python 3.12 + Django 2.2 |
| Frontend | HTML, CSS, JavaScript, Bootstrap 4, AdminLTE 3 |
| Database | MySQL 8.x |
| Quản lý CSDL | MySQL Workbench |
| Mã QR | Thư viện QR tích hợp Django |
| IDE | Visual Studio Code |

---

## Cài Đặt & Chạy Dự Án

### Yêu cầu

- Python 3.10+
- MySQL Server 8.x
- MySQL Workbench

### 1. Clone dự án

```bash
git clone https://github.com/VanThuongNote/doAnTotNghiep
cd DATN
git init
git add README.md
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/VanThuongNote/doAnTotNghiep.git
git push -u origin main
```

### 2. Cài đặt thư viện

```bash
pip install -r requirements.txt
pip install mysqlclient
```

### 3. Tạo database trong MySQL Workbench

```sql
CREATE DATABASE quanlysukien
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

### 4. Cấu hình kết nối MySQL

Mở file `event_management/settings.py`, cập nhật mật khẩu MySQL:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'quanlysukien',
        'USER': 'root',
        'PASSWORD': '2111',  
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

### 5. Chạy migrations

```bash
python manage.py migrate
```

### 6. Tạo tài khoản admin

```bash
python manage.py createsuperuser
```

### 7. Khởi động server

```bash
python manage.py runserver
```

Truy cập: http://127.0.0.1:8000

---

## Cấu Trúc Dự Án

```
DATN/
├── event_management/       # Cấu hình Django (settings, urls, views, forms)
├── events/                 # App chính: models, views, urls, forms
│   └── migrations/         # Lịch sử migration database
├── templates/              # Giao diện HTML (AdminLTE 3)
│   ├── base/               # Template cơ sở (sidebar, navbar, footer)
│   └── events/             # Template các trang sự kiện
├── static/                 # CSS, JavaScript, hình ảnh tĩnh
├── media/                  # File upload (avatar, ảnh sự kiện)
├── manage.py
└── requirements.txt
```

---

## Các Chức Năng Chính

### Admin
- Quản lý danh mục và sự kiện (tạo / sửa / xóa)
- Xem danh sách người đăng ký theo từng sự kiện
- Điểm danh người tham dự bằng mã QR
- Cấp điểm thưởng cho người dùng
- Thống kê đã điểm danh / vắng mặt

### Người dùng
- Xem danh sách và chi tiết sự kiện
- Đăng ký tham gia sự kiện
- Xem vé điện tử QR của mình
- Cập nhật hồ sơ cá nhân (avatar, số điện thoại, địa chỉ)

---

## Tác Giả

**Nguyễn Văn Thương**  
Email: Thuong_2251220272@dau.edu.vn  
Trường Đại học Kiến Trúc Đà Nẵng – Khoa CNTT – Lớp 22CT4 – Khóa 2022
