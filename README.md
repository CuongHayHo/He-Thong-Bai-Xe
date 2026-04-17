# 🛡️ SECURE SMART PARKING SYSTEM v4.0 (SSL/TLS Edition) 🚗💨

Hệ thống quản lý bãi đỗ xe thông minh phiên bản **Bảo Mật Cao Cấp**, tích hợp mã hóa SSL/TLS và xác thực Token. Hệ thống sử dụng **ESP32** (Quản lý cổng) và **Arduino Uno R4 WiFi** (Quản lý vị trí đỗ), giúp đảm bảo an toàn tuyệt đối cho dữ liệu và điều khiển.

---

## 🏗️ Kiến Trúc Hệ Thống & Bảo Mật

Hệ thống hoạt động theo mô hình **Hybrid Security (Bảo mật Lai)**:
- **Cổng 5000 (GATE):** Dành cho ESP32. Sử dụng **SSL/TLS (WiFiClientSecure)** kết hợp **Auth Token** để mã hóa toàn bộ thông tin thẻ RFID và lệnh mở cổng.
- **Cổng 5001 (SLOT):** Dành cho Uno R4. Sử dụng **TCP Standard** kết hợp **Auth Token** để theo dõi 6 vị trí đỗ xe.
- **PC Dashboard:** Xây dựng bằng Python, hỗ trợ đa luồng và giao diện quản lý chuyên nghiệp.

---

## 🔒 Tính Năng Bảo Mật Nổi Bật

1.  **Mã hóa SSL/TLS (MbedTLS):** Toàn bộ dữ liệu giữa ESP32 và máy tính được mã hóa bằng thuật toán RSA 2048-bit, ngăn chặn hoàn toàn việc nghe lén UIDs trong mạng nội bộ.
2.  **Xác thực thiết bị (Auth Token):** Mọi gói tin gửi lên Server phải đính kèm mã định danh bí mật. Backend sẽ từ chối các kết nối giả mạo.
3.  **Chứng chỉ tự ký (Self-signed Cert):** Hệ thống tự quản lý chứng chỉ bảo mật mà không cần phụ thuộc vào bên thứ ba.

---

## 🛠️ Hướng Dẫn Cài Đặt

### 1. Chuẩn bị môi trường Python
Yêu cầu Python 3.10+. Cài đặt thư viện bảo mật:
```powershell
pip install cryptography
```

### 2. Thiết lập Chứng chỉ SSL
Chạy lệnh duy nhất để tạo chứng chỉ (có hạn 10 năm):
```powershell
python gen_cert.py
```

### 3. Cấu hình thông số

#### A. ESP32 - Tạo file `config.h`:
Tạo file **config.h** trong thư mục **BAIDOXE_OPTIMIZED/** (cùng thư mục với baidoxe.ino):

```cpp
// config.h
#ifndef CONFIG_H
#define CONFIG_H

#define WIFI_SSID "YOUR_SSID"
#define WIFI_PASSWORD "YOUR_PASSWORD"
#define SERVER_IP "192.168.X.X"
#define SERVER_PORT 5000
#define AUTH_TOKEN "your_secret_token_12345"

#endif
```

**Điền:**
- `YOUR_SSID`: Tên WiFi của bạn
- `YOUR_PASSWORD`: Mật khẩu WiFi
- `192.168.X.X`: IP của máy tính (đặt IP tĩnh)
- `AUTH_TOKEN`: Token bảo mật (tùy chọn, phải giống .env)

#### B. PC Backend - Tạo file `.env`:
Tạo file **.env** trong thư mục **BAIDOXE_OPTIMIZED/**:

```env
SSID=YOUR_SSID
PASSWORD=YOUR_PASSWORD
PORT_GATE=5000
PORT_SLOT=5001
HOURLY_RATE=10000
AUTH_TOKEN=your_secret_token_12345
```

**Điền:**
- `SSID` & `PASSWORD`: Giống ESP32
- `HOURLY_RATE`: Phí giữ xe theo giờ (đơn vị: đồng)
- `AUTH_TOKEN`: **Phải giống config.h** để xác thực ESP32

#### C. Chạy ứng dụng:
```powershell
cd BAIDOXE_OPTIMIZED
python main.py
```
---

## 🔌 Sơ Đồ Đấu Dây (Wiring Diagram)

### 1. ESP32 (Bộ điều khiển Cổng)
Mạch sử dụng chung bus SPI cho 2 đầu đọc RFID.

| Linh kiện | Chân trên ESP32 | Ghi chú |
| :--- | :--- | :--- |
| **RFID RC522 (Chung)** | SCK(18), MOSI(23), MISO(19) | Bus SPI chung |
| **RFID VÀO/RA** | SDA(5/15), RST(25/26) | |
| **Servo VÀO/RA** | D32 / D33 | |
| **Cảm biến Vật cản** | Trig(27/4), Echo(34/35) | HC-SR04 |
| **LCD 16x2 (I2C)** | SDA(21), SCL(22) | |

### 2. Arduino Uno R4 WiFi (Bộ theo dõi Chỗ trống)
Quản lý 6 vị trí đỗ xe (Slot 1-6) sử dụng các chân từ D2 đến D13.

---

## 🚀 Hướng Dẫn Chạy Hệ Thống (Step-by-Step)

### Bước 1: Chuẩn bị chứng chỉ SSL
Truy cập thư mục `BAIDOXE_OPTIMIZED` và chạy:
```powershell
cd BAIDOXE_OPTIMIZED
python gen_cert.py
```
*Kết quả: Xuất hiện file `server.crt` và `server.key`.*

### Bước 2: Thiết lập cấu hình (.env)
1. Copy file `.env.example` thành `.env` (ngay trong thư mục `BAIDOXE_OPTIMIZED`).
2. Mở file `.env` và điền mã Token bí mật của bạn vào dòng `AUTH_TOKEN`.

### Bước 3: Cấu hình và Nạp code phần cứng
1. Mở thư mục `baidoxe`: Sửa `config.h` (WiFi, IP máy tính, Token). Nạp cho ESP32.
2. Mở thư mục `quanlysoluongunor4`: Nạp cho Uno R4.

### Bước 4: Khởi động Ứng dụng Quản lý
Chạy lệnh sau ngay tại thư mục `BAIDOXE_OPTIMIZED`:
```powershell
python main.py
```

---

## 🌟 Tính Năng Nổi Bật
- ESP32 sử dụng chế độ `setInsecure()` để có thể làm việc trực tiếp với chứng chỉ tự ký của Server mà không cần nạp Root CA.
- Đảm bảo Firewall của Windows cho phép các ứng dụng Python lắng nghe trên cổng 5000 và 5001.
