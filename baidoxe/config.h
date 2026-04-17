#ifndef CONFIG_H
#define CONFIG_H

// WiFi Configuration
const char *ssid = "YOUR_WIFI_SSID";   // Thay tên WiFi của bạn
const char *password = "YOUR_WIFI_PASSWORD"; // Thay mật khẩu WiFi

// Server Configuration
const char *server_ip = "YOUR_SERVER_IP"; // Thay IP của máy tính chạy Python
const uint16_t server_port = 5000;

// Security Configuration
#define AUTH_TOKEN "YOUR_SECRET_TOKEN"

#endif
