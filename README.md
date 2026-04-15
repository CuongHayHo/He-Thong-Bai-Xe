# 🚗 Smart Parking System - ESP32 & Python GUI

Hệ thống quản lý bãi đỗ xe thông minh sử dụng **ESP32** (FreeRTOS) kết nối với ứng dụng điều khiển trên máy tính viết bằng **Python**.

## 🌟 Tính năng nổi bật
- **Đồng bộ đa nhiệm (Real-time)**: Sử dụng FreeRTOS Queues trên ESP32 giúp phản hồi ngay lập tức, không gây trễ rào chắn.
- **Kiến trúc Tách lớp (Decoupled)**: Ứng dụng Python được chia làm Backend & Frontend, giúp hệ thống ổn định, chống treo (Not Responding).
- **Phản hồi cực nhanh**: Tối ưu hóa cảm biến siêu âm, đóng servo sau 0.1 giây khi xe qua.
- **Quản lý thẻ RFID**: Tự động nhận diện thẻ, tính phí dựa trên thời gian đỗ (VND/giờ).
- **Nhật ký hệ thống**: Lưu trữ lịch sử ra vào và doanh thu dưới dạng JSON và File Log.

## 🛠 Phần cứng sử dụng
- **MCU**: ESP32 (Vroom-32)
- **RFID**: MFRC522 (In/Out)
- **Sensor**: Ultrasonic HC-SR04
- **Servo**: SG90 / MG996
- **LCD**: I2C 16x2 / 20x4

## 💻 Phần mềm & Cấu trúc mã nguồn
```text
BAIDOXE_OPTIMIZED/
├── main_pro.py      # Điểm khởi chạy ứng dụng
├── backend.py       # Xử lý Socket, Database, Logic tính phí
├── frontend.py      # Giao diện Modern GUI (Tkinter)
└── parking_data.json # Cơ sở dữ liệu thẻ và lịch sử
```

## 🚀 Hướng dẫn cài đặt

### 1. Nạp code cho ESP32
- Mở `baidoxe.ino` bằng Arduino IDE.
- Cài đặt các thư viện: `MFRC522`, `ESP32Servo`, `ArduinoJson`.
- Cấu hình WiFi trong code và nạp xuống mạch.

### 2. Chạy ứng dụng PC
- Cài đặt Python 3.10+.
- Di chuyển vào thư mục: `cd BAIDOXE_OPTIMIZED`
- Khởi chạy: `python main_pro.py`

## 📝 Giấy phép
Hệ thống được phát triển nhằm mục đích học tập và ứng dụng thực tế quy mô nhỏ.
