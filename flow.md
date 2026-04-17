## 📊 **Các Loại Biểu Đồ Nên Dùng:**

### **1. Kiến Trúc Hệ Thống**
- **Architecture Diagram**: Hiển thị mối quan hệ giữa ESP32, Arduino, PC App, và kết nối mạng

#### Architecture Diagram - Sơ đồ Client-Server

```mermaid
architecture-beta
    service esp32(server)[ESP32 Port5000]
    
    group server(cloud)[PC Server Application]
    service pcapp(server)[              PC Dashboard Server] in server
    service db(database)[Parking Data Storage] in server
    
    service uno(server)[Arduino Uno Port5001]
    
    esp32:R --> L:pcapp
    uno:L --> R:pcapp
    pcapp:B --> T:db
```

**Mô tả Client-Server:**
- **PC Application** (Server): Lắng nghe trên port 5000 & 5001, quản lý dữ liệu, hiển thị dashboard
  - **ESP32 (Client Port 5000)**: Kết nối tới Server, gửi dữ liệu RFID và điều khiển Cửa tự động
  - **Arduino Uno R4 (Client Port 5001)**: Kết nối tới Server, gửi trạng thái 6 vị trí đỗ xe
  - **Storage**: Lưu trữ dữ liệu vào file JSON (parking_data.json)

**Luồng giao tiếp:**
- ESP32 → PC Server (Port 5000): RFID tags, obstacle sensors
- Arduino R4 → PC Server (Port 5001): Parking slot occupancy (6 sensors)
- PC Server → Both Clients: Control commands (door control, etc.)

#### Sequence Diagram - Luồng Giao Tiếp Chi Tiết

```mermaid
sequenceDiagram
    participant Xe as Xe/Thẻ RFID
    participant ESP32
    participant Server as PC Dashboard Server
    participant Arduino as Arduino (Slots)

    Xe->>ESP32: Quét thẻ RFID
    activate ESP32
    ESP32->>Server: Gửi dữ liệu thẻ (Card ID)
    deactivate ESP32
    
    activate Server
    Server->>Server: Kiểm tra loại thẻ<br/>(Admin/User)
    Server->>Server: Ghi nhận thời gian vào
    alt Thẻ Admin
        Server->>Server: Vào miễn phí
    else Thẻ User
        Server->>Server: Bắt đầu tính tiền
    end
    Server->>ESP32: Mở cửa
    deactivate Server
    
    activate ESP32
    ESP32->>ESP32: Điều khiển Servo Motor
    ESP32->>Server: Báo cửa đã mở
    deactivate ESP32
    
    Xe->>Server: Xe đỗ vào bãi
    
    activate Arduino
    Arduino->>Arduino: Đọc 6 cảm biến siêu âm
    Arduino->>Server: Gửi trạng thái 6 vị trí
    deactivate Arduino
    
    activate Server
    Server->>Server: Cập nhật trạng thái slot
    Server->>Server: Lưu vào parking_data.json
    deactivate Server
```

**Mô tả Sequence Diagram (Xe vào Bãi):**
1. **Quét RFID**: Xe đưa thẻ vào máy quét RFID trên ESP32
2. **Kiểm tra loại thẻ**: PC Server kiểm tra xem thẻ là Admin (miễn phí) hay User (tính tiền)
3. **Điều khiển cửa**: ESP32 nhận lệnh mở cửa, điều khiển Servo Motor
4. **Phát hiện chỗ trống**: Arduino đọc 6 cảm biến siêu âm, báo trạng thái 6 vị trí đỗ
5. **Lưu dữ liệu**: PC Server cập nhật trạng thái slot và lưu vào parking_data.json

#### Sequence Diagram (Xe ra Bãi)

