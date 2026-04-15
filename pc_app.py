import socket
import json
import threading
import time
import os
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import math

# --- CONFIGURATION ---
DB_FILE = 'parking_data.json'
HOST = '0.0.0.0'
PORT = 5000

# --- DATA MANAGEMENT ---
class ParkingStore:
    def __init__(self):
        self.data = self.load_db()
        self.lock = threading.Lock()

    def load_db(self):
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "config": {"hourly_rate": 10000},
            "cards": {},
            "history": []
        }

    def save_db(self):
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def calculate_fee(self, uid, exit_time_dt):
        card = self.data["cards"].get(uid)
        if not card or card.get("type") == "admin":
            return 0, 0
            
        entry_time_str = card.get("entry_time")
        if not entry_time_str:
            return 0, 0
            
        entry_time_dt = datetime.strptime(entry_time_str, "%Y-%m-%d %H:%M:%S")
        duration = exit_time_dt - entry_time_dt
        
        # Calculate hours (rounded up)
        hours = math.ceil(duration.total_seconds() / 3600)
        fee = hours * self.data["config"]["hourly_rate"]
        return max(0, fee), duration.total_seconds()

store = ParkingStore()

# --- GUI APPLICATION ---
class ParkingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PARKING CONTROL CENTER - v2.0")
        self.root.geometry("1150x750")
        self.root.configure(bg="#f4f4f4")

        # Connection management
        self.server = None
        self.active_clients = []

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("Treeview", rowheight=30, font=('Arial', 10))
        self.style.configure("TButton", font=('Arial', 10, 'bold'))

        # Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        self.tab_cards = ttk.Frame(self.notebook)
        self.tab_history = ttk.Frame(self.notebook)
        self.tab_settings = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_cards, text=" 📇 Quản Lý Thẻ & Ra Vào ")
        self.notebook.add(self.tab_history, text=" 📜 Lịch Sử Giao Dịch ")
        self.notebook.add(self.tab_settings, text=" ⚙️ Thiết Lập ")

        self.setup_cards_tab()
        self.setup_history_tab()
        self.setup_settings_tab()

        # Update loop
        self.update_ui_loop()

    def setup_cards_tab(self):
        # Tools & Controls
        ctrl_frame = tk.Frame(self.tab_cards, bg="#f4f4f4")
        ctrl_frame.pack(fill='x', padx=10, pady=10)

        # Control Group
        btn_group = tk.LabelFrame(ctrl_frame, text="ĐIỀU KHIỂN CỔNG THỦ CÔNG", font=('Arial', 9, 'bold'), labelanchor='n')
        btn_group.pack(side='left', padx=5)

        tk.Button(btn_group, text="🔓 MỞ CỔNG VÀO", command=lambda: self.manual_open("IN"), bg="#27ae60", fg="white", font=('Arial', 10, 'bold')).pack(side='left', padx=10, pady=10)
        tk.Button(btn_group, text="🔓 MỞ CỔNG RA", command=lambda: self.manual_open("OUT"), bg="#2980b9", fg="white", font=('Arial', 10, 'bold')).pack(side='left', padx=10, pady=10)

        # Status
        self.lbl_status = tk.Label(ctrl_frame, text="Trạng thái: Đang đợi ESP32...", fg="#7f8c8d", font=('Arial', 10, 'bold'), bg="#f4f4f4")
        self.lbl_status.pack(side='right', padx=10)

        # Table
        cols = ("STT", "ID Thẻ", "Chủ thẻ", "Giờ Vào", "Giờ Ra", "Thời Gian Đỗ", "Loại Thẻ", "Phí Đỗ Hiện Tại (VND)")
        self.tree = ttk.Treeview(self.tab_cards, columns=cols, show='headings')
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor='center', width=130)
        
        self.tree.column("STT", width=40)
        self.tree.column("ID Thẻ", width=110)
        self.tree.pack(fill='both', expand=True, padx=10, pady=5)

        # Context Menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="✏️ Đổi tên chủ thẻ", command=self.rename_card)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="⭐ Đặt làm thẻ ADMIN", command=lambda: self.set_card_type("admin"))
        self.context_menu.add_command(label="👤 Đặt làm thẻ THƯỜNG", command=lambda: self.set_card_type("regular"))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="❌ Xóa thẻ này", command=self.delete_card)

        self.tree.bind("<Button-3>", self.show_context_menu)

    def setup_history_tab(self):
        tk.Label(self.tab_history, text="NHẬT KÝ HỆ THỐNG (RAW LOG):", font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=5)
        self.log_txt = tk.Text(self.tab_history, height=12, bg="#2c3e50", fg="#ecf0f1", font=('Consolas', 9))
        self.log_txt.pack(fill='x', padx=10, pady=5)

        cols = ("Thời Gian", "ID Thẻ", "Sự Kiện", "Chi Tiết")
        self.history_tree = ttk.Treeview(self.tab_history, columns=cols, show='headings')
        for col in cols:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, anchor='center')
        self.history_tree.pack(fill='both', expand=True, padx=10, pady=5)

    def setup_settings_tab(self):
        frame = tk.Frame(self.tab_settings, padx=50, pady=50)
        frame.pack()
        tk.Label(frame, text="GIÁ GỬI XE (VND/giờ):", font=('Arial', 12)).grid(row=0, column=0, pady=10)
        self.ent_rate = tk.Entry(frame, font=('Arial', 12))
        self.ent_rate.insert(0, str(store.data["config"]["hourly_rate"]))
        self.ent_rate.grid(row=0, column=1, padx=10)
        tk.Button(frame, text="CẬP NHẬT GIÁ", command=self.save_settings, bg="#2ecc71", fg="white", width=20).grid(row=1, column=0, columnspan=2, pady=20)

    # --- ACTIONS ---
    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def rename_card(self):
        selected = self.tree.selection()
        if not selected: return
        uid = self.tree.item(selected[0])['values'][1]
        old_name = self.tree.item(selected[0])['values'][2]
        new_name = simpledialog.askstring("Đổi tên", f"Nhập tên mới cho thẻ {uid}:", initialvalue=old_name)
        if new_name:
            with store.lock:
                store.data["cards"][uid]["name"] = new_name
                store.save_db()
            self.refresh_cards_table()

    def set_card_type(self, ctype):
        selected = self.tree.selection()
        if not selected: return
        uid = self.tree.item(selected[0])['values'][1]
        with store.lock:
            store.data["cards"][uid]["type"] = ctype
            store.save_db()
        self.refresh_cards_table()

    def delete_card(self):
        selected = self.tree.selection()
        if not selected: return
        uid = self.tree.item(selected[0])['values'][1]
        if messagebox.askyesno("Xác nhận", f"Bạn chắc chắn muốn xóa thẻ {uid}?"):
            with store.lock:
                if uid in store.data["cards"]:
                    del store.data["cards"][uid]
                    store.save_db()
            self.refresh_cards_table()

    def manual_open(self, gate):
        if not self.active_clients:
            messagebox.showwarning("Lỗi", "Không có thiết bị ESP32 nào đang kết nối!")
            return
        
        msg = json.dumps({"gate": gate, "action": "OPEN"}) + "\n"
        with store.lock:
            dead_clients = []
            for client in self.active_clients:
                try:
                    client.sendall(msg.encode('utf-8'))
                except:
                    dead_clients.append(client)
            for dc in dead_clients:
                if dc in self.active_clients: self.active_clients.remove(dc)
        
        self.log_event("SYSTEM", f"MỞ CỔNG {gate}", "Lệnh được gửi từ PC")

    def save_settings(self):
        try:
            rate = int(self.ent_rate.get())
            store.data["config"]["hourly_rate"] = rate
            store.save_db()
            messagebox.showinfo("Th̀nh công", "Đã cập nhật giá mới.")
        except: messagebox.showerror("Lỗi", "Vui lòng nhập số hợp lệ")

    def refresh_cards_table(self):
        def ui_refresh():
            for item in self.tree.get_children(): self.tree.delete(item)
            with store.lock:
                i = 1
                now = datetime.now()
                for uid, card in store.data["cards"].items():
                    is_inside = card.get("isInside", False)
                    entry_time = card.get("entry_time", "-")
                    exit_time = card.get("exit_time", "-")
                    duration_str = "-"
                    current_fee = "0đ"
                    
                    if is_inside and entry_time != "-":
                        try:
                            et_dt = datetime.strptime(entry_time, "%Y-%m-%d %H:%M:%S")
                            diff = now - et_dt
                            duration_str = str(timedelta(seconds=int(diff.total_seconds())))
                            if card.get("type") == "admin": current_fee = "0đ (Admin)"
                            else:
                                hours = math.ceil(diff.total_seconds() / 3600)
                                fee = hours * store.data["config"]["hourly_rate"]
                                current_fee = f"{fee:,}đ"
                        except: pass
                    
                    self.tree.insert("", "end", values=(
                        i, uid, card.get("name", ""), entry_time, exit_time, 
                        duration_str, card.get("type", "regular").upper(), current_fee
                    ))
                    i += 1
        self.root.after(0, ui_refresh)

    def update_ui_loop(self):
        self.refresh_cards_table()
        conn_count = len(self.active_clients)
        if conn_count > 0:
            self.lbl_status.config(text=f"Trạng thái: Đã kết nối ({conn_count})", fg="#2ecc71")
        else:
            self.lbl_status.config(text="Trạng thái: Đang đợi ESP32...", fg="#7f8c8d")
        self.root.after(5000, self.update_ui_loop)

    def log_event(self, uid, event, detail):
        def ui_log():
            t = datetime.now().strftime("%H:%M:%S")
            self.history_tree.insert("", 0, values=(t, uid, event, detail))
            self.log_txt.insert('1.0', f"[{t}] {event} - {uid}: {detail}\n")
        self.root.after(0, ui_log)


    def show_payment_popup(self, uid, fee):
        def ui_popup(): messagebox.showinfo("THANH TOÁN XE RA", f"Thẻ: {uid}\nSố tiền cần thu: {fee:,} VND")
        self.root.after(0, ui_popup)

    def ask_add_card(self, uid):
        def ui_ask():
            if messagebox.askyesno("Thẻ lạ", f"Phát hiện thẻ mới: {uid}\nBạn có muốn thêm vào hệ thống không?"):
                with store.lock:
                    store.data["cards"][uid] = {
                        "name": f"User_{uid[-5:]}", 
                        "type": "regular", 
                        "isInside": False, 
                        "entry_time": None
                    }
                    store.save_db()
                self.log_event(uid, "ĐĂNG KÝ THÀNH CÔNG", "Thẻ mới đã được cấp phép")
                self.refresh_cards_table()
        self.root.after(0, ui_ask)

