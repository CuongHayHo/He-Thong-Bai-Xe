import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta
import math

class ModernParkingGUI:
    def __init__(self, root, backend):
        self.root = root
        self.backend = backend
        self.root.title("PREMIUM SMART PARKING SYSTEM v3.5 (Decoupled)")
        self.root.geometry("1100x750")
        
        # Color Palette
        self.colors = {
            "bg": "#1e1e2e",
            "surface": "#2d2d44", 
            "accent": "#7289da",
            "success": "#2ecc71",
            "danger": "#e74c3c",
            "text": "#ffffff",
            "text_dim": "#a9b1d6"
        }
        
        self.root.configure(bg=self.colors["bg"])
        self.setup_styles()
        self.create_widgets()
        
        # Throttling mechanism
        self.needs_refresh = False
        
        # Connect Backend Callbacks
        self.backend.set_callback("on_event", self._on_backend_event)
        self.backend.set_callback("on_refresh", self.refresh_table)
        self.backend.set_callback("on_new_card", self._on_new_card)
        self.backend.set_callback("on_client_change", self._on_client_change)
        
        self.update_ui_loop()

    def setup_styles(self):
        # ... style config unchanged ...
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", background=self.colors["surface"], foreground=self.colors["text"],
                        fieldbackground=self.colors["surface"], rowheight=35, font=('Segoe UI', 10))
        style.map("Treeview", background=[('selected', self.colors["accent"])])
        style.configure("Treeview.Heading", background=self.colors["bg"], foreground=self.colors["text"], font=('Segoe UI', 10, 'bold'))
        style.configure("TNotebook", background=self.colors["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=self.colors["surface"], foreground=self.colors["text_dim"], padding=[20, 5])
        style.map("TNotebook.Tab", background=[("selected", self.colors["accent"])], foreground=[("selected", "#ffffff")])
        style.configure("TFrame", background=self.colors["bg"])

    def create_widgets(self):
        # Header
        header = tk.Frame(self.root, bg=self.colors["surface"], height=60)
        header.pack(fill='x', side='top')
        header.pack_propagate(False)
        tk.Label(header, text="PARKING CONTROL CENTER", fg=self.colors["success"], bg=self.colors["surface"], font=('Segoe UI', 16, 'bold')).pack(side='left', padx=20)
        self.lbl_status = tk.Label(header, text="○ WAITING FOR ESP32...", fg=self.colors["text_dim"], bg=self.colors["surface"], font=('Segoe UI', 10, 'bold'))
        self.lbl_status.pack(side='right', padx=20)

        # Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=20, pady=10)
        self.tab_dashboard = ttk.Frame(self.notebook)
        self.tab_history = ttk.Frame(self.notebook)
        self.tab_settings = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_dashboard, text=" DASHBOARD ")
        self.notebook.add(self.tab_history, text=" LOGS ")
        self.notebook.add(self.tab_settings, text=" SETTINGS ")

        self.setup_dashboard()
        self.setup_history()
        self.setup_settings()

    def setup_dashboard(self):
        ctrl_frame = tk.Frame(self.tab_dashboard, bg=self.colors["bg"])
        ctrl_frame.pack(fill='x', pady=10)
        tk.Button(ctrl_frame, text="MỞ CỔNG VÀO (IN)", command=lambda: self.backend.manual_open("IN"), bg=self.colors["success"], fg="#ffffff", font=('Segoe UI', 9, 'bold'), border=0, padx=15, pady=5).pack(side='left', padx=5)
        tk.Button(ctrl_frame, text="MỞ CỔNG RA (OUT)", command=lambda: self.backend.manual_open("OUT"), bg=self.colors["accent"], fg="#ffffff", font=('Segoe UI', 9, 'bold'), border=0, padx=15, pady=5).pack(side='left', padx=5)

        cols = ("STT", "UID", "Tên Chủ Thẻ", "Giờ Vào", "Thời Gian Đỗ", "Loại", "Phí Tạm Tính")
        self.tree = ttk.Treeview(self.tab_dashboard, columns=cols, show='headings')
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor='center', width=120)
        self.tree.column("STT", width=40)
        self.tree.pack(fill='both', expand=True)

        self.ctx = tk.Menu(self.root, tearoff=0, bg=self.colors["surface"], fg=self.colors["text"], borderwidth=0)
        self.ctx.add_command(label="✏️ Đổi tên chủ thẻ", command=self.rename_card)
        self.ctx.add_command(label="⭐ Phân quyền ADMIN", command=lambda: self.set_card_type("admin"))
        self.ctx.add_command(label="👤 Phân quyền REGULAR", command=lambda: self.set_card_type("regular"))
        self.ctx.add_separator()
        self.ctx.add_command(label="❌ Xóa khỏi hệ thống", command=self.delete_card)
        self.tree.bind("<Button-3>", lambda e: self.ctx.post(e.x_root, e.y_root) if self.tree.identify_row(e.y) else None)

    def setup_history(self):
        self.log_txt = tk.Text(self.tab_history, height=10, bg="#000000", fg="#00ff00", font=('Consolas', 9))
        self.log_txt.pack(fill='x', pady=5)
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
        self.ent_rate.insert(0, str(self.backend.store.data["config"]["hourly_rate"]))
        self.ent_rate.grid(row=0, column=1, padx=20)
        tk.Button(frame, text="LƯU THIẾT LẬP", command=self.save_settings, bg=self.colors["success"], fg="#ffffff", padx=30, pady=10, border=0).grid(row=1, column=0, columnspan=2, pady=30)

    # --- CALLBACK HANDLERS ---
    def _on_backend_event(self, uid, event, detail):
        self.root.after(0, lambda: self._log_to_ui(uid, event, detail))

    def _on_new_card(self, uid):
        self.root.after(0, lambda: self.ask_add_card(uid))

    def _on_client_change(self, count):
        self.root.after(0, lambda: self._update_status(count))

    def _update_status(self, count):
        if count > 0:
            self.lbl_status.config(text=f"● CONNECTED: {count} DEVICES", fg=self.colors["success"])
        else:
            self.lbl_status.config(text="○ WAITING FOR ESP32...", fg=self.colors["text_dim"])

    def _log_to_ui(self, uid, event, detail):
        t = datetime.now().strftime("%H:%M:%S")
        try:
            self.htree.insert("", 0, values=(t, uid, event, detail))
            self.log_txt.insert('1.0', f"[{t}] {event} - {uid}: {detail}\n")
            # Tự động xóa bớt log cũ nếu quá dài để tránh lag
            if int(self.log_txt.index('end-1c').split('.')[0]) > 500:
                self.log_txt.delete('500.0', 'end')
        except: pass

    def ask_add_card(self, uid):
        # Thẻ lạ callback
        if messagebox.askyesno("Thẻ lạ", f"Phát hiện thẻ mới {uid}\nBạn có muốn thêm vào hệ thống không?"):
            with self.backend.store.lock:
                self.backend.store.data["cards"][uid] = {"name": f"User_{uid[-4:]}", "type": "regular", "isInside": False, "entry_time": None}
                self.backend.store.request_save()
            self._log_to_ui(uid, "REG", "Đã cấp quyền")
            self.needs_refresh = True

    def rename_card(self):
        sel = self.tree.selection()
        if not sel: return
        uid = self.tree.item(sel[0])['values'][1]
        name = simpledialog.askstring("Rename", "Nhập tên mới:", initialvalue=self.tree.item(sel[0])['values'][2])
        if name:
            with self.backend.store.lock:
                self.backend.store.data["cards"][uid]["name"] = name
                self.backend.store.request_save()
            self.refresh_table()

    def set_card_type(self, t):
        sel = self.tree.selection()
        if not sel: return
        uid = self.tree.item(sel[0])['values'][1]
        with self.backend.store.lock:
            self.backend.store.data["cards"][uid]["type"] = t
            self.backend.store.request_save()
        self.refresh_table()

    def delete_card(self):
        sel = self.tree.selection()
        if not sel: return
        uid = self.tree.item(sel[0])['values'][1]
        if messagebox.askyesno("Confirm", f"Xóa thẻ {uid}?"):
            with self.backend.store.lock:
                if uid in self.backend.store.data["cards"]:
                    del self.backend.store.data["cards"][uid]
                    self.backend.store.request_save()
            self.refresh_table()

    def save_settings(self):
        try:
            val = int(self.ent_rate.get())
            with self.backend.store.lock:
                self.backend.store.data["config"]["hourly_rate"] = val
                self.backend.store.request_save()
            messagebox.showinfo("OK", "Đã cập nhật giá mới")
        except: messagebox.showerror("Error", "Số không hợp lệ")

    def refresh_table(self):
        # Không vẽ lại UI ngay lập tức, chỉ bật cờ báo hiệu
        self.needs_refresh = True

    def _perform_ui_refresh(self):
        # Thực hiện việc vẽ lại bảng trong luồng UI chính
        for item in self.tree.get_children(): self.tree.delete(item)
        with self.backend.store.lock:
            i = 1
            now = datetime.now()
            # Copy data để tránh giữ lock lâu
            cards_copy = list(self.backend.store.data["cards"].items())
            
            for uid, c in cards_copy:
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
                            f, _ = self.backend.store.calculate_fee(uid, now)
                            fee = f"{f:,}đ"
                    except: pass
                self.tree.insert("", "end", values=(i, uid, c.get("name", ""), entry, dur, c.get("type", "regular").upper(), fee))
                i += 1
        self.needs_refresh = False

    def update_ui_loop(self):
        # Chạy vòng lặp kiểm tra 500ms một lần
        if self.needs_refresh:
            try:
                self._perform_ui_refresh()
            except Exception as e:
                print(f"UI Refresh Error: {e}")
        
        # Loop nhanh hơn để UI mượt mà nhưng không tốn tài nguyên vẽ lại
        self.root.after(500, self.update_ui_loop)
