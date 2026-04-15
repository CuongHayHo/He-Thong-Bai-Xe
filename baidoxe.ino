#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include <LiquidCrystal_I2C.h>
#include <MFRC522.h>
#include <SPI.h>
#include <WiFi.h>
#include <Wire.h>

const char *ssid = "YOUR_WIFI_SSID";         // Thay tên WiFi của bạn
const char *password = "YOUR_WIFI_PASSWORD"; // Thay mật khẩu WiFi
const char *server_ip = "192.168.x.x";       // Thay IP của máy tính chạy Python
const uint16_t server_port = 5000;

WiFiClient client;

// =====================================================================
// PIN DEFINITIONS
// =====================================================================
#define SS_PIN_IN 5
#define RST_PIN_IN 25
#define SS_PIN_OUT 15
#define RST_PIN_OUT 26
#define SERVO_IN_PIN 32
#define SERVO_OUT_PIN 33
#define TRIG_IN 27
#define ECHO_IN 34
#define TRIG_OUT 4
#define ECHO_OUT 35

// Config
#define ULTRA_THRESHOLD_CM 10
#define SERVO_OPEN_ANGLE 90
#define SERVO_CLOSED_ANGLE 0
#define SERVO_MAX_OPEN_MS 15000

// Hardware Init
// Hardware Init
LiquidCrystal_I2C lcd(0x27, 16, 2);
MFRC522 mfrc_in(SS_PIN_IN, RST_PIN_IN);
MFRC522 mfrc_out(SS_PIN_OUT, RST_PIN_OUT);
Servo servo_in, servo_out;

// =====================================================================
// STATE & COMMUNICATION
// =====================================================================
enum GateResponse {
  STATUS_WAIT,
  STATUS_SUCCESS,
  STATUS_REJECT,
  STATUS_WRONG_WAY,
  STATUS_MANUAL_OPEN
};

struct GateMsg {
  GateResponse status;
  long fee;
};

QueueHandle_t queueIn;
QueueHandle_t queueOut;

SemaphoreHandle_t lcdMutex;
SemaphoreHandle_t spiMutex;
SemaphoreHandle_t socketMutex;

// =====================================================================
// HELPERS
// =====================================================================

void updateLCD(const char *line1, String line2) {
  if (xSemaphoreTake(lcdMutex, portMAX_DELAY)) {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print(line1);
    lcd.setCursor(0, 1);
    lcd.print(line2);
    xSemaphoreGive(lcdMutex);
  }
}

float getDistance(int trig, int echo) {
  digitalWrite(trig, LOW);
  delayMicroseconds(2);
  digitalWrite(trig, HIGH);
  delayMicroseconds(10);
  digitalWrite(trig, LOW);
  long duration = pulseIn(echo, HIGH, 26000); // ~4m max
  return (duration == 0) ? 999 : (duration / 2.0) / 29.1;
}

void sendJson(const char *gate, const char *action, String uid,
              const char *msg) {
  if (client.connected()) {
    StaticJsonDocument<256> doc;
    doc["gate"] = gate;
    doc["action"] = action;
    doc["uid"] = uid;
    doc["msg"] = msg;

    if (xSemaphoreTake(socketMutex, portMAX_DELAY)) {
      serializeJson(doc, client);
      client.println();
      xSemaphoreGive(socketMutex);
    }
  }
}

void maintainConnection() {
  if (WiFi.status() != WL_CONNECTED) {
    updateLCD("WIFI CONNECTING", ssid);
    WiFi.begin(ssid, password);
    unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < 10000) {
      vTaskDelay(pdMS_TO_TICKS(500));
    }
  }

  if (WiFi.status() == WL_CONNECTED && !client.connected()) {
    updateLCD("SOCKET CONNECT..", server_ip);
    client.connect(server_ip, server_port);
    client.setTimeout(500); // Giảm xuống 500ms để phản hồi nhanh hơn
    vTaskDelay(pdMS_TO_TICKS(1000));

    if (client.connected()) {
      updateLCD("SYSTEM READY", "WIFI + SOCKET");
    }
  }
}