```mermaid
sequenceDiagram
    participant Xe as Xe/Thẻ RFID
    participant ESP32
    participant Server as PC Dashboard Server
    participant Arduino as Arduino (Slots)

    Xe->>ESP32: Quét thẻ RFID (Cổng ra)
    activate ESP32
    ESP32->>Server: Gửi dữ liệu thẻ (Card ID)
    deactivate ESP32
    
    activate Server
    Server->>Server: Kiểm tra loại thẻ<br/>(Admin/User)
    Server->>Server: Tính thời gian đỗ
    alt Thẻ Admin
        Server->>Server: Ra miễn phí
    else Thẻ User
        Server->>Server: Tính tiền theo giờ<br/>Cập nhật ví
    end
    Server->>Server: Ghi nhận lịch sử ra
    Server->>ESP32: Mở cửa ra
    deactivate Server
    
    activate ESP32
    ESP32->>ESP32: Điều khiển Servo Motor (Cửa ra)
    ESP32->>Server: Báo cửa ra đã mở
    deactivate ESP32
    
    Xe->>Server: Xe rời khỏi bãi
    
    activate Arduino
    Arduino->>Arduino: Đọc 6 cảm biến siêu âm
    Arduino->>Server: Gửi trạng thái slot trống
    deactivate Arduino
    
    activate Server
    Server->>Server: Cập nhật slot thành trống
    Server->>Server: Lưu vào parking_data.json
    deactivate Server
```

**Mô tả Sequence Diagram (Xe ra Bãi):**
1. **Quét RFID ra**: Xe quét thẻ tại cổng ra
2. **Tính toán phí**: PC Server tính thời gian đỗ và tiền phí (nếu là User)
   - Admin ra miễn phí
   - User: Tính tiền/giờ, cập nhật ví
3. **Ghi nhận lịch sử**: PC Server lưu ghi nhận xe ra
4. **Mở cửa ra**: ESP32 mở Servo Motor cửa ra
5. **Phát hiện slot trống**: Arduino phát hiện xe rời khỏi, báo slot trống
6. **Cập nhật dữ liệu**: PC Server cập nhật trạng thái slot và lưu JSON

### **2. Luồng Hoạt Động**
- **Sơ đồ quy trình (Flowchart)**: Quy trình xe vào/ra, tính tiền
- **Sơ đồ trạng thái (State Diagram)**: Trạng thái các slot (trống/đã đỗ)

#### Flowchart - baidoxe.ino (ESP32 Gate Controller)

