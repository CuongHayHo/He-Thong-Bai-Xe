# PREMIUM SMART PARKING SYSTEM 🚗💨

Hệ thống quản lý bãi đỗ xe thông minh sử dụng **ESP32** (Quản lý cổng) và **Arduino Uno R4 WiFi** (Quản lý vị trí đỗ), kết nối với PC App qua giao thức Socket TCP.

---

## 🏗️ Kiến Trúc Hệ Thống

Hệ thống hoạt động trên mô hình Client-Server với 2 luồng độc lập:
- **Cổng 5000**: Dành cho ESP32 xử lý RFID và Cửa tự động.
- **Cổng 5001**: Dành cho Uno R4 xử lý 6 cảm biến siêu âm theo dõi chỗ trống.
- **PC App**: Xây dựng bằng Python (Tkinter + Socket + Threading).

---

## 🔌 Sơ Đồ Đấu Dây (Wiring Diagram)

### 1. ESP32 (Bộ điều khiển Cổng)
Mạch sử dụng chung bus SPI cho 2 đầu đọc RFID.

| Linh kiện | Chân trên ESP32 | Ghi chú |
| :--- | :--- | :--- |
| **RFID RC522 (Chung)** | SCK(18), MOSI(23), MISO(19) | Bus SPI chung |
| **RFID VÀO** | SDA(5), RST(25) | |
| **RFID RA** | SDA(15), RST(26) | |
| **Servo VÀO** | D32 | |
| **Servo RA** | D33 | |
| **Cảm biến Vật cản VÀO** | Trig(27), Echo(34) | HC-SR04 |
| **Cảm biến Vật cản RA** | Trig(4), Echo(35) | HC-SR04 |
| **LCD 16x2 (I2C)** | SDA(21), SCL(22) | |

### 2. Arduino Uno R4 WiFi (Bộ theo dõi Chỗ trống)
Quản lý 6 vị trí đỗ xe bằng cảm biến siêu âm HC-SR04.

| Vị trí | Chân Trig | Chân Echo |
| :--- | :--- | :--- |
| **Slot 1** | 2 | 8 |
| **Slot 2** | 3 | 9 |
| **Slot 3** | 4 | 10 |
| **Slot 4** | 5 | 11 |
| **Slot 5** | 6 | 12 |
| **Slot 6** | 7 | 13 |

---

## 💻 Cấu Hình Phần Mềm

### 1. WiFi & Mạng
- **SSID**: `` (Nhập tên WiFi của bạn)
- **Password**: `` (Nhập mật khẩu WiFi)
- **IP Server (PC)**: `` (Nhập IP của máy tính - Cần đặt IP tĩnh cho máy tính phát WiFi).

### 2. PC Application
Yêu cầu Python 3.10+. Chạy lệnh khởi động:
```powershell
python .\main_pro.py
```

---

## 🌟 Tính Năng Nổi Bật

1. **Giao diện Real-time**: Dashboard hiện đại, cập nhật tức thời trạng thái xe và vị trí trống.
2. **Quản lý 6 chỗ đỗ**: Sử dụng thuật toán **Median Filter** để lọc nhiễu cảm biến, đảm bảo số liệu không bị nhảy ảo.
3. **Phân quyền thẻ**: Hỗ trợ thẻ Admin (miễn phí) và thẻ User (tính tiền theo giờ).
4. **Báo cáo chuyên nghiệp**:
   - Tự động lưu lịch sử vào JSON (`parking_data.json`).
   - Xuất báo cáo doanh thu ra file Excel/CSV kèm tổng cộng tiền.
   - Có tùy chọn xóa sạch lịch sử sau khi xuất báo cáo để chốt sổ.
5. **Ổn định cao**: Đa luồng (Threading) giúp App không bị treo khi xử lý đồng thời nhiều thiết bị.

---

## 📝 Lưu Ý Vận Hành
- Luôn khởi động PC App trước khi bật nguồn các mạch ESP32/Uno.
- Nếu App báo "Not Responding" khi chọn file lưu, hãy yên tâm là dữ liệu vẫn đang được xử lý ngầm, hộp thoại chọn file sẽ hiện lên ngay sau đó.
- Cảm biến siêu âm nên đặt cách mặt đất khoảng 10-15cm để nhận diện gầm xe tốt nhất.