bool waitVehicle(int trig, int echo, MFRC522 &mfrc, const char *gate,
                 Servo &srv) {
  unsigned long start = millis();
  bool detected = false;
  bool passed = false;

  while (millis() - start < SERVO_MAX_OPEN_MS) {
    float d = getDistance(trig, echo);
    if (!detected && d < ULTRA_THRESHOLD_CM) {
      detected = true;
    } else if (detected && d >= ULTRA_THRESHOLD_CM) {
      vTaskDelay(pdMS_TO_TICKS(100));
      passed = true;
      break;
    }

    // --- KIỂM TRA THẺ QUÉT THÊM (BÁO BẬN) ---
    if (xSemaphoreTake(spiMutex, 0)) {
      if (mfrc.PICC_IsNewCardPresent() && mfrc.PICC_ReadCardSerial()) {
        updateLCD(gate, "BUSY! PLS WAIT");
        mfrc.PICC_HaltA();
      }
      xSemaphoreGive(spiMutex);
    }

    vTaskDelay(pdMS_TO_TICKS(50));
  }

  srv.write(SERVO_CLOSED_ANGLE);
  vTaskDelay(
      pdMS_TO_TICKS(600)); // Đợi 0.6s vừa đủ để servo quay về vị trí đóng
  srv.detach();

  updateLCD("PARKING SYSTEM", "READY...");
  return passed;
}

// =====================================================================
// TASKS
// =====================================================================

void TaskSocketListener(void *pv) {
  while (1) {
    bool hasData = false;

    // Bảo vệ việc kiểm tra Socket
    if (xSemaphoreTake(socketMutex, portMAX_DELAY)) {
      if (client.connected() && client.available()) {
        hasData = true;
      }
      xSemaphoreGive(socketMutex);
    }

    if (hasData) {
      String line = "";
      if (xSemaphoreTake(socketMutex, portMAX_DELAY)) {
        line = client.readStringUntil('\n');
        xSemaphoreGive(socketMutex);
      }

      line.trim();
      if (line.length() > 0) {
        StaticJsonDocument<300> doc;
        DeserializationError error = deserializeJson(doc, line);
        if (!error) {
          String gate = doc["gate"];
          String action = doc["action"];

          if (action == "AUTH") {
            String status = doc["status"];
            GateMsg msg;
            msg.fee = doc.containsKey("fee") ? doc["fee"] : 0;
            msg.status = STATUS_REJECT;

            if (status == "SUCCESS")
              msg.status = STATUS_SUCCESS;
            else if (status == "WRONG_WAY")
              msg.status = STATUS_WRONG_WAY;

            if (gate == "IN")
              xQueueSend(queueIn, &msg, 0);
            else if (gate == "OUT")
              xQueueSend(queueOut, &msg, 0);

          } else if (action == "OPEN") {
            GateMsg msg = {STATUS_MANUAL_OPEN, 0};
            if (gate == "IN")
              xQueueSend(queueIn, &msg, 0);
            else if (gate == "OUT")
              xQueueSend(queueOut, &msg, 0);
          }
        }
      }
    }
    vTaskDelay(pdMS_TO_TICKS(1));
  }
}

