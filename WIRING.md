# Sơ đồ đấu nối Hệ thống Bãi đậu xe (Bản chung chân SPI - Ổn định nhất)

Bản quy hoạch này dùng chung chân SPI để đảm bảo tính tương thích cao nhất với LCD và thư viện Arduino.

## 1. Chân chung (Nối cả 2 RFID vào cùng 1 chân trên ESP32)
| Tín hiệu RFID | Chân ESP32 | Ghi chú |
| :--- | :--- | :--- |
| **SCK** | **GPIO 18** | Nối chung |
| **MISO** | **GPIO 19** | Nối chung |
| **MOSI** | **GPIO 23** | Nối chung |

---

## 2. Chân riêng cho từng bộ phận

### A. Cổng VÀO (Gate IN)
| Linh kiện | Chân Linh kiện | Chân ESP32 |
| :--- | :--- | :--- |
| **RFID IN** | SDA (SS) | **GPIO 5** |
| | RST | **GPIO 25** |
| **Siêu âm IN** | TRIG | **GPIO 27** |
| | ECHO | **GPIO 34** |
| **Servo IN** | PWM | **GPIO 32** |

### B. Cổng RA (Gate OUT)
| Linh kiện | Chân Linh kiện | Chân ESP32 |
| :--- | :--- | :--- |
| **RFID OUT** | SDA (SS) | **GPIO 15** |
| | RST | **GPIO 26** |
| **Siêu âm OUT** | TRIG | **GPIO 4** |
| | ECHO | **GPIO 35** |
| **Servo OUT** | PWM | **GPIO 33** |

### C. Màn hình LCD (I2C)
| Linh kiện | Chân Linh kiện | Chân ESP32 |
| :--- | :--- | :--- |
| **LCD 16x2** | SDA | **GPIO 21** |
| | SCL | **GPIO 22** |

---

## 3. Lưu ý nguồn điện
- **Servo:** Phải dùng nguồn 5V rời. Nối chung chân GND của nguồn rời với GND của ESP32.
- **RFID:** Cấp nguồn 3.3V ổn định.