```mermaid
flowchart TD
    Start([ESP32 Khởi Động]) --> Setup["<b>setup()</b><br/>Khởi tạo LCD, SPI, RFID,<br/>Servo, Queue, Semaphore,<br/>3 Tasks"]
    
    Setup --> Loop["<b>loop()</b><br/>Vòng lặp chính"]
    
    Loop --> MaintainConn{"WiFi<br/>kết nối?"}
    MaintainConn -->|Không| ConnectWiFi["Kết nối WiFi:<br/>{WIFI_SSID}"]
    ConnectWiFi --> CheckSocket{"TCP Socket<br/>kết nối?"}
    MaintainConn -->|Có| CheckSocket
    
    CheckSocket -->|Không| ConnectSocket["Kết nối TCP Server<br/>{SERVER_IP}:5000"]
    ConnectSocket --> Ready["LCD: SYSTEM READY"]
    CheckSocket -->|Có| Ready
    
    Ready --> TaskListener["<b>TaskSocketListener</b><br/>Priority 3 - Core 0"]
    Ready --> TaskGateIN["<b>TaskGate-IN</b><br/>Priority 1 - Core 1"]
    Ready --> TaskGateOUT["<b>TaskGate-OUT</b><br/>Priority 1 - Core 1"]
    
    TaskListener --> ListenLoop["Lắng nghe Socket<br/>từ PC Server"]
    ListenLoop --> ParseJSON{"Dữ liệu<br/>hợp lệ?"}
    ParseJSON -->|Action=AUTH| ReceiveAuth["Nhận kết quả AUTH:<br/>SUCCESS/REJECT/<br/>WRONG_WAY"]
    ParseJSON -->|Action=OPEN| ManualOpen["Lệnh mở cửa<br/>thủ công"]
    ReceiveAuth --> PushQueue["Push vào Queue<br/>IN hoặc OUT"]
    ManualOpen --> PushQueue
    PushQueue --> ListenLoop
    
    TaskGateIN --> GateINLoop["Loop: Chờ lệnh"]
    TaskGateOUT --> GateOUTLoop["Loop: Chờ lệnh"]
    
    GateINLoop --> CheckQueueIN{"Có lệnh<br/>Queue?"}
    GateOUTLoop --> CheckQueueOUT{"Có lệnh<br/>Queue?"}
    
    CheckQueueIN -->|Manual| OpenIN["Mở Servo IN"]
    CheckQueueIN -->|Không| ScanRFDIN["Chờ quét RFID"]
    
    CheckQueueOUT -->|Manual| OpenOUT["Mở Servo OUT"]
    CheckQueueOUT -->|Không| ScanRFDOUT["Chờ quét RFID"]
    
    ScanRFDIN --> CardIN{"Phát hiện<br/>thẻ?"}
    ScanRFDOUT --> CardOUT{"Phát hiện<br/>thẻ?"}
    
    CardIN -->|Không| GateINLoop
    CardOUT -->|Không| GateOUTLoop
    
    CardIN -->|Có| SendCheckIN["Gửi CHECK<br/>tới PC Server"]
    CardOUT -->|Có| SendCheckOUT["Gửi CHECK<br/>tới PC Server"]
    
    SendCheckIN --> WaitAuthIN["Chờ phản hồi<br/>5s Timeout"]
    SendCheckOUT --> WaitAuthOUT["Chờ phản hồi<br/>5s Timeout"]
    
    WaitAuthIN --> CheckAuthIN{"Status<br/>là gì?"}
    WaitAuthOUT --> CheckAuthOUT{"Status<br/>là gì?"}
    
    CheckAuthIN -->|SUCCESS| OpenIN
    CheckAuthIN -->|WRONG_WAY| RejectIN["LCD:<br/>ALREADY IN/OUT"]
    CheckAuthIN -->|FAIL| RejectIN
    CheckAuthIN -->|TIMEOUT| TimeoutIN["LCD:<br/>PC TIMEOUT"]
    
    CheckAuthOUT -->|SUCCESS| OpenOUT
    CheckAuthOUT -->|WRONG_WAY| RejectOUT["LCD:<br/>ALREADY IN/OUT"]
    CheckAuthOUT -->|FAIL| RejectOUT
    CheckAuthOUT -->|TIMEOUT| TimeoutOUT["LCD:<br/>PC TIMEOUT"]
    
    RejectIN --> GateINLoop
    TimeoutIN --> GateINLoop
    RejectOUT --> GateOUTLoop
    TimeoutOUT --> GateOUTLoop
    
    OpenIN --> WaitVehicleIN["Mở cửa, chờ xe<br/>Ultrasonic Sensor"]
    OpenOUT --> WaitVehicleOUT["Mở cửa, chờ xe<br/>Ultrasonic Sensor"]
    
    WaitVehicleIN --> PassIN{"Xe<br/>vượt qua?"}
    WaitVehicleOUT --> PassOUT{"Xe<br/>vượt qua?"}
    
    PassIN -->|Có| SendDoneIN["Gửi DONE<br/>tới PC"]
    PassIN -->|Timeout| TimeoutServoIN["Sang vàng"]
    
    PassOUT -->|Có| SendDoneOUT["Gửi DONE<br/>tới PC"]
    PassOUT -->|Timeout| TimeoutServoOUT["Sang vàng"]
    
    SendDoneIN --> CloseIN["Đóng Servo IN"]
    TimeoutServoIN --> CloseIN
    
    SendDoneOUT --> CloseOUT["Đóng Servo OUT"]
    TimeoutServoOUT --> CloseOUT
    
    CloseIN --> ReadyIN["LCD: READY..."]
    CloseOUT --> ReadyOUT["LCD: READY..."]
    
    ReadyIN --> GateINLoop
    ReadyOUT --> GateOUTLoop
    
    style Setup fill:#e1f5ff
    style TaskListener fill:#fff3e0
    style TaskGateIN fill:#f3e5f5
    style TaskGateOUT fill:#f3e5f5
    style OpenIN fill:#c8e6c9
    style OpenOUT fill:#c8e6c9
```

**Mô tả:**
- **setup()**: Khởi tạo hardware (LCD I2C, SPI bus cho 2 RFID readers, 2 Servo motors, 4 Ultrasonic sensors)
- **loop()**: Duy trì kết nối WiFi và TCP socket
- **3 Tasks (FreeRTOS)**:
  - `TaskSocketListener` (Priority 3): Lắng nghe dữ liệu từ PC Server, parse JSON, push kết quả vào Queue
  - `TaskGate-IN` (Priority 1): Xử lý cửa vào - scan RFID, kiểm tra, mở cửa
  - `TaskGate-OUT` (Priority 1): Xử lý cửa ra - scan RFID, kiểm tra, mở cửa

