import tkinter as tk
import threading
import time
import os
from screeninfo import get_monitors
import pystray
from PIL import Image, ImageDraw, ImageFont
from plyer import notification
import sys

# =================== Biến toàn cục ===================
interval_minutes = 30   # mặc định 30 phút
running = True
root = None
countdown_seconds = interval_minutes * 60
tray_icon = None
lock = threading.Lock()

# =================== Vẽ icon với countdown ===================
def create_icon(text="💧"):
    """Tạo icon system tray có chữ"""
    img = Image.new("RGB", (64, 64), "blue")
    d = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except (OSError, IOError):
        font = ImageFont.load_default()

    # dùng textbbox để tính kích thước
    bbox = d.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]

    d.text(((64 - w) / 2, (64 - h) / 2), text, font=font, fill="white")
    return img


# =================== Popup ===================
popup_windows = []  # lưu tất cả popup đang mở

def show_popup():
    global popup_windows
    popup_windows = []  # reset danh sách popup mới mỗi lần mở

    monitors = get_monitors()

    for m in monitors:
        popup = tk.Toplevel(root)
        popup.title("Uống nước đi nào 💧")

        # full màn hình mỗi monitor
        popup.geometry(f"{m.width}x{m.height}+{m.x}+{m.y}")
        popup.overrideredirect(True)  # bỏ khung
        popup.attributes("-topmost", True)
        popup.configure(bg="black")  # nền đen

        # Frame overlay mờ
        overlay = tk.Frame(popup, bg="black")
        overlay.place(relwidth=1, relheight=1)

        label = tk.Label(
            overlay,
            text="💦 Đến giờ uống nước rồi!",
            font=("Arial", 60, "bold"),
            bg="black"
        )
        label.pack(expand=True)

        def confirm_all():
            global countdown_seconds, interval_minutes, popup_windows
            # Đóng tất cả popup
            for win in popup_windows:
                try:
                    win.destroy()
                except tk.TclError:
                    pass
            popup_windows.clear()

            # Reset lại thời gian
            with lock:
                countdown_seconds = interval_minutes * 60

        btn = tk.Button(
            overlay,
            text="Đã uống ✅",
            command=confirm_all,
            font=("Arial", 28, "bold"),
            bg="green",
            fg="white",
            activebackground="darkgreen",
            relief="raised",
            padx=20,
            pady=10
        )
        btn.pack(pady=50)

        # Bind phím Enter để đóng popup (tránh vấn đề closure)
        def on_key_press(event, popup_window=popup):
            popup_window.focus_set()
        
        def on_enter_press(event, confirm_func=confirm_all):
            confirm_func()

        popup.bind("<Return>", on_enter_press)
        popup.bind("<KeyPress>", on_key_press)
        popup.focus_set()  # đặt focus cho popup

        # Thêm popup vào danh sách trước khi tạo animation
        popup_windows.append(popup)

    # Animation đổi màu cầu vồng cho TẤT CẢ popup
    colors = ["red", "orange", "yellow", "green", "blue", "purple"]

    def animate_all(i=0):
        # Chỉ chạy animation nếu còn popup nào đó
        if popup_windows:
            for popup in popup_windows:
                try:
                    # Tìm label trong popup để đổi màu
                    for widget in popup.winfo_children():
                        if isinstance(widget, tk.Frame):  # overlay frame
                            for child in widget.winfo_children():
                                if isinstance(child, tk.Label) and "💦" in child.cget("text"):
                                    child.config(fg=colors[i % len(colors)])
                except tk.TclError:
                    # Bỏ qua nếu popup đã bị destroy
                    pass
            
            # Tiếp tục animation nếu còn popup
            if popup_windows:
                root.after(400, animate_all, i + 1)

    animate_all()


