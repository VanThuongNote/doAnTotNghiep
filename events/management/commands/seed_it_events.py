import os
from datetime import date, time, timedelta
from PIL import Image, ImageDraw, ImageFont

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from events.models import (
    Event,
    EventAgenda,
    EventCategory,
    EventImage,
    JobCategory,
)


def _load_font(size: int, bold: bool = False):
    candidates = (
        [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/tahomabd.ttf",
        ]
        if bold
        else [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/tahoma.ttf",
        ]
    )
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _wrap_text(draw, text: str, font, max_width: int):
    words = text.split()
    lines = []
    current = ""
    for w in words:
        test = f"{current} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def generate_tech_banner(
    rel_path: str,
    title: str,
    subtitle: str,
    tag: str,
    palette: tuple,
    size=(1200, 630),
) -> str:
    """Tạo ảnh banner công nghệ thông tin sắc nét lưu vào MEDIA_ROOT/rel_path."""
    full_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    w, h = size
    c1, c2, accent = palette
    img = Image.new("RGB", (w, h), c1)
    draw = ImageDraw.Draw(img, "RGBA")

    # Gradient nền ngang + chéo
    for y in range(h):
        ratio = y / max(1, h - 1)
        r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
        g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
        b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b, 255))

    # Lưới công nghệ (Tech Grid)
    grid_color = (255, 255, 255, 18)
    for gx in range(0, w, 60):
        draw.line([(gx, 0), (gx, h)], fill=grid_color, width=1)
    for gy in range(0, h, 60):
        draw.line([(0, gy), (w, gy)], fill=grid_color, width=1)

    # Vòng tròn phát sáng trang trí bên phải
    draw.ellipse([w - 420, -120, w + 120, 420], fill=(accent[0], accent[1], accent[2], 45))
    draw.ellipse([w - 320, 220, w + 80, 620], fill=(255, 255, 255, 22))
    draw.ellipse([w - 260, 80, w - 40, 300], outline=(accent[0], accent[1], accent[2], 140), width=4)

    # Các node mạch điện tử trang trí
    nodes = [(w - 350, 140), (w - 220, 140), (w - 160, 220), (w - 280, 320), (w - 140, 380)]
    for i in range(len(nodes) - 1):
        draw.line([nodes[i], nodes[i + 1]], fill=(accent[0], accent[1], accent[2], 130), width=3)
    for nx, ny in nodes:
        draw.ellipse([nx - 8, ny - 8, nx + 8, ny + 8], fill=(accent[0], accent[1], accent[2], 230))

    # Khung viền mảnh bên trong
    draw.rounded_rectangle(
        [36, 36, w - 36, h - 36],
        radius=24,
        outline=(255, 255, 255, 45),
        width=2,
    )

    font_tag = _load_font(22, bold=True)
    font_title = _load_font(46, bold=True)
    font_sub = _load_font(25, bold=False)
    font_footer = _load_font(20, bold=True)

    # Badge danh mục
    tag_text = f"  {tag.upper()}  "
    tb = draw.textbbox((0, 0), tag_text, font=font_tag)
    tw, th = tb[2] - tb[0] + 24, tb[3] - tb[1] + 18
    draw.rounded_rectangle([76, 78, 76 + tw, 78 + th], radius=12, fill=(accent[0], accent[1], accent[2], 230))
    draw.text((88, 84), tag_text, fill=(15, 23, 42, 255), font=font_tag)

    # Tiêu đề chính (tự xuống dòng)
    lines = _wrap_text(draw, title, font_title, w - 260)
    y_text = 165
    for line in lines[:3]:
        draw.text((78, y_text), line, fill=(255, 255, 255, 255), font=font_title)
        y_text += 62

    # Phụ đề
    sub_lines = _wrap_text(draw, subtitle, font_sub, w - 280)
    y_text += 14
    for sline in sub_lines[:2]:
        draw.text((78, y_text), sline, fill=(203, 213, 225, 240), font=font_sub)
        y_text += 38

    # Thanh chân trang
    draw.rounded_rectangle([76, h - 110, 640, h - 62], radius=10, fill=(15, 23, 42, 165))
    draw.text(
        (96, h - 98),
        "CNTT & Chuyển Đổi Số  •  ĐH Kiến Trúc Đà Nẵng (DAU)",
        fill=(accent[0], accent[1], accent[2], 255),
        font=font_footer,
    )

    img.save(full_path, quality=92)
    return rel_path