**Quy trình chính (TaskGate)**:
1. Chờ lệnh từ Queue (manual open hoặc từ Socket)
2. Quét RFID (nếu không có lệnh manual)
3. Gửi CHECK request tới PC Server
4. Chờ phản hồi xác thực (5s timeout)
5. Nếu SUCCESS → Mở Servo, chờ xe vượt qua
6. Gửi DONE notification tới PC, đóng Servo
7. Quay lại bước 1

#### Flowchart - main.py (Entry Point)

```mermaid
flowchart TD
    Start([main.py Khởi Động]) --> InitBackend["Khởi tạo Backend<br/>- Load database JSON<br/>- Chuẩn bị 2 TCP servers<br/>Port 5000 GATE, 5001 SLOT"]
    
    InitBackend --> InitFront["Khởi tạo Frontend<br/>Tkinter GUI<br/>- Dashboard Tab<br/>- Slots Tab<br/>- History Tab<br/>- Settings Tab"]
    
    InitFront --> ConnectCallback["Kết nối Callbacks<br/>Backend -> Frontend<br/>- on_event<br/>- on_refresh<br/>- on_new_card<br/>- on_client_change"]
    
    ConnectCallback --> StartServer["backend.start_server()<br/>Khởi động 2 TCP servers<br/>trên 2 threads riêng"]
    
    StartServer --> MainLoop["root.mainloop()<br/>Chạy vòng lặp GUI"]
    
    MainLoop --> WaitEvent["Chờ sự kiện:<br/>- Người dùng click button<br/>- TCP message từ ESP32/Arduino<br/>- Callback từ Backend"]
    
    WaitEvent --> ProcessEvent{"Loại sự<br/>kiện?"}
    
    ProcessEvent -->|TCP Message| HandleMsg["Backend xử lý:<br/>CHECK / DONE / SLOT_UPDATE"]
    ProcessEvent -->|GUI Event| GUIEvent["Frontend xử lý:<br/>Thêm card, Export report,<br/>Manual gate control"]
    ProcessEvent -->|Callback| UpdateUI["Frontend cập nhật UI:<br/>Refresh table, Update status"]
    
    HandleMsg --> Trigger["Trigger callback<br/>on_event / on_refresh"]
    Trigger --> UpdateUI
    GUIEvent --> UpdateUI
    UpdateUI --> SaveDB["Backend save data<br/>vào parking_data.json"]
    SaveDB --> WaitEvent
    
    style Start fill:#e1f5ff
    style InitBackend fill:#fff3e0
    style InitFront fill:#f3e5f5
    style MainLoop fill:#c8e6c9
```

**Mô tả:**
- **Khởi tạo Backend**: Load dữ liệu, tạo 2 TCP servers (Port 5000 cho ESP32, 5001 cho Arduino)
- **Khởi tạo Frontend**: Tạo Tkinter GUI với 4 tabs (Dashboard, Slots, History, Settings)
- **Kết nối Callbacks**: Frontend lắng nghe sự kiện từ Backend
- **Vòng lặp chính**: Chờ sự kiện từ TCP, GUI, hoặc Backend callback → Xử lý → Cập nhật UI → Lưu dữ liệu

#### Flowchart - backend.py (Server TCP & Logic Xử Lý)

