import socket
import ssl
import json
import threading
import time
import os
import queue
import logging
from datetime import datetime, timedelta
import math

# --- LOGGING SETUP ---
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(f"logs/parking_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Backend")

# --- CONFIGURATION (Load from .env) ---
def load_env(file_path='.env'):
    env_vars = {}
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value
    return env_vars

env = load_env()
DB_FILE = 'parking_data.json'
HOST = '0.0.0.0'
PORT_GATE = int(env.get('PORT_GATE', 5000))
PORT_SLOT = int(env.get('PORT_SLOT', 5001))
DEFAULT_RATE = int(env.get('HOURLY_RATE', 10000))
AUTH_TOKEN = env.get('AUTH_TOKEN', 'SET_ME_IN_ENV')

class ParkingStore:
    def __init__(self):
        self.data = self.load_db()
        # Cập nhật rate từ .env nếu chưa có trong DB
        if "config" not in self.data:
            self.data["config"] = {"hourly_rate": DEFAULT_RATE}
        elif "hourly_rate" not in self.data["config"]:
            self.data["config"]["hourly_rate"] = DEFAULT_RATE
        
        self.lock = threading.Lock()
        self.save_queue = queue.Queue()
        threading.Thread(target=self._save_worker, daemon=True).start()

    def load_db(self):
        res = {
            "config": {"hourly_rate": 10000},
            "cards": {},
            "slots": {},
            "history": []
        }
        paths = [DB_FILE, 'parking_data.json']
        for p in paths:
            if os.path.exists(p):
                try:
                    with open(p, 'r', encoding='utf-8') as f:
                        loaded = json.load(f)
                        # Ensure all keys exist
                        for k in res:
                            if k not in loaded: loaded[k] = res[k]
                        return loaded
                except: pass
        return res

    def _save_worker(self):
        while True:
            self.save_queue.get()
            # Debounce: wait a bit and clear pending saves
            time.sleep(1.0) 
            while not self.save_queue.empty():
                try: self.save_queue.get_nowait()
                except: break
                
            try:
                with self.lock:
                    # Deep copy data to avoid mutation during save
                    data_to_save = json.loads(json.dumps(self.data))
                
                with open(DB_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, indent=4, ensure_ascii=False)
                logger.info("Database saved successfully.")
            except Exception as e:
                logger.error(f"Error saving database: {e}")

    def request_save(self):
        self.save_queue.put(True)

    def calculate_fee(self, uid, exit_time_dt):
        card = self.data["cards"].get(uid)
        if not card or card.get("type") == "admin":
            return 0, 0
            
        entry_time_str = card.get("entry_time")
        if not entry_time_str:
            return 0, 0
            
        entry_time_dt = datetime.strptime(entry_time_str, "%Y-%m-%d %H:%M:%S")
        duration = exit_time_dt - entry_time_dt
        hours = math.ceil(duration.total_seconds() / 3600)
        fee = hours * self.data["config"]["hourly_rate"]
        return max(0, fee), duration.total_seconds()

