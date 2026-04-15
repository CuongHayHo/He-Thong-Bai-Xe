import tkinter as tk
from backend import ParkingBackend
from frontend import ModernParkingGUI
import threading

def main():
    # 1. Khởi tạo Backend (Xử lý dữ liệu & TCP Server)
    backend = ParkingBackend()
    
    # 2. Khởi tạo Giao diện chính (Frontend)
    root = tk.Tk()
    app = ModernParkingGUI(root, backend)
    
    # 3. Chạy Server mạng trên một luồng riêng
    backend.start_server()
    
    # 4. Chạy vòng lặp Giao diện
    root.mainloop()

if __name__ == "__main__":
    main()