```mermaid
flowchart TD
    Start([Backend.py Khởi Động]) --> Init["ParkingBackend().__init__<br/>- Load/Create parking_data.json<br/>- Tạo 2 danh sách clients<br/>- Setup callbacks"]
    
    Init --> StartServer["start_server() - 2 Threads"]
    
    StartServer --> ServerGate["Thread 1: _server_loop<br/>Port 5000 - GATE Mode<br/>Lắng nghe ESP32"]
    StartServer --> ServerSlot["Thread 2: _server_loop<br/>Port 5001 - SLOT Mode<br/>Lắng nghe Arduino"]
    
    ServerGate --> ListenGate["server.listen 10<br/>Chờ kết nối"]
    ServerSlot --> ListenSlot["server.listen 10<br/>Chờ kết nối"]
    
    ListenGate --> AcceptGate{"Có ESP32<br/>kết nối?"}
    ListenSlot --> AcceptSlot{"Có Arduino<br/>kết nối?"}
    
    AcceptGate -->|Có| NewHandlerGate["Tạo thread handler<br/>cho ESP32 client"]
    AcceptSlot -->|Có| NewHandlerSlot["Tạo thread handler<br/>cho Arduino client"]
    
    NewHandlerGate --> HandlerLoop["_client_handler<br/>Lắng nghe dữ liệu"]
    NewHandlerSlot --> HandlerLoop2["_client_handler<br/>Lắng nghe dữ liệu"]
    
    HandlerLoop --> RecvMsg["Nhận từ ESP32<br/>JSON message"]
    HandlerLoop2 --> RecvMsgArduino["Nhận từ Arduino<br/>JSON message"]
    
    RecvMsg --> ParseAction["Phân tích action"]
    RecvMsgArduino --> ParseAction2["Phân tích action"]
    
    ParseAction --> IsCheck{"action<br/>== CHECK?"}
    ParseAction2 --> IsSlot{"action<br/>== SLOT_UPDATE?"}
    
    IsCheck -->|Có| CheckCard["CHECK - Kiểm tra thẻ"]
    IsCheck -->|Không| IsDone{"action<br/>== DONE?"}
    
    CheckCard --> CardExists{"Thẻ<br/>tồn tại?"}
    
    CardExists -->|Không| ReturnReject["Gửi phản hồi<br/>status: REJECT"]
    CardExists -->|Có| CheckType{"Loại<br/>thẻ?"}
    
    CheckType -->|Admin| AdminAuth["Admin card<br/>SUCCESS, fee=0"]
    CheckType -->|User| UserAuth["Check luồng:<br/>VÀO (not isInside)<br/>RA (isInside)"]
    
    UserAuth --> ValidFlow{"Luồng<br/>hợp lệ?"}
    ValidFlow -->|Không| WrongWay["Phản hồi:<br/>WRONG_WAY"]
    ValidFlow -->|Có| CalcFee["Tính phí<br/>nếu RA<br/>SUCCESS"]
    
    AdminAuth --> SendAuth["Gửi phản hồi AUTH<br/>về ESP32"]
    CalcFee --> SendAuth
    ReturnReject --> SendAuth
    WrongWay --> SendAuth
    
    IsDone -->|Có| DoneAction["DONE - Cập nhật trạng thái"]
    IsDone -->|Không| SkipDone["Skip"]
    
    DoneAction --> UpdateCard["Cập nhật card:<br/>isInside = true/false<br/>entry_time / exit_time"]
    UpdateCard --> SaveHistory["Lưu vào history:<br/>uid, event, fee, time"]
    SaveHistory --> TriggerEvent["Trigger callback<br/>on_event -> Frontend"]
    TriggerEvent --> SaveDB["Request save JSON"]
    
    IsSlot -->|Có| UpdateSlot["SLOT_UPDATE<br/>Cập nhật slot"]
    UpdateSlot --> SaveSlot["Lưu slot status<br/>VACANT / OCCUPIED"]
    SaveSlot --> RefreshUI["Trigger on_refresh<br/>-> Frontend update slot UI"]
    
    SendAuth --> HandlerLoop
    SkipDone --> HandlerLoop
    RefreshUI --> HandlerLoop2
    
    HandlerLoop -->|Client disconnect| RemoveClient["Xóa client khỏi list"]
    HandlerLoop2 -->|Client disconnect| RemoveClient2["Xóa client khỏi list"]
    
    RemoveClient --> ListenGate
    RemoveClient2 --> ListenSlot
    
    style Start fill:#e1f5ff
    style StartServer fill:#fff3e0
    style CheckCard fill:#c8e6c9
    style DoneAction fill:#fbcfe8
```

**Mô tả:**
- **2 Socket Servers**: Port 5000 (GATE) cho ESP32, Port 5001 (SLOT) cho Arduino
- **3 loại Messages**:
  - **CHECK**: Kiểm tra thẻ → Admin (SUCCESS/0đ) hoặc User (Check luồng VÀO/RA)
  - **DONE**: Cập nhật card status, tính phí (nếu RA), lưu history
  - **SLOT_UPDATE**: Cập nhật trạng thái 6 vị trí đỗ (VACANT/OCCUPIED)
- **Database**: Lưu tất cả vào parking_data.json

#### Flowchart - frontend.py (Tkinter GUI & User Interface)