class ParkingBackend:
    def __init__(self):
        self.store = ParkingStore()
        self.gate_clients = []
        self.slot_clients = []
        self.callbacks = {
            "on_event": None,        # lambda uid, event, detail
            "on_refresh": None,      # lambda
            "on_new_card": None,     # lambda uid
            "on_client_change": None # lambda count
        }
        logger.info("Backend initialized.")

    def set_callback(self, event_name, func):
        if event_name in self.callbacks:
            self.callbacks[event_name] = func

    def _trigger(self, event_name, *args):
        if self.callbacks[event_name]:
            try:
                self.callbacks[event_name](*args)
            except Exception as e:
                import traceback
                logger.error(f"Callback Error ({event_name}): {e}\n{traceback.format_exc()}")

    def start_server(self):
        # GATE (ESP32) dùng SSL để bảo mật mã thẻ và lệnh mở cổng
        threading.Thread(target=self._server_loop, args=(PORT_GATE, "GATE", True), daemon=True).start()
        # SLOT (Uno R4) dùng TCP thường để giảm tải và không cần sửa code Uno
        threading.Thread(target=self._server_loop, args=(PORT_SLOT, "SLOT", False), daemon=True).start()

    def _server_loop(self, port, mode, use_ssl=True):
        # --- SSL SETUP ---
        context = None
        if use_ssl:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            try:
                context.load_cert_chain(certfile="server.crt", keyfile="server.key")
                logger.info(f"{mode} SSL Certificate loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load SSL certificates for {mode}: {e}. Running WITHOUT SSL!")
                context = None

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, port))
        server.listen(10)
        
        if context:
            logger.info(f"{mode} SSL Server listening on {HOST}:{port}")
        else:
            logger.info(f"{mode} Standard Server listening on {HOST}:{port}")
        
        while True:
            conn, addr = server.accept()
            
            # Wrap connection with SSL if context was loaded
            if context:
                try:
                    conn = context.wrap_socket(conn, server_side=True)
                except Exception as e:
                    logger.warning(f"SSL Handshake failed with {addr}: {e}")
                    conn.close()
                    continue

            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            client_list = self.gate_clients if mode == "GATE" else self.slot_clients
            with self.store.lock:
                client_list.append(conn)
            
            self._trigger("on_client_change", len(self.gate_clients) + len(self.slot_clients)) 
            logger.info(f"New {mode} connection from {addr}")
            threading.Thread(target=self._client_handler, args=(conn, addr, mode), daemon=True).start()

    def _client_handler(self, conn, addr, mode):
        buffer = ""
        try:
            while True:
                data = conn.recv(1024).decode('utf-8')
                if not data: break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        self.handle_msg(conn, line.strip(), mode)
        except Exception as e:
            logger.warning(f"{mode} Client {addr} disconnected: {e}")
        finally:
            client_list = self.gate_clients if mode == "GATE" else self.slot_clients
            with self.store.lock:
                if conn in client_list:
                    client_list.remove(conn)
            self._trigger("on_client_change", len(self.gate_clients) + len(self.slot_clients))
            conn.close()

    def handle_msg(self, conn, line, mode):
        try:
            req = json.loads(line)
            
            # --- AUTHENTICATION CHECK (Chỉ áp dụng cho GATE) ---
            if mode == "GATE":
                client_token = req.get("auth")
                if client_token != AUTH_TOKEN:
                    logger.warning(f"Unauthorized access attempt from {conn.getpeername()}. Invalid Token.")
                    conn.close()
                    return

            action = req.get("action")
            uid = req.get("uid")
            gate_raw = req.get("gate", "")
            gate = "IN" if "IN" in gate_raw else "OUT"

            if action == "CHECK":
                res = None
                is_new = False
                with self.store.lock:
                    if uid not in self.store.data["cards"]:
                        res = {"gate": gate, "action": "AUTH", "status": "REJECT"}
                        is_new = True
                    else:
                        card = self.store.data["cards"][uid]
                        is_in = "IN" in gate_raw
                        is_admin = card.get("type") == "admin"
                        
                        # Thẻ ADMIN được ưu tiên: Luôn SUCCESS và phí 0đ, không kiểm tra isInside
                        if is_admin:
                            res = {"gate": gate, "action": "AUTH", "status": "SUCCESS", "fee": 0}
                        # Thẻ thường: Kiểm tra đúng luồng VÀO/RA
                        elif (is_in and not card["isInside"]) or (not is_in and card["isInside"]):
                            fee = 0
                            if not is_in:
                                fee, _ = self.store.calculate_fee(uid, datetime.now())
                            res = {"gate": gate, "action": "AUTH", "status": "SUCCESS", "fee": fee}
                        else:
                            res = {"gate": gate, "action": "AUTH", "status": "WRONG_WAY"}
                
                if is_new:
                    self._trigger("on_new_card", uid) # Ở ngoài lock
                
                if res:
                    conn.sendall((json.dumps(res) + "\n").encode())
                    logger.info(f"Gate {gate} CHECK response sent for UID {uid}: {res['status']}")

            elif action == "DONE":
                event_data = None
                with self.store.lock:
                    if uid in self.store.data["cards"]:
                        card = self.store.data["cards"][uid]
                        is_in = "IN" in gate_raw
                        now = datetime.now()
                        card["isInside"] = is_in
                        if is_in: 
                            card["entry_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
                            event_data = (uid, "VÀO", "Xe đã qua cổng")
                        else:
                            fee, _ = self.store.calculate_fee(uid, now)
                            card["exit_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
                            event_data = (uid, "RA", f"Phí: {fee:,}đ")
                        
                        # Save to history for reporting
                        self.store.data["history"].append({
                            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
                            "uid": uid,
                            "event": event_data[1],
                            "detail": event_data[2],
                            "fee": fee if not is_in else 0
                        })
                        self.store.request_save()
                
                if event_data:
                    self._trigger("on_event", *event_data)
                    self._trigger("on_refresh")
                    logger.info(f"Gate {gate} process DONE for UID {uid}")

            elif action == "SLOT_UPDATE":
                slot_id = req.get("slot", 1)
                status = req.get("status", "VACANT")
                with self.store.lock:
                    if "slots" not in self.store.data:
                        self.store.data["slots"] = {}
                    self.store.data["slots"][str(slot_id)] = status
                    self.store.request_save()
                
                self._trigger("on_refresh")
                self._trigger("on_event", "PARKING", f"SLOT {slot_id}", status)
                logger.info(f"Slot {slot_id} updated to {status}")

        except Exception as e:
            logger.error(f"Handler Error: {e}")

    def manual_open(self, gate):
        msg = (json.dumps({"gate": gate, "action": "OPEN"}) + "\n").encode('utf-8')
        dead = []
        with self.store.lock:
            # Chỉ lặp qua bản sao để tránh lỗi khi remove trong lúc lặp
            current_clients = list(self.gate_clients)
            
            for c in current_clients:
                try:
                    c.sendall(msg)
                except (socket.error, ssl.SSLError) as e:
                    logger.warning(f"Failed to send manual open to a client: {e}")
                    dead.append(c)
            
            # Dọn dẹp các kết nối chết
            for d in dead:
                if d in self.gate_clients:
                    try: 
                        d.close()
                        self.gate_clients.remove(d)
                    except: pass
        
        count = len(self.gate_clients) + len(self.slot_clients)
        self._trigger("on_client_change", count)
        self._trigger("on_event", "SYSTEM", f"MANUAL OPEN {gate}", f"Sent to {len(current_clients) - len(dead)} clients")
        logger.info(f"Manual open command handled for gate {gate}")
