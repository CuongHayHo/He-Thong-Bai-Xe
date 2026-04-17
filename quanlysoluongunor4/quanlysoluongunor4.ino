#include "WiFiS3.h"

// --- CẤU HÌNH HỆ THỐNG ---
const char* ssid = "YOUR_WIFI_SSID";          // Tên WiFi
const char* password = "YOUR_WIFI_PASSWORD";        // Mật khẩu WiFi
const char* serverIP = "YOUR_SERVER_IP";    // IP máy tính (Server)
const int serverPort = 5001;               // Cổng Server (Dành cho Uno R4)
#define AUTH_TOKEN "YOUR_SECRET_TOKEN"


#define NUM_SLOTS 6
#define NUM_SAMPLES 3      // Số lần đo để lấy trung vị (lọc nhiễu)
#define READ_DELAY 600      // Khoảng nghỉ giữa các cảm biến (ms)

// Khai báo các chân Pin tương ứng với 6 slot
const int trigPins[NUM_SLOTS] = {2, 3, 4, 5, 6, 7};
const int echoPins[NUM_SLOTS] = {8, 9, 10, 11, 12, 13};

// --- TRẠNG THÁI ---
bool slotStatus[NUM_SLOTS]; // false: TRỐNG, true: CÓ XE
WiFiClient client;

// ======================= HÀM HỖ TRỢ ĐO KHOẢNG CÁCH =======================

// Hàm đo 1 lần duy nhất
long readOnce(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(5);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Chờ phản hồi trong 35ms (~6 mét)
  long duration = pulseIn(echoPin, HIGH, 35000); 
  if (duration == 0) return -1;
  return duration * 0.034 / 2;
}

// Hàm lọc nhiễu (Lấy giá trị trung vị từ 3 lần đo)
long medianFilter(int trigPin, int echoPin) {
  long values[NUM_SAMPLES];
  for (int i = 0; i < NUM_SAMPLES; i++) {
    values[i] = readOnce(trigPin, echoPin);
    delay(15); // Nghỉ một chút giữa các mẫu của cùng 1 sensor
  }
  
  // Sắp xếp tăng dần (Bubble Sort đơn giản cho 3 phần tử)
  for (int i = 0; i < NUM_SAMPLES - 1; i++) {
    for (int j = i + 1; j < NUM_SAMPLES; j++) {
      if (values[j] < values[i]) {
        long tmp = values[i];
        values[i] = values[j];
        values[j] = tmp;
      }
    }
  }
  return values[NUM_SAMPLES / 2]; // Lấy giá trị chính giữa
}

// Hàm gửi dữ liệu lên Server
void sendUpdate(int slotIdx, bool occupied) {
  String status = occupied ? "OCCUPIED" : "VACANT";
  // Slot ID hiển thị trên App sẽ là 1, 2, 3, 4, 5, 6
  String json = "{\"action\": \"SLOT_UPDATE\", \"slot\": " + String(slotIdx + 1) + ", \"status\": \"" + status + "\", \"auth\": \"" + String(AUTH_TOKEN) + "\"}";

  
  if (client.connected()) {
    client.println(json);
    Serial.println("Gửi Server: " + json);
  }
}

// ======================= CÀI ĐẶT BAN ĐẦU =======================

void setup() {
  Serial.begin(115200);

  // Khởi tạo các chân chân Pin
  for (int i = 0; i < NUM_SLOTS; i++) {
    pinMode(trigPins[i], OUTPUT);
    pinMode(echoPins[i], INPUT);
    digitalWrite(trigPins[i], LOW);
    slotStatus[i] = false; // Mặc định tất cả các chỗ đều trống
  }

  // Kết nối WiFi
  Serial.print("Đang kết nối WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi đã kết nối thành công!");
}

// ======================= VÒNG LẶP CHÍNH =======================

void loop() {
  // Kiểm tra và duy trì kết nối với Server
  if (!client.connected()) {
    Serial.println("Đang kết nối lại với PC Server...");
    if (client.connect(serverIP, serverPort)) {
      Serial.println("Đã kết nối với PC Server thành công.");
      // Gửi trạng thái ban đầu ngay khi vừa kết nối
      for (int i = 0; i < NUM_SLOTS; i++) {
        sendUpdate(i, slotStatus[i]);
      }
    } else {
      Serial.println("Không thể kết nối Server. Thử lại sau 5 giây...");
      delay(5000);
      return;
    }
  }

  // Quét từng cảm biến một cách tuần tự
  for (int i = 0; i < NUM_SLOTS; i++) {
    long distance = medianFilter(trigPins[i], echoPins[i]);
    
    Serial.print("Slot ");
    Serial.print(i + 1);
    Serial.print(": ");
    if (distance == -1) Serial.println("Ngoại tầm");
    else {
      Serial.print(distance);
      Serial.println(" cm");
    }

    // Kiểm tra xe (dưới 10cm là có xe)
    bool currentOccupied = (distance > 0 && distance < 10);

    // Nếu trạng thái thay đổi so với lần quét trước thì gửi cập nhật
    if (currentOccupied != slotStatus[i]) {
      slotStatus[i] = currentOccupied;
      sendUpdate(i, slotStatus[i]);
    }

    delay(READ_DELAY); // Nghỉ giữa các cảm biến để tránh nhiễu chéo
  }

  Serial.println("--- Kết thúc một vòng quét ---");
}