```mermaid
flowchart TD
    Start([Frontend.py - ModernParkingGUI]) --> Init["__init__ setup<br/>- Color palette<br/>- Create widgets<br/>- Connect callbacks<br/>- Load history"]
    
    Init --> CreateUI["create_widgets()"]
    
    CreateUI --> Header["Header:<br/>Title + Status LED"]
    CreateUI --> Tabs["4 Tabs:<br/>1. Dashboard<br/>2. Slots<br/>3. History<br/>4. Settings"]
    
    Header --> DashTab["TAB 1: DASHBOARD<br/>- Show active cards<br/>- Duration, Fee<br/>- Pin/Unpin buttons"]
    Tabs --> DashTab
    
    DashTab --> SlotTab["TAB 2: SLOTS<br/>- 6 parking slots<br/>- Status: VACANT/OCCUPIED<br/>- Real-time update"]
    SlotTab --> HistTab["TAB 3: HISTORY<br/>- All entry/exit logs<br/>- Scrollable list<br/>- Time, UID, Event, Fee"]
    
    HistTab --> SettTab["TAB 4: SETTINGS<br/>- Add card button<br/>- Export report button<br/>- Manual gate control<br/>- Hourly rate setting"]
    
    SettTab --> MainLoop["update_ui_loop()<br/>Refresh UI mỗi 200ms"]
    
    MainLoop --> CheckCallbacks["Kiểm tra callback events<br/>từ Backend"]
    
    CheckCallbacks --> OnEvent["on_event<br/>uid, action, detail"]
    CheckCallbacks --> OnRefresh["on_refresh<br/>Cập nhật tất cả"]
    CheckCallbacks --> OnNewCard["on_new_card<br/>Thẻ mới"]
    CheckCallbacks --> OnClientChange["on_client_change<br/>Status LED"]
    
    OnEvent --> AddLog["Thêm vào event log<br/>Hiển thị động"]
    AddLog --> UpdateDash["Cập nhật Dashboard:<br/>Thêm/xóa card row"]
    
    OnRefresh --> RefreshAll["Refresh table<br/>Tính thời gian realtime<br/>Update slot status"]
    
    OnNewCard --> PromptAdd["Pop-up: Add card<br/>Nhập loại (Admin/User)"]
    PromptAdd --> SaveCard["backend.add_card()<br/>Lưu vào database"]
    
    OnClientChange --> UpdateLED["Cập nhật Status LED<br/>○ Waiting... <br/> Connected  (Red/Green)"]
    
    UpdateDash --> UserClick["Chờ user interaction"]
    RefreshAll --> UserClick
    UpdateLED --> UserClick
    
    UserClick --> ClickType{"Click<br/>type?"}
    
    ClickType -->|Pin Card| PinCard["Highlight card<br/>Pin = True"]
    ClickType -->|Remove Card| RemoveCard["backend.remove_card(uid)<br/>Xóa khỏi database"]
    ClickType -->|Add Card| AddCardForm["Dialog: Add new card<br/>Input UID"]
    ClickType -->|Change Type| ChangeType["Change: Admin ↔ User"]
    
    ClickType -->|Export Report| ExportReport["filedialog save CSV"]
    ExportReport --> GenReport["Generate report<br/>Sum fee, List all logs<br/>Write to CSV"]
    ExportReport --> ClearOpt["Option: Clear history?"]
    
    ClickType -->|Manual Open| ManualGate["Send OPEN command<br/>via Backend<br/>to ESP32"]
    ClickType -->|Hourly Rate| SettingForm["Dialog: Set rate<br/>default 10000đ/hour"]
    
    PinCard --> MainLoop
    RemoveCard --> MainLoop
    AddCardForm --> MainLoop
    ChangeType --> MainLoop
    GenReport --> MainLoop
    ClearOpt --> MainLoop
    ManualGate --> MainLoop
    SettingForm --> MainLoop
    
    style Start fill:#e1f5ff
    style CreateUI fill:#fff3e0
    style MainLoop fill:#c8e6c9
    style ClickType fill:#fbcfe8
```

**Mô tả:**
- **4 Tabs**: Dashboard (active cars), Slots (6 vị trí), History (logs), Settings (config)
- **UI Loop**: Refresh mỗi 200ms, realtime update thời gian & phí
- **Callbacks từ Backend**:
  - `on_event`: Thêm log động
  - `on_refresh`: Cập nhật tất cả
  - `on_new_card`: Pop-up thêm thẻ mới
  - `on_client_change`: Cập nhật Status LED
