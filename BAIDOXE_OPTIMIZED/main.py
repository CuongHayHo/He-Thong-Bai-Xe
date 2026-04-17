import tkinter as tk
from backend import ParkingBackend
from frontend import ModernParkingGUI
import os
import sys

def main():
    # Kiểm tra file chứng chỉ ngay tại thư mục hiện hành
    if not os.path.exists("server.crt") or not os.path.exists("server.key"):
        print("="*50)
        print("QUAN TRỌNG: KHÔNG TÌM THẤY FILE CHỨNG CHỈ SSL!")
        print("Vui lòng chạy file gen_cert.py trong thư mục này trước.")
        print("="*50)
    
    # Khởi tạo Backend
    backend = ParkingBackend()
    
    # Khởi động các luồng Server (TCP/SSL)
    backend.start_server()
    
    # Khởi tạo Giao diện (Frontend)
    root = tk.Tk()
    app = ModernParkingGUI(root, backend)
    
    print("Hệ thống SSL đã sẵn sàng. Đang mở giao diện...")
    
    # Chạy vòng lặp chính của giao diện
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Đang đóng hệ thống...")
        sys.exit(0)

if __name__ == "__main__":
    main()
