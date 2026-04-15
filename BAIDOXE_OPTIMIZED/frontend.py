import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta

class ScrollableFrame(tk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=kwargs.get("bg", "#0f172a"), highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_window = tk.Frame(self.canvas, bg=kwargs.get("bg", "#0f172a"))

        self.scrollable_window.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # Lưu id của window để có thể thay đổi kích thước sau này
        self.window_id = self.canvas.create_window((0, 0), window=self.scrollable_window, anchor="nw")
        
        # Ép frame bên trong rộng bằng canvas khi canvas thay đổi kích thước
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    def _on_canvas_configure(self, event):
        # Cập nhật độ rộng của frame bên trong để bằng với canvas
        self.canvas.itemconfigure(self.window_id, width=event.width)

class ModernParkingGUI:
    def __init__(self, root, backend):
        self.root = root
        self.backend = backend
        self.root.title("PREMIUM SMART PARKING SYSTEM v4.0")
        self.root.geometry("1150x800")
        
        # Color Palette: Professional Midnight
        self.colors = {
            "bg": "#0f172a",         # Deep Navy
            "surface": "#1e293b",    # Slate Blue
            "accent": "#3b82f6",     # Primary Blue
            "success": "#10b981",    # Emerald Green
            "danger": "#ef4444",     # Muted Red
            "warning": "#f59e0b",    # Amber
            "text": "#f8fafc",       # Clean White
            "text_dim": "#94a3b8"    # Slate Gray
        }
        
        self.root.configure(bg=self.colors["bg"])
        self.setup_styles()
        
        # UI State
        self.card_rows = {} # uid -> {frame, dur_label, fee_label, type_btn}
        self.needs_refresh = True
        
        self.create_widgets()
        
        # Connect Backend Callbacks
        self.backend.set_callback("on_event", self._on_backend_event)
        self.backend.set_callback("on_refresh", self.refresh_table)
        self.backend.set_callback("on_new_card", self._on_new_card)
        self.backend.set_callback("on_client_change", self._on_client_change)
        
        self.update_ui_loop()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TNotebook", background=self.colors["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=self.colors["surface"], foreground=self.colors["text_dim"], padding=[20, 5])
        style.map("TNotebook.Tab", background=[("selected", self.colors["accent"])], foreground=[("selected", "#ffffff")])
        style.configure("Vertical.TScrollbar", background=self.colors["surface"], bordercolor=self.colors["bg"], arrowcolor=self.colors["accent"])

    def create_widgets(self):
        # Header
        header = tk.Frame(self.root, bg=self.colors["surface"], height=70)
        header.pack(fill='x', side='top')
        header.pack_propagate(False)
        tk.Label(header, text="PARKING CONTROL CENTER", fg=self.colors["success"], bg=self.colors["surface"], font=('Segoe UI', 18, 'bold')).pack(side='left', padx=30)
        self.lbl_status = tk.Label(header, text="○ WAITING FOR ESP32...", fg=self.colors["text_dim"], bg=self.colors["surface"], font=('Segoe UI', 10, 'bold'))
        self.lbl_status.pack(side='right', padx=30)

        # Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=20, pady=10)
        self.tab_dashboard = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.tab_history = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.tab_settings = tk.Frame(self.notebook, bg=self.colors["bg"])
        self.notebook.add(self.tab_dashboard, text="  DASHBOARD  ")
        self.notebook.add(self.tab_history, text="  HTR LOGS  ")
        self.notebook.add(self.tab_settings, text="  SETTINGS  ")

        self.setup_dashboard()
        self.setup_history()
        self.setup_settings()

    def setup_dashboard(self):
        # Toolbar
        tools = tk.Frame(self.tab_dashboard, bg=self.colors["bg"])
        tools.pack(fill='x', pady=10)
        tk.Button(tools, text="⚡ MỞ CỔNG IN", command=lambda: self.backend.manual_open("IN"), bg=self.colors["success"], fg="#1a1b26", font=('Segoe UI', 9, 'bold'), border=0, padx=20, pady=8).pack(side='left', padx=5)
        tk.Button(tools, text="⚡ MỞ CỔNG OUT", command=lambda: self.backend.manual_open("OUT"), bg=self.colors["accent"], fg="#ffffff", font=('Segoe UI', 9, 'bold'), border=0, padx=20, pady=8).pack(side='left', padx=5)
        
        # Scrollable List Container
        self.list_frame = ScrollableFrame(self.tab_dashboard, bg=self.colors["bg"])
        self.list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Cấu hình các cột (weight) cho toàn bộ bảng
        # Cột: 0:Tên, 1:UID, 2:Status, 3:Dur, 4:Fee, 5:Actions
        self.list_frame.scrollable_window.columnconfigure(0, weight=1, minsize=200) # Tên giãn rộng nhất
        self.list_frame.scrollable_window.columnconfigure(1, minsize=150)
        self.list_frame.scrollable_window.columnconfigure(2, minsize=100)
        self.list_frame.scrollable_window.columnconfigure(3, minsize=100)
        self.list_frame.scrollable_window.columnconfigure(4, minsize=100)
        self.list_frame.scrollable_window.columnconfigure(5, minsize=300)

    def setup_history(self):
        self.log_txt = tk.Text(self.tab_history, height=12, bg="#16161e", fg=self.colors["success"], font=('Consolas', 10), borderwidth=0)
        self.log_txt.pack(fill='x', pady=10, padx=10)
        
        cols = ("Thời Gian", "UID", "Sự Kiện", "Chi Tiết")
        self.htree = ttk.Treeview(self.tab_history, columns=cols, show='headings', height=10)
        for col in cols:
            self.htree.heading(col, text=col)
            self.htree.column(col, anchor='center')
        self.htree.pack(fill='both', expand=True, padx=10, pady=5)

    def setup_settings(self):
        frame = tk.Frame(self.tab_settings, bg=self.colors["bg"])
        frame.pack(expand=True)
        tk.Label(frame, text="ĐƠN GIÁ (VND/GIỜ):", fg=self.colors["text"], bg=self.colors["bg"], font=('Segoe UI', 12, 'bold')).grid(row=0, column=0, pady=20)
        self.ent_rate = tk.Entry(frame, font=('Segoe UI', 14), bg=self.colors["surface"], fg=self.colors["text"], border=0, insertbackground="white")
        self.ent_rate.insert(0, str(self.backend.store.data["config"]["hourly_rate"]))
        self.ent_rate.grid(row=0, column=1, padx=20)
        tk.Button(frame, text="LƯU THIẾT LẬP", command=self.save_settings, bg=self.colors["success"], fg="#1a1b26", padx=40, pady=12, border=0, font=('Segoe UI', 10, 'bold')).grid(row=1, column=0, columnspan=2, pady=40)

    # --- ACTION HANDLERS ---
    def set_card_type(self, uid, t):
        with self.backend.store.lock:
            self.backend.store.data["cards"][uid]["type"] = t
            self.backend.store.request_save()
        self.refresh_table()

    def rename_card(self, uid):
        old_name = self.backend.store.data["cards"][uid].get("name", "")
        name = simpledialog.askstring("Rename", "Nhập tên mới cho thẻ:", initialvalue=old_name)
        if name:
            with self.backend.store.lock:
                self.backend.store.data["cards"][uid]["name"] = name
                self.backend.store.request_save()
            self.refresh_table()

    def delete_card(self, uid):
        if messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa thẻ {uid} khỏi hệ thống?"):
            with self.backend.store.lock:
                if uid in self.backend.store.data["cards"]:
                    del self.backend.store.data["cards"][uid]
                    self.backend.store.request_save()
            self.refresh_table()

    # --- UI UPDATE LOGIC ---
    def refresh_table(self):
        self.needs_refresh = True

    def _perform_ui_refresh(self):
        # Clear existing
        for child in self.list_frame.scrollable_window.winfo_children():
            child.destroy()
        self.card_rows.clear()
        
        # 1. Vẽ Header (Dòng 0)
        headers = [("Tên Chủ Thẻ", 0), ("UID Thẻ", 1), ("Trạng Thái", 2), ("Thời Gian", 3), ("Phí", 4), ("Hành Động", 5)]
        for txt, col in headers:
            sticky = 'w' if col <= 1 else ''
            tk.Label(self.list_frame.scrollable_window, text=txt.upper(), fg=self.colors["accent"], bg=self.colors["bg"], 
                     font=('Segoe UI', 9, 'bold'), pady=10).grid(row=0, column=col, sticky=sticky, padx=10)
        
        # 2. Vẽ Dữ liệu (Dòng 1 trở đi)
        with self.backend.store.lock:
            cards = self.backend.store.data["cards"]
            sorted_uids = sorted(cards.keys(), key=lambda u: cards[u].get("isInside", False), reverse=True)
            
            for idx, uid in enumerate(sorted_uids, start=1):
                c = cards[uid]
                
                # Name
                tk.Label(self.list_frame.scrollable_window, text=c.get("name", "Unknown"), fg="#ffffff", bg=self.colors["bg"], 
                         font=('Segoe UI', 10, 'bold'), anchor='w').grid(row=idx, column=0, padx=10, pady=10, sticky='ew')
                
                # UID
                tk.Label(self.list_frame.scrollable_window, text=uid, fg=self.colors["text_dim"], bg=self.colors["bg"], 
                         font=('Consolas', 10), anchor='w').grid(row=idx, column=1, padx=10, pady=10, sticky='w')
                
                # Status
                is_in = c.get("isInside", False)
                st_color = self.colors["success"] if is_in else self.colors["text_dim"]
                st_txt = "● TRONG BÃI" if is_in else "○ ĐÃ RA"
                tk.Label(self.list_frame.scrollable_window, text=st_txt, fg=st_color, bg=self.colors["bg"], 
                         font=('Segoe UI', 8, 'bold')).grid(row=idx, column=2, padx=10, pady=10)
                
                # Duration
                dur_lbl = tk.Label(self.list_frame.scrollable_window, text="-", fg="#ffffff", bg=self.colors["bg"], 
                                   font=('Segoe UI', 10))
                dur_lbl.grid(row=idx, column=3, padx=10, pady=10)
                
                # Fee
                fee_lbl = tk.Label(self.list_frame.scrollable_window, text="0đ", fg=self.colors["warning"], bg=self.colors["bg"], 
                                   font=('Segoe UI', 10, 'bold'))
                fee_lbl.grid(row=idx, column=4, padx=10, pady=10)
                
                # Action Buttons
                btn_frame = tk.Frame(self.list_frame.scrollable_window, bg=self.colors["bg"])
                btn_frame.grid(row=idx, column=5, padx=15, pady=10, sticky='e')
                
                ctype = c.get("type", "regular")
                type_btn_txt = "⭐ ADMIN" if ctype == "admin" else "👤 USER"
                type_btn_clr = self.colors["warning"] if ctype == "admin" else self.colors["surface"]
                
                # Toggle Role Button
                new_type = "regular" if ctype == "admin" else "admin"
                tk.Button(btn_frame, text=type_btn_txt, command=lambda u=uid, t=new_type: self.set_card_type(u, t), 
                          bg=type_btn_clr, fg="#1a1b26", font=('Segoe UI', 8, 'bold'), border=0, padx=12, pady=4).pack(side='left', padx=5)
                
                tk.Button(btn_frame, text=" ✏️ SỬA ", command=lambda u=uid: self.rename_card(u), 
                          bg=self.colors["accent"], fg="#ffffff", font=('Segoe UI', 8, 'bold'), border=0, padx=10, pady=4).pack(side='left', padx=5)
                
                tk.Button(btn_frame, text=" 🗑️ XÓA ", command=lambda u=uid: self.delete_card(u), 
                          bg=self.colors["danger"], fg="#ffffff", font=('Segoe UI', 8, 'bold'), border=0, padx=10, pady=4).pack(side='left', padx=5)
                
                self.card_rows[uid] = {"dur_lbl": dur_lbl, "fee_lbl": fee_lbl}
        
        self.needs_refresh = False
        self._update_timers() # Immediate first update

    def _update_timers(self):
        # Updates only the duration labels and fees without destroying frames
        now = datetime.now()
        with self.backend.store.lock:
            for uid, widgets in self.card_rows.items():
                c = self.backend.store.data["cards"].get(uid)
                if not c: continue
                
                dur_txt = "-"
                fee_txt = "0đ"
                
                if c.get("isInside"):
                    entry_str = c.get("entry_time")
                    if entry_str:
                        try:
                            edt = datetime.strptime(entry_str, "%Y-%m-%d %H:%M:%S")
                            diff = now - edt
                            dur_txt = str(timedelta(seconds=int(diff.total_seconds())))
                            if c.get("type") == "admin":
                                fee_txt = "FREE"
                            else:
                                fee, _ = self.backend.store.calculate_fee(uid, now)
                                fee_txt = f"{fee:,}đ"
                        except: pass
                
                widgets["dur_lbl"].config(text=dur_txt)
                widgets["fee_lbl"].config(text=fee_txt)

    def update_ui_loop(self):
        if self.needs_refresh:
            self._perform_ui_refresh()
        else:
            self._update_timers()
        self.root.after(1000, self.update_ui_loop)

    # --- CALLBACKS ---
    def _on_backend_event(self, uid, event, detail):
        self.root.after(0, lambda: self._log_to_ui(uid, event, detail))

    def _on_new_card(self, uid):
        self.root.after(0, lambda: self.ask_add_card(uid))

    def _on_client_change(self, count):
        self.root.after(0, lambda: self._update_status(count))

    def _update_status(self, count):
        if count > 0:
            self.lbl_status.config(text=f"● ONLINE: {count} DEVICES", fg=self.colors["success"])
        else:
            self.lbl_status.config(text="○ WAITING FOR ESP32...", fg=self.colors["text_dim"])

    def _log_to_ui(self, uid, event, detail):
        t = datetime.now().strftime("%H:%M:%S")
        try:
            self.htree.insert("", 0, values=(t, uid, event, detail))
            self.log_txt.insert('1.0', f"[{t}] {event} - {uid}: {detail}\n")
            if int(self.log_txt.index('end-1c').split('.')[0]) > 200:
                self.log_txt.delete('200.0', 'end')
        except: pass

    def ask_add_card(self, uid):
        if messagebox.askyesno("Thẻ mới", f"Phát hiện thẻ mới {uid}\nBạn có muốn cấp quyền không?"):
            with self.backend.store.lock:
                self.backend.store.data["cards"][uid] = {"name": f"User_{uid[-4:]}", "type": "regular", "isInside": False, "entry_time": None}
                self.backend.store.request_save()
            self._log_to_ui(uid, "REG", "Đã cấp quyền")
            self.refresh_table()

    def save_settings(self):
        try:
            val = int(self.ent_rate.get())
            with self.backend.store.lock:
                self.backend.store.data["config"]["hourly_rate"] = val
                self.backend.store.request_save()
            messagebox.showinfo("Thành công", "Đã cập nhật đơn giá.")
        except: messagebox.showerror("Lỗi", "Số tiền không hợp lệ.")