- **User Actions**: Pin/remove cards, export reports, manual gate control, set hourly rate

### **4. Cơ Sở Hạ Tầng - Network Diagram**

#### Network Topology - Sơ đồ Kết nối Mạng

```mermaid
graph TB
    subgraph WiFi["📡 WiFi Network<br/>"]
        PC["💻 PC WiFi Hotspot<br/>IP: {GATEWAY_IP}<br/>Gateway: {GATEWAY_IP}<br/>Subnet: 255.255.255.0"]
        
        ESP32["🔧 ESP32 Client<br/>IP: DHCP<br/>Port: 5000<br/>(GATE Controller)"]
        
        Arduino["🎛️ Arduino Uno R4<br/>IP: DHCP<br/>Port: 5001<br/>(SLOT Detector)"]
    end
    
    subgraph Services["🖥️ PC Services"]
        Server["TCP Servers<br/>- Port 5000: GATE Server<br/>- Port 5001: SLOT Server"]
        Frontend["Tkinter GUI<br/>Dashboard + Settings"]
        Backend["Python Backend<br/>Logic & Database"]
        DB[" parking_data.json<br/>Local Storage"]
    end
    
    subgraph External["🌐 External (Optional)"]
        PaymentGW["Payment Gateway<br/>(Internet Connection)"]
    end
    
    PC -->|WiFi Connection| ESP32
    PC -->|WiFi Connection| Arduino
    ESP32 -->|TCP Port 5000| Server
    Arduino -->|TCP Port 5001| Server
    Server --> Backend
    Backend --> Frontend
    Backend --> DB
    PC -.->|Optional| PaymentGW
    
    style PC fill:#e1f5ff,stroke:#01579b,stroke-width:3px
    style ESP32 fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style Arduino fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    style Server fill:#c8e6c9,stroke:#1b5e20,stroke-width:2px
    style Backend fill:#fbcfe8,stroke:#880e4f,stroke-width:2px
    style Frontend fill:#e0f2f1,stroke:#004d40,stroke-width:2px
    style DB fill:#fce4ec,stroke:#b71c1c,stroke-width:2px
```

**Mô tả Network:**

**WiFi Layer:**
- **SSID**: {NETWORK_SSID} (2.4GHz 802.11n)
- **Mode**: PC tạo WiFi Hotspot
- **Gateway**: {GATEWAY_IP} (PC)
- **Subnet Mask**: 255.255.255.0
- **DHCP**: Cấp IP tự động cho ESP32 & Arduino

**Thiết bị kết nối:**
- **PC WiFi Hotspot** (Trung tâm):
  - IP: {GATEWAY_IP}
  - Gateway & Server chính
  - Lắng nghe Port 5000 & 5001
  
- **ESP32 (GATE Controller)**:
  - IP: Nhận từ DHCP
  - Kết nối TCP tới PC:5000
  - Gửi: RFID data, sensor data
  - Nhận: Door control commands
  
- **Arduino Uno R4 (SLOT Detector)**:
  - IP: Nhận từ DHCP
  - Kết nối TCP tới PC:5001
  - Gửi: 6 slot occupancy status
  - Nhận: Control commands (nếu có)

**TCP Ports:**
- **Port 5000 (GATE Server)**: Xử lý ESP32 signals
  - CHECK: Thẻ kiểm tra
  - DONE: Cửa đã đóng
  - Status: Trạng thái
  
- **Port 5001 (SLOT Server)**: Xử lý Arduino signals
  - SLOT_UPDATE: Cập nhật 6 vị trí
  - Dữ liệu: VACANT / OCCUPIED

**PC Local Services:**
- **Backend (Python)**: Xử lý logic, lưu JSON
- **Frontend (Tkinter)**: Giao diện Dashboard
- **Database**: parking_data.json

**Optional:**
- Payment Gateway integration (Internet connection)

**Lợi ích hệ thống:**
✅ Locally hosted → No internet required  
✅ DHCP automatic IP → Plug & play  
✅ Dual TCP servers → Separate GATE & SLOT handling  
✅ JSON local storage → Fast access & backup