class Command(BaseCommand):
    help = "Tạo danh mục, sự kiện ngành Công nghệ thông tin và gắn đầy đủ hình ảnh banner"

    def handle(self, *args, **options):
        admin_user = (
            User.objects.filter(is_superuser=True).first()
            or User.objects.filter(is_staff=True).first()
            or User.objects.first()
        )
        if not admin_user:
            admin_user = User.objects.create_superuser(
                username="admin",
                email="admin@dau.edu.vn",
                password="admin123",
            )

        # 1. Tạo các JobCategory ngành CNTT & AI
        job_names = [
            "Kỹ thuật Phần mềm (Software Engineering)",
            "Trí tuệ Nhân tạo & Khoa học Dữ liệu (AI & Data Science)",
            "An toàn Thông tin & Mạng (CyberSecurity)",
            "DevOps, Cloud & Kiến trúc Hệ thống",
            "Phát triển Web & Ứng dụng Di động",
            "Thiết kế UI/UX & Sản phẩm Số",
            "Kỹ sư Mô hình Ngôn ngữ Lớn & AI Tạo sinh (LLM & GenAI)",
            "Thị giác Máy tính & Robot Thông minh (Computer Vision)",
            "Hệ thống Nhúng, IoT & Vi mạch Bán dẫn (AIoT & Chip)",
            "Công nghệ Chuỗi khối & Tài chính Số (Blockchain & FinTech)",
        ]
        job_map = {}
        for jname in job_names:
            jobj, _ = JobCategory.objects.get_or_create(name=jname)
            job_map[jname] = jobj

        # 2. Tạo/Cập nhật các Danh mục Sự kiện (EventCategory) ngành CNTT + ảnh đại diện
        categories_data = [
            {
                "code": "ITDEV",
                "name": "Lập trình & Phát triển Phần mềm",
                "priority": 1,
                "img": "event_category/cat_software_dev.png",
                "palette": ((15, 23, 42), (30, 64, 175), (56, 189, 248)),
                "sub": "Web, Mobile, Backend, Kiến trúc Phần mềm hiện đại",
            },
            {
                "code": "ITAID",
                "name": "Trí tuệ Nhân tạo & Dữ liệu lớn (AI & Big Data)",
                "priority": 2,
                "img": "event_category/cat_ai_data.png",
                "palette": ((23, 15, 45), (88, 28, 135), (192, 132, 252)),
                "sub": "Generative AI, LLM, Machine Learning, Computer Vision",
            },
            {
                "code": "ITSEC",
                "name": "An toàn Thông tin & An ninh Mạng",
                "priority": 3,
                "img": "event_category/cat_cyber_sec.png",
                "palette": ((6, 32, 28), (6, 95, 70), (52, 211, 153)),
                "sub": "Ethical Hacking, CTF, Bảo mật Hệ thống & Cloud Security",
            },
            {
                "code": "ITOPS",
                "name": "Cloud Computing & DevOps",
                "priority": 4,
                "img": "event_category/cat_cloud_devops.png",
                "palette": ((15, 23, 42), (12, 74, 110), (34, 211, 238)),
                "sub": "Docker, Kubernetes, CI/CD, AWS / GCP / Azure",
            },
            {
                "code": "ITHCK",
                "name": "Cuộc thi Lập trình & Hackathon CNTT",
                "priority": 5,
                "img": "event_category/cat_hackathon.png",
                "palette": ((45, 18, 25), (153, 27, 27), (251, 146, 60)),
                "sub": "Coding Contest, Đổi mới Sáng tạo, Khởi nghiệp Công nghệ",
            },
            {
                "code": "ITCAR",
                "name": "Định hướng Nghề nghiệp & Tuyển dụng IT",
                "priority": 6,
                "img": "event_category/cat_it_career.png",
                "palette": ((20, 20, 46), (67, 56, 202), (129, 140, 248)),
                "sub": "IT Job Fair, Kỹ năng Phỏng vấn Big Tech, Giao lưu Doanh nghiệp",
            },
            {
                "code": "AILMM",
                "name": "AI Tạo sinh & Mô hình Ngôn ngữ Lớn (GenAI & LLM)",
                "priority": 7,
                "img": "event_category/cat_genai_llm.png",
                "palette": ((30, 12, 52), (126, 34, 206), (232, 121, 249)),
                "sub": "ChatGPT, Claude, DeepSeek, RAG, LangChain & AI Agents",
            },
            {
                "code": "AICVR",
                "name": "Thị giác Máy tính & Robot Tự hành (Computer Vision)",
                "priority": 8,
                "img": "event_category/cat_computer_vision.png",
                "palette": ((10, 30, 46), (14, 116, 144), (103, 232, 249)),
                "sub": "YOLO, OpenCV, Nhận diện Khuôn mặt, Xe Tự hành & Xử lý Ảnh",
            },
            {
                "code": "ITIOT",
                "name": "Internet Vạn Vật (AIoT) & Vi mạch Bán dẫn",
                "priority": 9,
                "img": "event_category/cat_aiot_semiconductor.png",
                "palette": ((12, 34, 24), (21, 128, 61), (134, 239, 172)),
                "sub": "Embedded Systems, Edge AI, Thiết kế Vi mạch & Smart City",
            },
            {
                "code": "ITW3F",
                "name": "Blockchain, Web3 & Công nghệ Tài chính (FinTech)",
                "priority": 10,
                "img": "event_category/cat_blockchain_fintech.png",
                "palette": ((40, 22, 10), (180, 83, 9), (251, 191, 36)),
                "sub": "Smart Contracts, DeFi, Bảo mật Chuỗi khối & Thanh toán Số",
            },
        ]

        cat_map = {}
        used_priorities = set(EventCategory.objects.values_list("priority", flat=True))
        for cdata in categories_data:
            generate_tech_banner(
                rel_path=cdata["img"],
                title=cdata["name"],
                subtitle=cdata["sub"],
                tag=cdata["code"],
                palette=cdata["palette"],
                size=(800, 450),
            )
            cat_obj = (
                EventCategory.objects.filter(code=cdata["code"]).first()
                or EventCategory.objects.filter(name=cdata["name"]).first()
            )
            if cat_obj:
                cat_obj.name = cdata["name"]
                cat_obj.image = cdata["img"]
                cat_obj.status = "active"
                cat_obj.updated_user = admin_user
                cat_obj.save()
            else:
                prio = cdata["priority"]
                while prio in used_priorities:
                    prio += 1
                used_priorities.add(prio)
                cat_obj = EventCategory.objects.create(
                    name=cdata["name"],
                    code=cdata["code"],
                    image=cdata["img"],
                    priority=prio,
                    created_user=admin_user,
                    updated_user=admin_user,
                    status="active",
                )
            cat_map[cdata["code"]] = cat_obj

        # Đảm bảo các EventCategory sẵn có trong DB cũng có file ảnh hợp lệ
        for existing_cat in EventCategory.objects.all():
            img_path = os.path.join(settings.MEDIA_ROOT, str(existing_cat.image)) if existing_cat.image else ""
            if not existing_cat.image or not os.path.exists(img_path):
                rel = f"event_category/cat_existing_{existing_cat.id}.png"
                generate_tech_banner(
                    rel_path=rel,
                    title=existing_cat.name,
                    subtitle="Danh mục Sự kiện Công nghệ Thông tin",
                    tag=existing_cat.code or "IT",
                    palette=((15, 23, 42), (55, 48, 163), (96, 165, 250)),
                    size=(800, 450),
                )
                existing_cat.image = rel
                existing_cat.save()

        # 3. Tạo 8 Sự kiện ngành Công nghệ thông tin kèm Banner & Lịch trình
        today = date.today()
        it_events = [
            {
                "uid": 2026101,
                "name": "Hội thảo AI & Generative Agents 2026: Ứng dụng LLM trong Phát triển Phần mềm",
                "cat": "ITAID",
                "job": "Trí tuệ Nhân tạo & Khoa học Dữ liệu (AI & Data Science)",
                "venue": "Hội trường A - ĐH Kiến Trúc Đà Nẵng (566 Núi Thành)",
                "start_date": today + timedelta(days=5),
                "end_date": today + timedelta(days=5),
                "points": 30,
                "max_attende": 150,
                "img": "event_image/it_ai_summit_2026.png",
                "palette": ((18, 16, 46), (88, 28, 135), (192, 132, 252)),
                "subtitle": "Khám phá kiến trúc RAG, Multi-Agent Systems & AI Coding Assistants cho kỹ sư CNTT",
                "description": """
                    <h3>Giới thiệu Hội thảo AI & Generative Agents 2026</h3>
                    <p>Hội thảo chuyên sâu dành cho sinh viên và lập trình viên ngành <strong>Công nghệ Thông tin</strong> về cách tích hợp các mô hình ngôn ngữ lớn (LLM), hệ thống truy xuất tri thức <strong>RAG</strong> và <strong>Multi-Agent</strong> vào sản phẩm thực tế.</p>
                    <ul>
                        <li>Xây dựng AI Agent tự động hóa quy trình kiểm thử và review code.</li>
                        <li>Tối ưu hóa hiệu năng suy luận (Inference) và bảo mật dữ liệu doanh nghiệp.</li>
                        <li>Demo trực tiếp trợ lý lập trình thông minh trên nền tảng Python &amp; Django.</li>
                    </ul>
                """,
                "agenda": {
                    "session_name": "Keynote: Kiến trúc RAG & AI Agent trong Doanh nghiệp Phần mềm",
                    "speaker_name": "TS. Nguyễn Minh Khoa - Chuyên gia AI & Cloud",
                    "start_time": time(8, 30),
                    "end_time": time(11, 30),
                    "venue_name": "Hội trường A - Tầng 2",
                },
            },
            {
                "uid": 2026102,
                "name": "Workshop Thực chiến Cloud & DevOps: Triển khai Microservices với Docker & Kubernetes",
                "cat": "ITOPS",
                "job": "DevOps, Cloud & Kiến trúc Hệ thống",
                "venue": "Phòng Lab CNTT 402 - ĐH Kiến Trúc Đà Nẵng",
                "start_date": today + timedelta(days=8),
                "end_date": today + timedelta(days=9),
                "points": 35,
                "max_attende": 80,
                "img": "event_image/it_devops_k8s_2026.png",
                "palette": ((12, 25, 44), (3, 105, 161), (56, 189, 248)),
                "subtitle": "Thực hành đóng gói контейner, thiết lập CI/CD GitHub Actions và giám sát cụm Kubernetes",
                "description": """
                    <h3>Workshop Thực chiến Cloud &amp; DevOps</h3>
                    <p>Chương trình huấn luyện thực hành 100% trên máy tính giúp sinh viên CNTT nắm vững quy trình <strong>CI/CD</strong> và vận hành hệ thống hiện đại:</p>
                    <ul>
                        <li>Viết <code>Dockerfile</code> tối ưu đa tầng (Multi-stage build) cho ứng dụng Web Django &amp; Node.js.</li>
                        <li>Triển khai hệ thống tự động co giãn (Auto-scaling) trên <strong>Kubernetes (K8s)</strong>.</li>
                        <li>Thiết lập hệ thống giám sát tập trung với <strong>Prometheus &amp; Grafana</strong>.</li>
                    </ul>
                """,
                "agenda": {
                    "session_name": "Hands-on Lab: Từ Docker Compose lên Kubernetes Cluster & CI/CD Pipeline",
                    "speaker_name": "KS. Trần Quốc Bảo - Senior DevOps Engineer",
                    "start_time": time(13, 30),
                    "end_time": time(17, 0),
                    "venue_name": "Phòng máy thực hành 402",
                },
            },
            {
                "uid": 2026103,
                "name": "Diễn đàn An toàn Thông tin: Phòng chống Tấn công Mạng & Bảo mật Ứng dụng Web (OWASP Top 10)",
                "cat": "ITSEC",
                "job": "An toàn Thông tin & Mạng (CyberSecurity)",
                "venue": "Hội trường B - Khu giảng đường CNTT",
                "start_date": today + timedelta(days=12),
                "end_date": today + timedelta(days=12),
                "points": 30,
                "max_attende": 120,
                "img": "event_image/it_cybersecurity_owasp.png",
                "palette": ((6, 30, 26), (5, 122, 85), (52, 211, 153)),
                "subtitle": "Phân tích lỗ hổng SQL Injection, XSS, CSRF và diễn tập phòng thủ hệ thống trực tiếp",
                "description": """
                    <h3>Diễn đàn An toàn Thông tin &amp; Bảo mật Web 2026</h3>
                    <p>Trang bị tư duy bảo mật (Security Mindset) cho sinh viên ngành Công nghệ Thông tin trước các mối đe dọa an ninh mạng ngày càng tinh vi:</p>
                    <ul>
                        <li>Demo trực tiếp cách khai thác và vá các lỗ hổng trong <strong>OWASP Top 10</strong>.</li>
                        <li>Bảo mật xác thực đa yếu tố (2FA/OTP), quản lý phiên đăng nhập và phân quyền RBAC.</li>
                        <li>Mini-game <strong>Capture The Flag (CTF)</strong> nhận giải thưởng hấp dẫn ngay tại hội trường.</li>
                    </ul>
                """,
                "agenda": {
                    "session_name": "Live Demo: Pentest Ứng dụng Web & Chiến thuật Phòng thủ Red Team vs Blue Team",
                    "speaker_name": "ThS. Lê Hoàng Nam - Chuyên gia An ninh mạng",
                    "start_time": time(8, 0),
                    "end_time": time(11, 30),
                    "venue_name": "Hội trường B",
                },
            },
            {
                "uid": 2026104,
                "name": "Cuộc thi Lập trình DAU IT Hackathon 2026: Giải pháp Công nghệ cho Đô thị Thông minh",
                "cat": "ITHCK",
                "job": "Kỹ thuật Phần mềm (Software Engineering)",
                "venue": "Không gian Sáng tạo Khoa CNTT - ĐH Kiến Trúc Đà Nẵng",
                "start_date": today + timedelta(days=15),
                "end_date": today + timedelta(days=16),
                "points": 50,
                "max_attende": 200,
                "img": "event_image/it_dau_hackathon_2026.png",
                "palette": ((43, 16, 28), (153, 27, 27), (251, 146, 60)),
                "subtitle": "24 giờ lập trình liên tục kiến tạo các sản phẩm AI, IoT và Web/App phục vụ cộng đồng",
                "description": """
                    <h3>DAU IT Hackathon 2026 - 24h Sáng tạo Công nghệ</h3>
                    <p>Sân chơi lập trình lớn nhất năm dành cho các đội thi yêu thích phát triển sản phẩm phần mềm hoàn chỉnh chỉ trong 24 giờ:</p>
                    <ul>
                        <li>Chủ đề: <strong>Smart Campus, EdTech, Green IoT &amp; Chuyển đổi số Đô thị</strong>.</li>
                        <li>Cố vấn (Mentor) 1-1 từ các Tech Lead tại các công ty phần mềm lớn ở Đà Nẵng.</li>
                        <li>Cộng ngay <strong>50 điểm thưởng</strong> và Giấy chứng nhận cho tất cả thành viên hoàn thành.</li>
                    </ul>
                """,
                "agenda": {
                    "session_name": "Khai mạc Hackathon, Công bố Đề bài & Pitching Chung kết",
                    "speaker_name": "Ban Chủ nhiệm Khoa Công nghệ Thông tin",
                    "start_time": time(7, 30),
                    "end_time": time(17, 30),
                    "venue_name": "Không gian Sáng tạo Tầng 5",
                },
            },
            {
                "uid": 2026105,
                "name": "Chuyên đề Fullstack Web Hiện đại: Xây dựng Hệ thống Lớn với Python Django & React/Next.js",
                "cat": "ITDEV",
                "job": "Phát triển Web & Ứng dụng Di động",
                "venue": "Phòng Hội thảo 305 - ĐH Kiến Trúc Đà Nẵng",
                "start_date": today + timedelta(days=18),
                "end_date": today + timedelta(days=18),
                "points": 25,
                "max_attende": 100,
                "img": "event_image/it_fullstack_django_react.png",
                "palette": ((15, 23, 42), (37, 99, 235), (96, 165, 250)),
                "subtitle": "Thiết kế RESTful API, tối ưu truy vấn Database, Caching với Redis và kiến trúc Frontend",
                "description": """
                    <h3>Chuyên đề Fullstack Web với Django &amp; React</h3>
                    <p>Buổi chia sẻ chuyên sâu giúp sinh viên làm Đồ án tốt nghiệp và chuẩn bị đi thực tập nắm vững kiến trúc ứng dụng Web thực tế:</p>
                    <ul>
                        <li>Tối ưu hóa ORM trong Django (`select_related`, `prefetch_related`, Indexing).</li>
                        <li>Xác thực bảo mật với JWT, OAuth2 và tích hợp thanh toán / mã QR điện tử.</li>
                        <li>Kinh nghiệm tổ chức source code sạch (Clean Architecture) và viết Unit Test tự động.</li>
                    </ul>
                """,
                "agenda": {
                    "session_name": "Kiến trúc Backend hiệu năng cao với Django & Tích hợp Frontend hiện đại",
                    "speaker_name": "KS. Phạm Nhật Minh - Fullstack Tech Lead",
                    "start_time": time(14, 0),
                    "end_time": time(17, 0),
                    "venue_name": "Phòng Hội thảo 305",
                },
            },
            {
                "uid": 2026106,
                "name": "Ngày hội Tuyển dụng & Triển lãm Đồ án Công nghệ Thông tin (DAU IT Job Fair & Tech Expo 2026)",
                "cat": "ITCAR",
                "job": "Kỹ thuật Phần mềm (Software Engineering)",
                "venue": "Sảnh Chính & Hội trường Lớn - ĐH Kiến Trúc Đà Nẵng",
                "start_date": today + timedelta(days=22),
                "end_date": today + timedelta(days=22),
                "points": 40,
                "max_attende": 300,
                "img": "event_image/it_job_fair_expo_2026.png",
                "palette": ((19, 19, 48), (79, 70, 229), (165, 180, 252)),
                "subtitle": "Kết nối hơn 20 doanh nghiệp phần mềm hàng đầu, phỏng vấn trực tiếp và trưng bày đồ án CNTT",
                "description": """
                    <h3>DAU IT Job Fair &amp; Tech Expo 2026</h3>
                    <p>Sự kiện thường niên quy tụ các doanh nghiệp Công nghệ Thông tin hàng đầu tại Đà Nẵng và miền Trung (FPT Software, KMS Technology, Axon Active, Enclave, BAP IT...):</p>
                    <ul>
                        <li>Hơn <strong>200+ vị trí Thực tập sinh (Internship) &amp; Fresher</strong> các mảng Web, Mobile, AI, QA/Tester, DevOps.</li>
                        <li>Hoạt động <strong>Review CV 1-1</strong> và phỏng vấn thử trực tiếp cùng chuyên gia tuyển dụng IT.</li>
                        <li>Khu vực trưng bày Top 25 Đồ án Tốt nghiệp CNTT xuất sắc nhất năm.</li>
                    </ul>
                """,
                "agenda": {
                    "session_name": "Lễ Khai mạc IT Job Fair, Tham quan Gian hàng & Phỏng vấn Trực tiếp",
                    "speaker_name": "Đại diện Khoa CNTT & Các Doanh nghiệp Đối tác",
                    "start_time": time(8, 0),
                    "end_time": time(16, 30),
                    "venue_name": "Sảnh Chính & Hội trường Lớn",
                },
            },
            {
                "uid": 2026107,
                "name": "Bootcamp Khoa học Dữ liệu: Phân tích Dữ liệu Lớn & Trực quan hóa với Python, Pandas và Power BI",
                "cat": "ITAID",
                "job": "Trí tuệ Nhân tạo & Khoa học Dữ liệu (AI & Data Science)",
                "venue": "Phòng Lab Dữ liệu 308 - ĐH Kiến Trúc Đà Nẵng",
                "start_date": today + timedelta(days=25),
                "end_date": today + timedelta(days=26),
                "points": 30,
                "max_attende": 90,
                "img": "event_image/it_data_science_bootcamp.png",
                "palette": ((17, 24, 39), (109, 40, 217), (244, 114, 182)),
                "subtitle": "Thực hành làm sạch dữ liệu, xây dựng Pipeline ETL và thiết kế Dashboard phân tích quyết định",
                "description": """
                    <h3>Bootcamp Khoa học Dữ liệu &amp; Business Intelligence</h3>
                    <p>Khóa huấn luyện ngắn hạn giúp sinh viên CNTT làm chủ kỹ năng xử lý dữ liệu thực tế từ con số 0:</p>
                    <ul>
                        <li>Khai phá và làm sạch bộ dữ liệu hàng triệu dòng với <strong>Python, Pandas &amp; Polars</strong>.</li>
                        <li>Xây dựng mô hình dự báo xu hướng bằng <strong>Scikit-Learn &amp; XGBoost</strong>.</li>
                        <li>Thiết kế báo cáo trực quan tương tác cho doanh nghiệp.</li>
                    </ul>
                """,
                "agenda": {
                    "session_name": "Thực hành: Xây dựng End-to-End Data Pipeline & Machine Learning Model",
                    "speaker_name": "ThS. Võ Thanh Tùng - Lead Data Scientist",
                    "start_time": time(8, 30),
                    "end_time": time(16, 0),
                    "venue_name": "Phòng Lab 308",
                },
            },
            {
                "uid": 2026108,
                "name": "Tech Talk UI/UX & Product Design: Thiết kế Giao diện Trải nghiệm Người dùng cho Kỹ sư Phần mềm",
                "cat": "ITDEV",
                "job": "Thiết kế UI/UX & Sản phẩm Số",
                "venue": "Phòng Seminar 204 - ĐH Kiến Trúc Đà Nẵng",
                "start_date": today + timedelta(days=28),
                "end_date": today + timedelta(days=28),
                "points": 20,
                "max_attende": 100,
                "img": "event_image/it_uiux_product_design.png",
                "palette": ((24, 24, 42), (190, 24, 93), (251, 113, 133)),
                "subtitle": "Làm chủ Design System trên Figma, tư duy UX hiện đại và chuyển đổi mượt mà sang Frontend Code",
                "description": """
                    <h3>Tech Talk: UI/UX &amp; Design System dành cho Developer</h3>
                    <p>Làm sao để sản phẩm phần mềm hay Đồ án tốt nghiệp của bạn không chỉ chạy đúng mà còn có giao diện đẹp, hiện đại và dễ sử dụng?</p>
                    <ul>
                        <li>Nguyên tắc <strong>Visual Hierarchy, Typography, Color Palette</strong> trong ứng dụng Web/App.</li>
                        <li>Xây dựng Component Library trên <strong>Figma</strong> và quy trình bàn giao cho Frontend Developer.</li>
                        <li>Thực hành nâng cấp giao diện Dashboard thực tế ngay tại buổi học.</li>
                    </ul>
                """,
                "agenda": {
                    "session_name": "Từ Wireframe đến Design System & High-Conversion Web UI",
                    "speaker_name": "Chuyên gia Đặng Thu Hà - Senior Product Designer",
                    "start_time": time(14, 0),
                    "end_time": time(16, 30),
                    "venue_name": "Phòng Seminar 204",
                },
            },
            {
                "uid": 2026109,
                "name": "Hội nghị Thượng đỉnh AI Tạo sinh 2026: Xây dựng Hệ thống Multi-Agent với LangGraph & DeepSeek",
                "cat": "AILMM",
                "job": "Kỹ sư Mô hình Ngôn ngữ Lớn & AI Tạo sinh (LLM & GenAI)",
                "venue": "Công viên Phần mềm Đà Nẵng - Số 02 Quang Trung",
                "location": "108.222500,16.077200",
                "start_date": today + timedelta(days=3),
                "end_date": today + timedelta(days=3),
                "points": 45,
                "max_attende": 250,
                "img": "event_image/ai_multi_agent_summit_2026.png",
                "palette": ((28, 12, 54), (107, 33, 168), (232, 121, 249)),
                "subtitle": "Kiến trúc AI tự suy luận (Reasoning Models), điều phối đa tác tử và ứng dụng vào sản xuất phần mềm",
                "description": """
                    <h3>Hội nghị Thượng đỉnh AI Tạo sinh &amp; Multi-Agent 2026</h3>
                    <p>Khám phá bước tiến mới nhất của ngành <strong>Trí tuệ Nhân tạo (AI)</strong> khi các mô hình LLM không chỉ trò chuyện mà còn tự lập kế hoạch, viết code và phối hợp giải quyết bài toán phức tạp:</p>
                    <ul>
                        <li>So sánh thực chiến các mô hình <strong>GPT, Claude, Gemini và DeepSeek R1</strong>.</li>
                        <li>Xây dựng quy trình <strong>Multi-Agent</strong> tự động nghiên cứu, viết code và kiểm thử với LangGraph.</li>
                        <li>Triển khai mô hình AI cục bộ (Local LLM) bảo mật dữ liệu với Ollama &amp; vLLM.</li>
                    </ul>
                """,
                "agenda": {
                    "session_name": "Keynote: Kỷ nguyên Agentic AI & Thực hành Xây dựng AI Đội nhóm",
                    "speaker_name": "PGS.TS. Hoàng Minh Đức - Viện Nghiên cứu Trí tuệ Nhân tạo",
                    "start_time": time(8, 30),
                    "end_time": time(11, 30),
                    "venue_name": "Hội trường Tầng 4 - Công viên Phần mềm ĐN",
                },
            },
            {
                "uid": 2026110,
                "name": "Workshop Thị giác Máy tính (Computer Vision): Nhận diện Thời gian thực với YOLOv11 & OpenCV",
                "cat": "AICVR",
                "job": "Thị giác Máy tính & Robot Thông minh (Computer Vision)",
                "venue": "Phòng Lab AI & Robotics 501 - ĐH Kiến Trúc Đà Nẵng",
                "location": "108.220832,16.047079",
                "start_date": today + timedelta(days=6),
                "end_date": today + timedelta(days=6),
                "points": 35,
                "max_attende": 85,
                "img": "event_image/ai_computer_vision_yolo.png",
                "palette": ((10, 28, 44), (14, 116, 144), (103, 232, 249)),
                "subtitle": "Huấn luyện mô hình phát hiện vật thể, nhận diện biển số xe và điểm danh khuôn mặt tự động",
                "description": """
                    <h3>Workshop Thực hành Computer Vision &amp; Deep Learning</h3>
                    <p>Buổi thực hành chuyên sâu dành cho sinh viên yêu thích mảng <strong>Xử lý ảnh và Thị giác máy tính</strong>:</p>
                    <ul>
                        <li>Chuẩn bị tập dữ liệu (Dataset Annotation) trên Roboflow và huấn luyện <strong>YOLOv11</strong> trên Google Colab / GPU.</li>
                        <li>Xây dựng ứng dụng <strong>Điểm danh khuôn mặt (Face Recognition)</strong> và giám sát giao thông thông minh.</li>
                        <li>Tối ưu mô hình với ONNX / TensorRT để chạy mượt trên thiết bị biên (Jetson Nano / Raspberry Pi).</li>
                    </ul>
                """,
                "agenda": {
                    "session_name": "Hands-on: Huấn luyện YOLOv11 trên Custom Dataset & Tích hợp Web Camera",
                    "speaker_name": "TS. Đỗ Quang Huy - Chuyên gia Computer Vision",
                    "start_time": time(13, 30),
                    "end_time": time(17, 0),
                    "venue_name": "Phòng Lab AI 501",
                },
            },
            {
                "uid": 2026111,
                "name": "Chuyên đề RAG & Vector Database: Xây dựng Trợ lý AI Hỏi đáp Tài liệu Tiếng Việt Chuyên ngành",
                "cat": "AILMM",
                "job": "Kỹ sư Mô hình Ngôn ngữ Lớn & AI Tạo sinh (LLM & GenAI)",
                "venue": "Hội trường A - ĐH Kiến Trúc Đà Nẵng (566 Núi Thành)",
                "location": "108.221900,16.048100",
                "start_date": today + timedelta(days=10),
                "end_date": today + timedelta(days=10),
                "points": 40,
                "max_attende": 120,
                "img": "event_image/ai_rag_vector_db_2026.png",
                "palette": ((25, 18, 56), (91, 33, 182), (196, 181, 253)),
                "subtitle": "Kỹ thuật Chunking, Embedding tiếng Việt, tìm kiếm ngữ nghĩa với Qdrant/ChromaDB và chống ảo giác (Hallucination)",
                "description": """
                    <h3>Chuyên đề RAG (Retrieval-Augmented Generation) Thực chiến</h3>
                    <p>Đề tài <strong>Chatbot AI hỏi đáp tài liệu nội bộ (RAG)</strong> đang là hướng Đồ án tốt nghiệp hot nhất ngành CNTT. Chuyên đề sẽ hướng dẫn chi tiết từ A-Z:</p>
                    <ul>
                        <li>Trích xuất văn bản từ PDF, Word, Website và chiến lược chia nhỏ văn bản (Semantic Chunking).</li>
                        <li>Sử dụng mô hình <strong>Vietnamese Embedding</strong> kết hợp cơ sở dữ liệu vector (Qdrant, Milvus, pgvector).</li>
                        <li>Đánh giá độ chính xác của hệ thống RAG và tích hợp trực tiếp vào website Django.</li>
                    </ul>
                """,
                "agenda": {
                    "session_name": "Live Coding: Tích hợp Chatbot RAG Tiếng Việt vào Website Django trong 90 phút",
                    "speaker_name": "KS. Nguyễn Hoàng Long - AI Solutions Architect",
                    "start_time": time(8, 30),
                    "end_time": time(11, 30),
                    "venue_name": "Hội trường A",
                },
            },
            {
                "uid": 2026112,
                "name": "Hội thảo Công nghệ Vi mạch Bán dẫn & AIoT: Cơ hội Bứt phá cho Kỹ sư CNTT Miền Trung",
                "cat": "ITIOT",
                "job": "Hệ thống Nhúng, IoT & Vi mạch Bán dẫn (AIoT & Chip)",
                "venue": "Khu Công nghệ cao Đà Nẵng - Hòa Liên, Hòa Vang",
                "location": "108.078500,16.112500",
                "start_date": today + timedelta(days=14),
                "end_date": today + timedelta(days=14),
                "points": 35,
                "max_attende": 160,
                "img": "event_image/it_aiot_semiconductor_2026.png",
                "palette": ((8, 36, 26), (22, 101, 52), (110, 231, 183)),
                "subtitle": "Xu hướng thiết kế chip AI, lập trình nhúng C/C++/Rust và hệ sinh thái IoT thông minh tại Đà Nẵng",
                "description": """
                    <h3>Hội thảo Vi mạch Bán dẫn &amp; Hệ thống Nhúng AIoT 2026</h3>
                    <p>Đà Nẵng đang trở thành trung tâm <strong>Vi mạch bán dẫn và AI</strong> mới của Việt Nam. Hội thảo mang đến góc nhìn toàn diện và cơ hội học bổng/tuyển dụng cho sinh viên CNTT:</p>
                    <ul>
                        <li>Quy trình thiết kế vi mạch số (VLSI Design) và kiểm thử chip (IC Verification).</li>
                        <li>Đưa mô hình học sâu lên vi điều khiển (TinyML / Edge AI trên ESP32 &amp; STM32).</li>
                        <li>Giao lưu trực tiếp với các kỹ sư trưởng từ Synopsys, Marvell và FPT Semiconductor.</li>
                    </ul>
                """,
                "agenda": {
                    "session_name": "Toàn cảnh Ngành Chip Bán dẫn & Demo Hệ thống Nhà Thông minh AIoT",
                    "speaker_name": "TS. Phan Văn Khải - Chuyên gia Hệ thống Nhúng & Vi mạch",
                    "start_time": time(8, 0),
                    "end_time": time(11, 30),
                    "venue_name": "Trung tâm Hội nghị Khu Công nghệ cao",
                },
            },
            {
                "uid": 2026113,
                "name": "Cuộc thi Đấu trường Trí tuệ Nhân tạo (DAU AI Challenge 2026): Giải bài toán Đô thị Thông minh",
                "cat": "ITHCK",
                "job": "Trí tuệ Nhân tạo & Khoa học Dữ liệu (AI & Data Science)",
                "venue": "Hội trường Lớn - ĐH Kiến Trúc Đà Nẵng",
                "location": "108.220200,16.046500",
                "start_date": today + timedelta(days=19),
                "end_date": today + timedelta(days=20),
                "points": 60,
                "max_attende": 180,
                "img": "event_image/ai_challenge_contest_2026.png",
                "palette": ((48, 14, 24), (185, 28, 28), (253, 186, 116)),
                "subtitle": "Tranh tài huấn luyện mô hình AI xử lý ngôn ngữ tự nhiên tiếng Việt và dự báo giao thông đô thị",
                "description": """
                    <h3>DAU AI Challenge 2026 - Đấu trường Trí tuệ Nhân tạo</h3>
                    <p>Cuộc thi học thuật thường niên dành cho các đội thi đam mê <strong>Machine Learning, Deep Learning và Data Science</strong>:</p>
                    <ul>
                        <li>Bảng A: <strong>Xử lý Ngôn ngữ Tự nhiên (NLP)</strong> — Phân tích cảm xúc &amp; tóm tắt văn bản tiếng Việt.</li>
                        <li>Bảng B: <strong>Computer Vision</strong> — Nhận diện vi phạm an toàn giao thông qua camera.</li>
                        <li>Tổng giải thưởng tiền mặt, tài khoản Cloud GPU miễn phí và <strong>+60 điểm thưởng rèn luyện</strong>.</li>
                    </ul>
                """,
                "agenda": {
                    "session_name": "Vòng Chung kết Live-Benchmark & Lễ Trao giải DAU AI Challenge",
                    "speaker_name": "Hội đồng Giám khảo Chuyên gia AI & Khoa CNTT",
                    "start_time": time(8, 0),
                    "end_time": time(17, 0),
                    "venue_name": "Hội trường Lớn",
                },
            },
            {
                "uid": 2026114,
                "name": "Diễn đàn Blockchain, Web3 & FinTech 2026: Lập trình Smart Contract & Bảo mật Tài sản Số",
                "cat": "ITW3F",
                "job": "Công nghệ Chuỗi khối & Tài chính Số (Blockchain & FinTech)",
                "venue": "Công viên Phần mềm số 2 - Hải Châu, Đà Nẵng",
                "location": "108.224800,16.086500",
                "start_date": today + timedelta(days=23),
                "end_date": today + timedelta(days=23),
                "points": 30,
                "max_attende": 130,
                "img": "event_image/it_blockchain_fintech_2026.png",
                "palette": ((38, 22, 10), (180, 83, 9), (252, 211, 77)),
                "subtitle": "Ứng dụng chuỗi khối trong truy xuất nguồn gốc, xác thực văn bằng số chống giả và cổng thanh toán điện tử",
                "description": """
                    <h3>Diễn đàn Công nghệ Blockchain &amp; FinTech 2026</h3>
                    <p>Tìm hiểu ứng dụng thực tiễn của <strong>Blockchain</strong> vượt ra ngoài tiền mã hóa vào lĩnh vực ngân hàng số, chứng nhận điện tử và chuỗi cung ứng:</p>
                    <ul>
                        <li>Viết và kiểm toán hợp đồng thông minh (Smart Contract Audit) với <strong>Solidity &amp; Rust</strong>.</li>
                        <li>Ứng dụng Blockchain &amp; SHA-256 trong cấp phát văn bằng, chứng chỉ sự kiện chống làm giả.</li>
                        <li>Kiến trúc cổng thanh toán số hiệu năng cao (High-Throughput Payment Gateway).</li>
                    </ul>
                """,
                "agenda": {
                    "session_name": "Chuyên đề: Bảo mật Smart Contract & Ứng dụng Blockchain trong Giáo dục Số",
                    "speaker_name": "KS. Vũ Đình Khôi - Blockchain Core Developer",
                    "start_time": time(14, 0),
                    "end_time": time(17, 0),
                    "venue_name": "Hội trường Khu A - Công viên Phần mềm số 2",
                },
            },
        ]

        created_count = 0
        updated_count = 0
        for edata in it_events:
            generate_tech_banner(
                rel_path=edata["img"],
                title=edata["name"],
                subtitle=edata["subtitle"],
                tag=edata["cat"],
                palette=edata["palette"],
            )
            cat_obj = cat_map[edata["cat"]]
            job_obj = job_map[edata["job"]]

            evt = (
                Event.objects.filter(uid=edata["uid"]).first()
                or Event.objects.filter(name=edata["name"]).first()
            )
            if evt:
                evt.category = cat_obj
                evt.name = edata["name"]
                evt.description = edata["description"].strip()
                evt.job_category = job_obj
                evt.scheduled_status = "scheduled"
                evt.venue = edata["venue"]
                evt.start_date = edata["start_date"]
                evt.end_date = edata["end_date"]
                evt.location = edata.get("location", "108.220832,16.047079")
                evt.points = edata["points"]
                evt.maximum_attende = edata["max_attende"]
                evt.status = "active"
                evt.updated_user = admin_user
                evt.save()
                updated_count += 1
            else:
                evt = Event.objects.create(
                    category=cat_obj,
                    name=edata["name"],
                    uid=edata["uid"],
                    description=edata["description"].strip(),
                    job_category=job_obj,
                    scheduled_status="scheduled",
                    venue=edata["venue"],
                    start_date=edata["start_date"],
                    end_date=edata["end_date"],
                    location=edata.get("location", "108.220832,16.047079"),
                    points=edata["points"],
                    maximum_attende=edata["max_attende"],
                    created_user=admin_user,
                    updated_user=admin_user,
                    status="active",
                )
                created_count += 1

            # Gắn hoặc cập nhật EventImage
            EventImage.objects.update_or_create(
                event=evt,
                defaults={"image": edata["img"]},
            )

            # Gắn EventAgenda nếu chưa có
            ag = edata["agenda"]
            if not EventAgenda.objects.filter(event=evt).exists():
                EventAgenda.objects.create(
                    event=evt,
                    session_name=ag["session_name"],
                    speaker_name=ag["speaker_name"],
                    start_time=ag["start_time"],
                    end_time=ag["end_time"],
                    venue_name=ag["venue_name"],
                )

        # 4. Tự động tạo & gắn ảnh banner CNTT cho bất kỳ sự kiện cũ nào trong DB chưa có ảnh
        palettes = [
            ((15, 23, 42), (30, 64, 175), (56, 189, 248)),
            ((23, 15, 45), (88, 28, 135), (192, 132, 252)),
            ((6, 32, 28), (6, 95, 70), (52, 211, 153)),
            ((15, 23, 42), (12, 74, 110), (34, 211, 238)),
        ]
        backfilled = 0
        for idx, ev in enumerate(Event.objects.select_related("category").all()):
            ev_img = EventImage.objects.filter(event=ev).first()
            img_disk = os.path.join(settings.MEDIA_ROOT, str(ev_img.image)) if (ev_img and ev_img.image) else ""
            if not ev_img or not ev_img.image or not os.path.exists(img_disk):
                rel = f"event_image/event_banner_{ev.id}.png"
                generate_tech_banner(
                    rel_path=rel,
                    title=ev.name,
                    subtitle=f"Địa điểm: {ev.venue}",
                    tag=ev.category.code if ev.category else "CNTT",
                    palette=palettes[idx % len(palettes)],
                )
                EventImage.objects.update_or_create(
                    event=ev,
                    defaults={"image": rel},
                )
                backfilled += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Hoàn tất! Đã tạo mới {created_count} sự kiện CNTT, cập nhật {updated_count} sự kiện, "
                f"và bổ sung ảnh banner cho {backfilled} sự kiện cũ."
            )
        )