void TaskGate(void *pv) {
  bool isInsideGate = (bool)pv;
  MFRC522 &mfrc = isInsideGate ? mfrc_in : mfrc_out;
  Servo &srv = isInsideGate ? servo_in : servo_out;
  const char *lcdName = isInsideGate ? "GATE IN" : "GATE OUT";
  int trig = isInsideGate ? TRIG_IN : TRIG_OUT;
  int echo = isInsideGate ? ECHO_IN : ECHO_OUT;

  while (1) {
    bool triggerOpen = false;
    String scannedUid = "";
    GateMsg receivedMsg;

    // 1. Kiểm tra lệnh mở cổng (Thủ công hoặc từ Socket)
    if (xQueueReceive(isInsideGate ? queueIn : queueOut, &receivedMsg, 0) ==
        pdTRUE) {
      if (receivedMsg.status == STATUS_MANUAL_OPEN) {
        triggerOpen = true;
        updateLCD(lcdName, "MANUAL OPENING");
      }
    }

    // 2. Scan RFID (Nếu chưa được mở thủ công)
    bool cardFound = false;
    if (!triggerOpen) {
      if (xSemaphoreTake(spiMutex, portMAX_DELAY)) {
        if (mfrc.PICC_IsNewCardPresent() && mfrc.PICC_ReadCardSerial()) {
          for (byte i = 0; i < mfrc.uid.size; i++) {
            scannedUid += String(mfrc.uid.uidByte[i] < 0x10 ? "0" : "") +
                          String(mfrc.uid.uidByte[i], HEX) +
                          (i == mfrc.uid.size - 1 ? "" : " ");
          }
          scannedUid.toUpperCase();
          cardFound = true;
        }
        xSemaphoreGive(spiMutex);
      }
    }

    if (cardFound) {
      // 1. GỬI YÊU CẦU NGAY LẬP TỨC
      sendJson(isInsideGate ? "GATE IN" : "GATE OUT", "CHECK", scannedUid,
               "Auth Req");
      updateLCD(lcdName, "WAITING PC...");

      // 2. Chờ kết quả từ Queue thay vì dùng loop polling
      if (xQueueReceive(isInsideGate ? queueIn : queueOut, &receivedMsg,
                        pdMS_TO_TICKS(5000)) == pdTRUE) {
        if (receivedMsg.status == STATUS_SUCCESS) {
          triggerOpen = true;
          if (!isInsideGate) {
            updateLCD("SUCCESS! EXIT",
                      "FEE: " + String(receivedMsg.fee) + "VND");
            vTaskDelay(pdMS_TO_TICKS(500));
          } else {
            updateLCD(lcdName, "SUCCESS! WELCOME");
          }
        } else if (receivedMsg.status == STATUS_WRONG_WAY) {
          updateLCD(lcdName, "ALREDY IN/OUT");
        } else if (receivedMsg.status == STATUS_REJECT) {
          updateLCD(lcdName, "CARD REJECTED");
        } else if (receivedMsg.status == STATUS_MANUAL_OPEN) {
          triggerOpen = true;
          updateLCD(lcdName, "MANUAL OPENING");
        }
      } else {
        updateLCD(lcdName, "PC TIMEOUT");
      }

      if (xSemaphoreTake(spiMutex, portMAX_DELAY)) {
        mfrc.PICC_HaltA();
        xSemaphoreGive(spiMutex);
      }
    }

    // 3. Servo Action
    if (triggerOpen) {
      srv.attach(isInsideGate ? SERVO_IN_PIN : SERVO_OUT_PIN);
      srv.write(SERVO_OPEN_ANGLE);

      if (waitVehicle(trig, echo, mfrc, lcdName, srv)) {
        sendJson(isInsideGate ? "GATE IN" : "GATE OUT", "DONE", scannedUid,
                 "Process Complete");
      } else {
        updateLCD(lcdName, "TIMEOUT! CLOSED");
        vTaskDelay(pdMS_TO_TICKS(1000));
      }
    }
    vTaskDelay(pdMS_TO_TICKS(20));
  }
}

void setup() {
  lcdMutex = xSemaphoreCreateMutex();
  spiMutex = xSemaphoreCreateMutex();
  socketMutex = xSemaphoreCreateMutex();

  queueIn = xQueueCreate(5, sizeof(GateMsg));
  queueOut = xQueueCreate(5, sizeof(GateMsg));

  Wire.begin(21, 22);
  lcd.init();
  lcd.backlight();
  lcd.clear();

  // Dùng chung một bus SPI duy nhất cho cả 2 cổng
  SPI.begin(18, 19, 23);
  mfrc_in.PCD_Init();
  mfrc_out.PCD_Init();
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);

  servo_in.write(SERVO_CLOSED_ANGLE);
  servo_out.write(SERVO_CLOSED_ANGLE);
  pinMode(TRIG_IN, OUTPUT);
  pinMode(ECHO_IN, INPUT);
  pinMode(TRIG_OUT, OUTPUT);
  pinMode(ECHO_OUT, INPUT);

  xTaskCreatePinnedToCore(TaskSocketListener, "Socket", 4096, NULL, 3, NULL, 0);
  xTaskCreatePinnedToCore(TaskGate, "IN", 4096, (void *)true, 1, NULL, 1);
  xTaskCreatePinnedToCore(TaskGate, "OUT", 4096, (void *)false, 1, NULL, 1);

  updateLCD("PARKING SYSTEM", "READY...");
}

void loop() {
  maintainConnection();
  vTaskDelay(pdMS_TO_TICKS(1000));
}
