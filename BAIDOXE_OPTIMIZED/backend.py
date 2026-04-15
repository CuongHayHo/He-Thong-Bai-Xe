import socket
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

# --- CONFIGURATION ---
DB_FILE = 'parking_data.json'
HOST = '0.0.0.0'
PORT = 5000

class ParkingStore:
    def __init__(self):
        self.data = self.load_db()
        self.lock = threading.Lock()
        self.save_queue = queue.Queue()
        threading.Thread(target=self._save_worker, daemon=True).start()

    def load_db(self):
        paths = [DB_FILE, 'parking_data.json']
        for p in paths:
            if os.path.exists(p):
                try:
                    with open(p, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except: pass
        return {
            "config": {"hourly_rate": 10000},
            "cards": {},
            "history": []
        }

    def _save_worker(self):
        while True:
            self.save_queue.get()
            try:
                with open(DB_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, indent=4, ensure_ascii=False)
                logger.info("Database saved successfully.")
            except Exception as e:
                logger.error(f"Error saving database: {e}")
            finally:
                self.save_queue.task_done()

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
        self.active_clients = []
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
        threading.Thread(target=self._server_loop, daemon=True).start()

    def _server_loop(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(10)
        logger.info(f"Server listening on {HOST}:{PORT}")
        
        while True:
            conn, addr = server.accept()
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            count = 0
            with self.store.lock:
                self.active_clients.append(conn)
                count = len(self.active_clients)
            
            self._trigger("on_client_change", count) # Ở ngoài lock
            logger.info(f"New connection from {addr}")
            threading.Thread(target=self._client_handler, args=(conn, addr), daemon=True).start()

    def _client_handler(self, conn, addr):
        buffer = ""
        try:
            while True:
                data = conn.recv(1024).decode('utf-8')
                if not data: break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        self.handle_msg(conn, line.strip())
        except Exception as e:
            logger.warning(f"Client {addr} disconnected or error: {e}")
        finally:
            count = 0
            with self.store.lock:
                if conn in self.active_clients:
                    self.active_clients.remove(conn)
                    count = len(self.active_clients)
            self._trigger("on_client_change", count) # Ở ngoài lock
            conn.close()

    def handle_msg(self, conn, line):
        try:
            req = json.loads(line)
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
                        
                        self.store.request_save()
                
                if event_data:
                    self._trigger("on_event", *event_data)
                    self._trigger("on_refresh")
                    logger.info(f"Gate {gate} process DONE for UID {uid}")

        except Exception as e:
            logger.error(f"Handler Error: {e}")

    def manual_open(self, gate):
        msg = json.dumps({"gate": gate, "action": "OPEN"}) + "\n"
        dead = []
        with self.store.lock:
            for c in self.active_clients:
                try:
                    c.sendall(msg.encode('utf-8'))
                except: dead.append(c)
            for d in dead:
                if d in self.active_clients: self.active_clients.remove(d)
                self._trigger("on_client_change", len(self.active_clients))
        
        self._trigger("on_event", "SYSTEM", f"MANUAL OPEN {gate}", "Gửi từ phần mềm")
        logger.info(f"Manual open command sent for gate {gate}")
