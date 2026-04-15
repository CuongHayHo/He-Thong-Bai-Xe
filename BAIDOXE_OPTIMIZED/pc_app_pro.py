import socket
import json
import threading
import time
import os
import queue
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import math

# --- CONFIGURATION ---
DB_FILE = '../parking_data.json' # Vẫn sử dụng chung database với bản cũ
HOST = '0.0.0.0'
PORT = 5000

# --- DATA MANAGEMENT ---
class ParkingStore:
    def __init__(self):
        self.data = self.load_db()
        self.lock = threading.Lock()
        self.save_queue = queue.Queue()
        # Thread ghi file chạy ngầm để không làm đứng Server
        threading.Thread(target=self._save_worker, daemon=True).start()

    def load_db(self):
        # Kiểm tra file ở cả thư mục hiện tại và thư mục cha
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
            # Đợi yêu cầu ghi từ queue
            self.save_queue.get()
            try:
                with open(DB_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"Lỗi ghi DB: {e}")
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

store = ParkingStore()

# --- MODERN UI DESIGN ---
class ModernParkingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PREMIUM SMART PARKING SYSTEM v3.0")
        self.root.geometry("1100x750")
        
        # Color Palette (Premium Dark/Modern)
        self.colors = {
            "bg": "#1e1e2e",      # Dark Blue-Grey
            "surface": "#2d2d44", # Slightly lighter surface
            "accent": "#7289da",  # Discord Purple-Blue
            "success": "#2ecc71",
            "danger": "#e74c3c",
            "text": "#ffffff",
            "text_dim": "#a9b1d6"
        }
        
        self.root.configure(bg=self.colors["bg"])
        self.active_clients = []
        self.setup_styles()
        self.create_widgets()
        self.update_ui_loop()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Customizing Treeview
        style.configure("Treeview", 
                        background=self.colors["surface"],
                        foreground=self.colors["text"],
                        fieldbackground=self.colors["surface"],
                        rowheight=35,
                        font=('Segoe UI', 10))
        style.map("Treeview", background=[('selected', self.colors["accent"])])
        
        style.configure("Treeview.Heading", 
                        background=self.colors["bg"], 
                        foreground=self.colors["text"], 
                        font=('Segoe UI', 10, 'bold'))

        style.configure("TNotebook", background=self.colors["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=self.colors["surface"], foreground=self.colors["text_dim"], padding=[20, 5])
        style.map("TNotebook.Tab", background=[("selected", self.colors["accent"])], foreground=[("selected", "#ffffff")])

        style.configure("TFrame", background=self.colors["bg"])

    def create_widgets(self):
        # Header
        header = tk.Frame(self.root, bg=self.colors["surface"], height=60)
        header.pack(fill='x', side='top')
        header.pack_propagate(False)
        
        tk.Label(header, text="PARKING CONTROL CENTER", fg=self.colors["success"], bg=self.colors["surface"], 
                 font=('Segoe UI', 16, 'bold')).pack(side='left', padx=20)
        
        self.lbl_status = tk.Label(header, text="● SERVER READY", fg=self.colors["text_dim"], bg=self.colors["surface"],
                                  font=('Segoe UI', 10, 'bold'))
        self.lbl_status.pack(side='right', padx=20)

        # Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=20, pady=10)

        self.tab_dashboard = ttk.Frame(self.notebook)
        self.tab_history = ttk.Frame(self.notebook)
        self.tab_settings = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_dashboard, text=" TRẠNG THÁI BÃI XE ")
        self.notebook.add(self.tab_history, text=" NHẬT KÝ HỆ THỐNG ")
        self.notebook.add(self.tab_settings, text=" CÀI ĐẶT ")

        self.setup_dashboard()
        self.setup_history()
        self.setup_settings()

    def setup_dashboard(self):
        # Top Controls
        ctrl_frame = tk.Frame(self.tab_dashboard, bg=self.colors["bg"])
        ctrl_frame.pack(fill='x', pady=10)
        
        btn_in = tk.Button(ctrl_frame, text="MỞ CỔNG VÀO (IN)", command=lambda: self.manual_open("IN"),
                          bg=self.colors["success"], fg="#ffffff", font=('Segoe UI', 9, 'bold'), border=0, padx=15, pady=5)
        btn_in.pack(side='left', padx=5)
        
        btn_out = tk.Button(ctrl_frame, text="MỞ CỔNG RA (OUT)", command=lambda: self.manual_open("OUT"),
                           bg=self.colors["accent"], fg="#ffffff", font=('Segoe UI', 9, 'bold'), border=0, padx=15, pady=5)
        btn_out.pack(side='left', padx=5)

        # Main Table
        cols = ("STT", "UID", "Tên Chủ Thẻ", "Giờ Vào", "Thời Gian Đỗ", "Loại", "Phí Tạm Tính")
        self.tree = ttk.Treeview(self.tab_dashboard, columns=cols, show='headings')
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor='center', width=120)
        self.tree.column("STT", width=40)
        self.tree.pack(fill='both', expand=True)

        # Context Menu
        self.ctx = tk.Menu(self.root, tearoff=0, bg=self.colors["surface"], fg=self.colors["text"], borderwidth=0)
        self.ctx.add_command(label="✏️ Đổi tên chủ thẻ", command=self.rename_card)
        self.ctx.add_command(label="⭐ Phân quyền ADMIN", command=lambda: self.set_card_type("admin"))
        self.ctx.add_command(label="👤 Phân quyền REGULAR", command=lambda: self.set_card_type("regular"))
        self.ctx.add_separator()
        self.ctx.add_command(label="❌ Xóa khỏi hệ thống", command=self.delete_card)
        self.tree.bind("<Button-3>", lambda e: self.ctx.post(e.x_root, e.y_root) if self.tree.identify_row(e.y) else None)

    def setup_history(self):
        # Real-time Log
        self.log_txt = tk.Text(self.tab_history, height=10, bg="#000000", fg="#00ff00", font=('Consolas', 9))
        self.log_txt.pack(fill='x', pady=5)
        
        # History Table
        cols = ("Thời Gian", "UID", "Sự Kiện", "Chi Tiết")
        self.htree = ttk.Treeview(self.tab_history, columns=cols, show='headings')
        for col in cols:
            self.htree.heading(col, text=col)
            self.htree.column(col, anchor='center')
        self.htree.pack(fill='both', expand=True)

    def setup_settings(self):
        frame = tk.Frame(self.tab_settings, bg=self.colors["bg"])
        frame.pack(expand=True)
        tk.Label(frame, text="ĐƠN GIÁ (VND/GIỜ):", fg=self.colors["text_dim"], bg=self.colors["bg"], font=('Segoe UI', 12, 'bold')).grid(row=0, column=0, pady=20)
        self.ent_rate = tk.Entry(frame, font=('Segoe UI', 14), bg=self.colors["surface"], fg=self.colors["text"], border=0)
        self.ent_rate.insert(0, str(store.data["config"]["hourly_rate"]))
        self.ent_rate.grid(row=0, column=1, padx=20)
        tk.Button(frame, text="LƯU THIẾT LẬP", command=self.save_settings, bg=self.colors["success"], fg="#ffffff", padx=30, pady=10, border=0).grid(row=1, column=0, columnspan=2, pady=30)

    # --- ACTIONS ---
    def manual_open(self, gate):
        if not self.active_clients:
            return
        msg = json.dumps({"gate": gate, "action": "OPEN"}) + "\n"
        self._broadcast(msg)
        self.log_event("SYSTEM", f"MANUAL OPEN {gate}", "Gửi từ phần mềm")

    def rename_card(self):
        sel = self.tree.selection()
        if not sel: return
        uid = self.tree.item(sel[0])['values'][1]
        name = simpledialog.askstring("Rename", "Nhập tên mới:", initialvalue=self.tree.item(sel[0])['values'][2])
        if name:
            with store.lock:
                store.data["cards"][uid]["name"] = name
                store.request_save()
            self.refresh_table()

    def set_card_type(self, t):
        sel = self.tree.selection()
        if not sel: return
        uid = self.tree.item(sel[0])['values'][1]
        with store.lock:
            store.data["cards"][uid]["type"] = t
            store.request_save()
        self.refresh_table()

    def delete_card(self):
        sel = self.tree.selection()
        if not sel: return
        uid = self.tree.item(sel[0])['values'][1]
        if messagebox.askyesno("Confirm", f"Xóa thẻ {uid}?"):
            with store.lock:
                if uid in store.data["cards"]:
                    del store.data["cards"][uid]
                    store.request_save()
            self.refresh_table()

    def save_settings(self):
        try:
            store.data["config"]["hourly_rate"] = int(self.ent_rate.get())
            store.request_save()
            messagebox.showinfo("OK", "Đã cập nhật giá mới")
        except: messagebox.showerror("Error", "Số không hợp lệ")

    def _broadcast(self, msg):
        dead = []
        for c in self.active_clients:
            try:
                c.sendall(msg.encode('utf-8'))
            except: dead.append(c)
        for d in dead:
            if d in self.active_clients: self.active_clients.remove(d)

    def log_event(self, uid, event, detail):
        t = datetime.now().strftime("%H:%M:%S")
        self.htree.insert("", 0, values=(t, uid, event, detail))
        self.log_txt.insert('1.0', f"[{t}] {event} - {uid}: {detail}\n")

    def refresh_table(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        with store.lock:
            i = 1
            now = datetime.now()
            for uid, c in store.data["cards"].items():
                is_in = c.get("isInside", False)
                entry = c.get("entry_time", "-")
                dur = "-"
                fee = "0đ"
                if is_in and entry != "-":
                    try:
                        edt = datetime.strptime(entry, "%Y-%m-%d %H:%M:%S")
                        diff = now - edt
                        dur = str(timedelta(seconds=int(diff.total_seconds())))
                        if c.get("type") == "admin": fee = "ADMIN"
                        else:
                            f, _ = store.calculate_fee(uid, now)
                            fee = f"{f:,}đ"
                    except: pass
                self.tree.insert("", "end", values=(i, uid, c.get("name", ""), entry, dur, c.get("type", "regular").upper(), fee))
                i += 1

    def update_ui_loop(self):
        self.refresh_table()
        count = len(self.active_clients)
        if count > 0:
            self.lbl_status.config(text=f"● CONNECTED: {count} DEVICES", fg=self.colors["success"])
        else:
            self.lbl_status.config(text="○ WAITING FOR ESP32...", fg=self.colors["text_dim"])
        self.root.after(3000, self.update_ui_loop)

# --- SPEED OPTIMIZED SERVER ---
class FastParkingServer:
    def __init__(self, app):
        self.app = app

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Tắt Nagle's Algorithm trên Socket Server
        server.bind((HOST, PORT))
        server.listen(10)
        print(f"[*] Fast Server Listening on {HOST}:{PORT}")
        
        while True:
            conn, addr = server.accept()
            # BẬT TCP_NODELAY: Gửi dữ liệu ngay lập tức, cực kỳ quan trọng cho điều khiển rào chắn
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            with store.lock:
                self.app.active_clients.append(conn)
            threading.Thread(target=self.client_handler, args=(conn, addr), daemon=True).start()

    def client_handler(self, conn, addr):
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
        except: pass
        finally:
            with store.lock:
                if conn in self.app.active_clients: self.app.active_clients.remove(conn)
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
                with store.lock:
                    if uid not in store.data["cards"]:
                        res = {"gate": gate, "action": "AUTH", "status": "REJECT"}
                        self.app.root.after(0, lambda u=uid: self.app.ask_add_card(u))
                    else:
                        card = store.data["cards"][uid]
                        is_in = "IN" in gate_raw
                        if (is_in and not card["isInside"]) or (not is_in and card["isInside"]):
                            fee = 0
                            if not is_in:
                                fee, _ = store.calculate_fee(uid, datetime.now())
                            res = {"gate": gate, "action": "AUTH", "status": "SUCCESS", "fee": fee}
                        else:
                            res = {"gate": gate, "action": "AUTH", "status": "WRONG_WAY"}
                
                # Gửi dữ liệu SAU KHI nhả Lock
                if res:
                    conn.sendall((json.dumps(res) + "\n").encode())

            elif action == "DONE":
                with store.lock:
                    if uid in store.data["cards"]:
                        card = store.data["cards"][uid]
                        is_in = "IN" in gate_raw
                        now = datetime.now()
                        card["isInside"] = is_in
                        if is_in: 
                            card["entry_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
                            self.app.root.after(0, lambda u=uid: self.app.log_event(u, "VÀO", "Xe đã qua cổng"))
                        else:
                            fee, _ = store.calculate_fee(uid, now)
                            card["exit_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
                            self.app.root.after(0, lambda u=uid, f=fee: self.app.log_event(u, "RA", f"Phí: {f:,}đ"))
                        
                        store.request_save()
                        self.app.root.after(0, self.app.refresh_table)

        except Exception as e: print(f"Handler Error: {e}")

    def ask_add_card(self, uid):
        if messagebox.askyesno("Thẻ lạ", f"Thêm thẻ mới {uid}?"):
            with store.lock:
                store.data["cards"][uid] = {"name": f"User_{uid[-4:]}", "type": "regular", "isInside": False, "entry_time": None}
                store.request_save()
            self.app.log_event(uid, "REG", "Đã cấp quyền")
            self.app.refresh_table()

if __name__ == "__main__":
    root = tk.Tk()
    app = ModernParkingApp(root)
    server = FastParkingServer(app)
    threading.Thread(target=server.start, daemon=True).start()
    root.mainloop()