# --- SERVER ENGINE ---
class ParkingServer:
    def __init__(self, app):
        self.app = app

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(10)
        print(f"[*] Server Listening on {HOST}:{PORT}")
        
        while True:
            conn, addr = server.accept()
            with store.lock:
                self.app.active_clients.append(conn)
            threading.Thread(target=self.client_handler, args=(conn, addr), daemon=True).start()

    def client_handler(self, conn, addr):
        try:
            buffer = ""
            while True:
                data = conn.recv(1024).decode('utf-8')
                if not data: break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        self.handle_msg(conn, line.strip())
        except Exception as e:
            print(f"[-] Client {addr} error: {e}")
        finally:
            with store.lock:
                if conn in self.app.active_clients: self.app.active_clients.remove(conn)
            conn.close()

    def handle_msg(self, conn, line):
        try:
            req = json.loads(line)
            action = req.get("action") or req.get("status")
            uid = req.get("uid")
            gate_raw = req.get("gate", "")
            gate_clean = "IN" if "IN" in gate_raw else "OUT"

            if action == "CHECK":
                with store.lock:
                    if uid not in store.data["cards"]:
                        res = {"gate": gate_clean, "action": "AUTH", "status": "REJECT"}
                        conn.sendall((json.dumps(res) + "\n").encode())
                        self.app.ask_add_card(uid)
                    else:
                        card = store.data["cards"][uid]
                        is_in = "IN" in gate_raw
                        # Chỉ kiểm tra quyền, CHƯA cập nhật database
                        if (is_in and not card["isInside"]) or (not is_in and card["isInside"]):
                            fee = 0
                            if not is_in: # Tính phí phục vụ hiển thị LCD
                                fee, _ = store.calculate_fee(uid, datetime.now())
                            
                            res = {"gate": gate_clean, "action": "AUTH", "status": "SUCCESS", "fee": fee}
                            conn.sendall((json.dumps(res) + "\n").encode())
                        else:
                            res = {"gate": gate_clean, "action": "AUTH", "status": "WRONG_WAY"}
                            conn.sendall((json.dumps(res) + "\n").encode())

            elif action == "DONE":
                with store.lock:
                    if uid in store.data["cards"]:
                        card = store.data["cards"][uid]
                        is_in = "IN" in gate_raw
                        now = datetime.now()
                        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

                        if is_in:
                            card["isInside"] = True
                            card["entry_time"] = now_str
                            self.app.log_event(uid, "VÀO THÀNH CÔNG", "Xe đã qua cổng")
                        else:
                            fee, _ = store.calculate_fee(uid, now)
                            card["isInside"] = False
                            card["exit_time"] = now_str
                            self.app.log_event(uid, "RA THÀNH CÔNG", f"Phí: {fee:,}đ")

                        store.save_db()
                        self.app.refresh_cards_table()

        except Exception as e:
            print(f"JSON Error: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ParkingApp(root)
    server = ParkingServer(app)
    threading.Thread(target=server.start, daemon=True).start()
    root.mainloop()