# =================== Countdown loop ===================
def countdown_loop():
    global countdown_seconds, tray_icon, interval_minutes, running

    while running:
        with lock:
            if countdown_seconds <= 0:
                print("[DEBUG] Hiện popup uống nước")
                root.after(0, show_popup)

                # không reset ở đây nữa, chỉ reset khi bấm nút
                countdown_seconds = 9999999  # tạm dừng chờ xác nhận

            else:
                countdown_seconds -= 1

        # Cập nhật icon
        mins, secs = divmod(countdown_seconds, 60)
        if mins > 99:
            text = f"{mins}m"
        else:
            text = f"{mins:02}:{secs:02}"

        if tray_icon:
            tray_icon.icon = create_icon(text)
            tray_icon.update_menu()

        time.sleep(1)


# =================== System Tray ===================
def on_quit(icon, item):
    global running, root
    running = False
    icon.stop()
    try:
        root.quit()
        root.destroy()
    except tk.TclError:
        pass
    os._exit(0)   # ⚡ kill process hoàn toàn, không để treo task


def set_interval(minutes):
    global interval_minutes, countdown_seconds
    with lock:
        interval_minutes = minutes
        countdown_seconds = minutes * 60
    print(f"\n⏱️ Đổi thời gian nhắc nhở: {minutes} phút")


def is_checked(minutes):
    return lambda item: interval_minutes == minutes


def setup_tray():
    global tray_icon
    tray_icon = pystray.Icon("Drink Water")
    tray_icon.icon = create_icon("💧")
    tray_icon.title = "Drink Water Reminder"

    tray_icon.menu = pystray.Menu(
        pystray.MenuItem(
            "Thời gian nhắc nhở",
            pystray.Menu(
                pystray.MenuItem("1 phút (test)", lambda icon, item: set_interval(1), checked=is_checked(1)),
                pystray.MenuItem("5 phút", lambda icon, item: set_interval(5), checked=is_checked(5)),
                pystray.MenuItem("10 phút", lambda icon, item: set_interval(10), checked=is_checked(10)),
                pystray.MenuItem("15 phút", lambda icon, item: set_interval(15), checked=is_checked(15)),
                pystray.MenuItem("30 phút", lambda icon, item: set_interval(30), checked=is_checked(30)),
            )
        ),
        pystray.MenuItem("Thoát", on_quit)
    )

    tray_icon.run()

# =================== Splash Screen ===================
def show_splash():
    splash = tk.Toplevel(root)   # dùng root làm parent
    splash.overrideredirect(True)
    splash.geometry("500x300+600+250")
    splash.configure(bg="white")

    label = tk.Label(splash, text="💧 Drink Water Reminder", font=("Arial", 20, "bold"), bg="white")
    label.pack(pady=30)

    guide = tk.Label(
        splash,
        text="App sẽ chạy dưới System Tray (góc dưới phải).\nClick icon 💧 để đổi cài đặt.",
        font=("Arial", 12),
        bg="white"
    )
    guide.pack(pady=10)

    # Progress bar
    progress_frame = tk.Frame(splash, bg="lightgray", height=20, width=400)
    progress_frame.pack(pady=40)
    progress_frame.pack_propagate(False)

    bar = tk.Frame(progress_frame, bg="red", height=20, width=0)
    bar.pack(side="left")

    colors = ["red", "orange", "yellow", "green", "blue", "purple"]

    def animate(i=0):
        if i <= 400:
            bar.config(width=i, bg=colors[(i // 70) % len(colors)])
            splash.after(10, animate, i + 1)
        else:
            splash.destroy()

    animate()
    return splash   # ⚡ trả splash về, không chạy mainloop ở đây

# =================== Main ===================
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # ẩn cửa sổ chính

    # Splash screen
    splash = show_splash()

    # Thread chạy countdown
    threading.Thread(target=countdown_loop, daemon=True).start()

    # Thread chạy tray icon
    tray_thread = threading.Thread(target=setup_tray, daemon=True)
    tray_thread.start()

    root.mainloop()
