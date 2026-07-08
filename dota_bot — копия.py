import cv2
import numpy as np
import mss
import pydirectinput
import time
import json
import os
import threading
import tkinter as tk
from tkinter import messagebox

# Отключаем задержки ввода
pydirectinput.PAUSE = 0.0
pydirectinput.FAILSAFE = False

CONFIG_FILE = "bot_config_v6.json"

# ЦВЕТОВАЯ ПАЛИТРА WINDOWS 11 DARK MODE
COLOR_BG = "#1f1f1f"          # Основной фон окна (Mica dark)
COLOR_CARD = "#2d2d2d"        # Фон карточек/контейнеров
COLOR_ACCENT = "#60cdff"      # Фирменный голубой акцент Win11
COLOR_TEXT = "#ffffff"        # Основной текст
COLOR_TEXT_MUTED = "#a0a0a0"  # Второстепенный текст
COLOR_BTN_GRAY = "#333333"    # Обычная темная кнопка
COLOR_BTN_GREEN = "#2ccb5d"   # Кнопка старта (Win11 Success)
COLOR_BTN_RED = "#e81123"     # Кнопка стопа (Win11 Close/Error)

# Настройки для КРАСНОЙ вагонетки
LOWER_RED1 = np.array([0, 70, 70])
UPPER_RED1 = np.array([10, 255, 255])
LOWER_RED2 = np.array([170, 70, 70])
UPPER_RED2 = np.array([180, 255, 255])

class DotaBotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dota 2 Arkanoid Bot v7.0")
        self.root.geometry("520x760")
        self.root.configure(bg=COLOR_BG)
        self.root.resizable(False, False)
        
        self.is_running = False
        self.is_bot_active = False
        self.current_key = None
        self.prev_gray_zone = None
        
        self.sct = mss.mss()
        self.space_thread = None

        # Дефолтные настройки
        self.config = {
            "monitor": 4,
            "left_x": 35,
            "right_x": 65,
            "top_y": 15,
            "split_y": 75,
            "bottom_y": 90,
            "motion_thresh": 35,
            "min_area": 200,
            "deadzone": 20,
            "show_preview": 1
        }
        self.load_config()
        self.create_ui()
        
        # Запуск цикла тиков
        self.root.after(10, self.master_tick)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.config.update(json.load(f))
            except Exception:
                pass

    def save_config(self):
        self.config["monitor"] = int(self.monitor_spin.get())
        self.config["left_x"] = self.slider_left_x.get()
        self.config["right_x"] = self.slider_right_x.get()
        self.config["top_y"] = self.slider_top_y.get()
        self.config["split_y"] = self.slider_split_y.get()
        self.config["bottom_y"] = self.slider_bottom_y.get()
        self.config["motion_thresh"] = self.slider_thresh.get()
        self.config["min_area"] = self.slider_area.get()
        self.config["deadzone"] = self.slider_deadzone.get()
        self.config["show_preview"] = self.preview_var.get()

        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)
        self.status_label.config(text="Настройки успешно сохранены", fg=COLOR_ACCENT)

    def create_ui(self):
        # ЗАГОЛОВОК ПРИЛОЖЕНИЯ
        title_label = tk.Label(self.root, text="DOTA 2 ARKANOID AUTOMATION", font=("Segoe UI Variable", 12, "bold"), bg=COLOR_BG, fg=COLOR_TEXT)
        title_label.pack(pady=(15, 5))

        # ПАНЕЛЬ УПРАВЛЕНИЯ (Верхняя карточка)
        top_frame = tk.Frame(self.root, bg=COLOR_CARD, bd=0, padx=15, pady=12)
        top_frame.pack(fill="x", padx=20, pady=5)

        tk.Label(top_frame, text="Монитор Доты:", font=("Segoe UI", 10), bg=COLOR_CARD, fg=COLOR_TEXT).grid(row=0, column=0, sticky="w", pady=5)
        
        # Кастомный темный Spinbox
        self.monitor_spin = tk.Spinbox(top_frame, from_=1, to=10, width=4, font=("Segoe UI", 10), bg=COLOR_BG, fg=COLOR_TEXT, bd=0, buttonbackground=COLOR_BTN_GRAY, insertbackground="white")
        self.monitor_spin.delete(0, "end")
        self.monitor_spin.insert(0, str(self.config["monitor"]))
        self.monitor_spin.grid(row=0, column=1, padx=8, sticky="w")

        # Чекбокс дебага
        self.preview_var = tk.IntVar(value=self.config["show_preview"])
        chk = tk.Checkbutton(top_frame, text="Превью дебага", variable=self.preview_var, font=("Segoe UI", 10), bg=COLOR_CARD, fg=COLOR_TEXT, activebackground=COLOR_CARD, activeforeground="white", selectcolor=COLOR_BG, bd=0)
        chk.grid(row=0, column=2, padx=20, sticky="e")

        # КНОПКИ УПРАВЛЕНИЯ
        btn_frame = tk.Frame(top_frame, bg=COLOR_CARD)
        btn_frame.grid(row=1, column=0, columnspan=3, pady=(10, 2))

        self.preview_btn = tk.Button(btn_frame, text="1. ТЕСТ РАМОК (БЕЗ КЛИКОВ)", bg=COLOR_BTN_GRAY, fg=COLOR_TEXT, font=("Segoe UI", 9, "bold"), width=23, bd=0, relief="flat", activebackground="#444444", activeforeground="white", command=self.start_preview)
        self.preview_btn.pack(side="left", padx=4, pady=2)

        self.start_btn = tk.Button(btn_frame, text="2. АВТОПИЛОТ", bg=COLOR_BTN_GREEN, fg=COLOR_TEXT, font=("Segoe UI", 9, "bold"), width=13, bd=0, relief="flat", activebackground="#259b47", activeforeground="white", command=self.start_bot)
        self.start_btn.pack(side="left", padx=4, pady=2)

        self.stop_btn = tk.Button(btn_frame, text="СТОП", bg=COLOR_BTN_RED, fg=COLOR_TEXT, font=("Segoe UI", 9, "bold"), width=9, bd=0, relief="flat", activebackground="#b80f1d", activeforeground="white", command=self.stop_all, state="disabled")
        self.stop_btn.pack(side="left", padx=4, pady=2)

        # ПАНЕЛЬ ГЕОМЕТРИИ ЗОН (Средняя карточка)
        geo_frame = tk.Frame(self.root, bg=COLOR_CARD, bd=0, padx=15, pady=10)
        geo_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(geo_frame, text="ГРАНИЦЫ ИГРОВОГО ПОЛЯ", font=("Segoe UI Variable", 9, "bold"), bg=COLOR_CARD, fg=COLOR_ACCENT).pack(anchor="w", pady=(0, 5))

        self.slider_left_x = self.create_ui_slider(geo_frame, "Левая граница поля X", self.config["left_x"])
        self.slider_right_x = self.create_ui_slider(geo_frame, "Правая граница поля X", self.config["right_x"])
        self.slider_top_y = self.create_ui_slider(geo_frame, "Верх поля (старт Сапога) Y", self.config["top_y"])
        self.slider_split_y = self.create_ui_slider(geo_frame, "РАЗДЕЛИТЕЛЬ (Сапог/Вагонетка) Y", self.config["split_y"])
        self.slider_bottom_y = self.create_slider_win11(geo_frame, "Низ поля (дно Вагонетки) Y", self.config["bottom_y"])

        # ПАНЕЛЬ НАСТРОЕК ДАТЧИКОВ (Нижняя карточка)
        sens_frame = tk.Frame(self.root, bg=COLOR_CARD, bd=0, padx=15, pady=10)
        sens_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(sens_frame, text="ЧУВСТВИТЕЛЬНОСТЬ И ТОЧНОСТЬ", font=("Segoe UI Variable", 9, "bold"), bg=COLOR_CARD, fg=COLOR_ACCENT).pack(anchor="w", pady=(0, 5))

        self.slider_thresh = self.create_ui_slider(sens_frame, "Порог изменения движения", self.config["motion_thresh"])
        self.slider_area = self.create_ui_slider(sens_frame, "Минимальный размер сапога", self.config["min_area"], max_val=2000)
        self.slider_deadzone = self.create_slider_win11(sens_frame, "Мертвая зона торможения (пикс)", self.config["deadzone"], max_val=100)

        # КНОПКА СОХРАНЕНИЯ Настроек
        save_btn = tk.Button(self.root, text="СОХРАНИТЬ КОНФИГУРАЦИЮ", bg=COLOR_BTN_GRAY, fg=COLOR_TEXT, font=("Segoe UI", 9, "bold"), height=2, bd=0, relief="flat", activebackground="#444444", activeforeground="white", command=self.save_config)
        save_btn.pack(fill="x", padx=20, pady=(12, 5))

        # СТИЛЬНЫЙ СТАТУС-БАР В НИЗУ
        self.status_label = tk.Label(self.root, text="Система готова к работе", font=("Segoe UI", 10, "italic"), bg=COLOR_BG, fg=COLOR_TEXT_MUTED)
        self.status_label.pack(pady=5)

    # Метод обертка для сохранения единого стиля верстки
    def create_ui_slider(self, parent, label_text, default_val, max_val=100):
        return self.create_slider_win11(parent, label_text, default_val, max_val)

    # КРАСИВЫЙ СЛАЙДЕР В СТИЛЕ WINDOWS 11 С КНОПКАМИ-СТРЕЛКАМИ
    def create_slider_win11(self, parent, label_text, default_val, max_val=100):
        frame = tk.Frame(parent, bg=COLOR_CARD)
        frame.pack(fill="x", pady=4)
        
        # Текстовая метка слева
        tk.Label(frame, text=label_text, font=("Segoe UI", 9), bg=COLOR_CARD, fg=COLOR_TEXT, width=28, anchor="w").pack(side="left")
        
        control_frame = tk.Frame(frame, bg=COLOR_CARD)
        control_frame.pack(side="right")
        
        # Стилизованный ползунок
        slider = tk.Scale(control_frame, from_=0, to=max_val, orient="horizontal", length=110, showvalue=True, bg=COLOR_CARD, fg=COLOR_TEXT, troughcolor=COLOR_BG, highlightthickness=0, bd=0, font=("Segoe UI", 8))
        slider.set(default_val)
        
        # Плоские минималистичные кнопки-стрелочки
        btn_minus = tk.Button(control_frame, text="◀", font=("Segoe UI", 7), width=2, bg=COLOR_BTN_GRAY, fg=COLOR_TEXT, bd=0, relief="flat", activebackground="#444444", activeforeground="white", command=lambda: slider.set(slider.get() - 1))
        btn_plus = tk.Button(control_frame, text="▶", font=("Segoe UI", 7), width=2, bg=COLOR_BTN_GRAY, fg=COLOR_TEXT, bd=0, relief="flat", activebackground="#444444", activeforeground="white", command=lambda: slider.set(slider.get() + 1))
        
        btn_minus.pack(side="left", padx=4)
        slider.pack(side="left", padx=2)
        btn_plus.pack(side="left", padx=4)
        return slider

    def set_key(self, key):
        if self.current_key == key:
            return
        if self.current_key == 'a' and key != 'a': pydirectinput.keyUp('a')
        if self.current_key == 'd' and key != 'd': pydirectinput.keyUp('d')
        if key == 'a': pydirectinput.keyDown('a')
        elif key == 'd': pydirectinput.keyDown('d')
        self.current_key = key

    def start_preview(self):
        self.is_running = True
        self.is_bot_active = False
        self.preview_btn.config(state="disabled", bg="#252525")
        self.start_btn.config(state="normal", bg=COLOR_BTN_GREEN)
        self.stop_btn.config(state="normal", bg=COLOR_BTN_RED)
        self.status_label.config(text="Режим калибровки: Кнопки управления отключены", fg=COLOR_ACCENT)

    def start_bot(self):
        self.is_running = True
        self.is_bot_active = True
        self.preview_btn.config(state="disabled", bg="#252525")
        self.start_btn.config(state="disabled", bg="#252525")
        self.stop_btn.config(state="normal", bg=COLOR_BTN_RED)
        self.status_label.config(text="Автопилот запущен! Бот управляет игрой.", fg=COLOR_BTN_GREEN)
        
        if not self.space_thread or not self.space_thread.is_alive():
            self.space_thread = threading.Thread(target=self.isolated_space_loop, daemon=True)
            self.space_thread.start()

    def stop_all(self):
        self.is_running = False
        self.is_bot_active = False
        self.set_key(None)
        cv2.destroyAllWindows()
        self.preview_btn.config(state="normal", bg=COLOR_BTN_GRAY)
        self.start_btn.config(state="normal", bg=COLOR_BTN_GREEN)
        self.stop_btn.config(state="disabled", bg="#252525")
        self.status_label.config(text="Работа бота полностью остановлена", fg="#ff9999")

    def isolated_space_loop(self):
        while self.is_running:
            if self.is_bot_active:
                pydirectinput.keyDown('space')
                time.sleep(0.05)
                pydirectinput.keyUp('space')
                time.sleep(0.15)
                pydirectinput.keyDown('space')
                time.sleep(0.05)
                pydirectinput.keyUp('space')
            time.sleep(3.0)

    def master_tick(self):
        if self.is_running:
            try:
                target_monitor = int(self.monitor_spin.get())
                monitor_screen = self.sct.monitors[target_monitor]
                scr_w, scr_h = monitor_screen["width"], monitor_screen["height"]
                scr_left, scr_top = monitor_screen["left"], monitor_screen["top"]

                lx_p, rx_p = self.slider_left_x.get() / 100.0, self.slider_right_x.get() / 100.0
                ty_p, sy_p, by_p = self.slider_top_y.get() / 100.0, self.slider_split_y.get() / 100.0, self.slider_bottom_y.get() / 100.0
                motion_thresh, min_area, deadzone = self.slider_thresh.get(), self.slider_area.get(), self.slider_deadzone.get()
                show_preview = self.preview_var.get()

                box_left = int(scr_w * lx_p)
                box_right = int(scr_w * rx_p)
                box_top = int(scr_h * ty_p)
                box_bottom = int(scr_h * by_p)
                box_w, box_h = box_right - box_left, box_bottom - box_top

                if box_w > 10 and box_h > 10:
                    crop_monitor = {"top": box_top + scr_top, "left": box_left + scr_left, "width": box_w, "height": box_h}
                    crop_img = np.array(self.sct.grab(crop_monitor))
                    
                    gray = cv2.cvtColor(crop_img, cv2.COLOR_BGRA2GRAY)
                    split_y_rel = max(1, min(int(scr_h * sy_p) - box_top, box_h - 1))

                    # 1. Поиск Сапога
                    gray_zone = gray[0:split_y_rel, 0:box_w]
                    boot_x, boot_y = None, None
                    if self.prev_gray_zone is not None and self.prev_gray_zone.shape == gray_zone.shape:
                        frame_diff = cv2.absdiff(gray_zone, self.prev_gray_zone)
                        _, thresh = cv2.threshold(frame_diff, motion_thresh, 255, cv2.THRESH_BINARY)
                        thresh = cv2.dilate(thresh, None, iterations=2)
                        contours_boot, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        
                        max_boot_area = 0
                        for c in contours_boot:
                            area = cv2.contourArea(c)
                            if area > min_area and area > max_boot_area:
                                max_boot_area = area
                                M = cv2.moments(c)
                                if M["m00"] > 0:
                                    boot_x = int(M["m10"] / M["m00"])
                                    boot_y = int(M["m01"] / M["m00"])
                    self.prev_gray_zone = gray_zone

                    # 2. Поиск Вагонетки
                    wagon_zone_img = crop_img[split_y_rel:box_h, 0:box_w]
                    wagon_zone_bgr = cv2.cvtColor(wagon_zone_img, cv2.COLOR_BGRA2BGR)
                    hsv_wagon = cv2.cvtColor(wagon_zone_bgr, cv2.COLOR_BGR2HSV)
                    mask_red = cv2.inRange(hsv_wagon, LOWER_RED1, UPPER_RED1) + cv2.inRange(hsv_wagon, LOWER_RED2, UPPER_RED2)
                    contours_red, _ = cv2.findContours(mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    wagon_x, wagon_y = None, None
                    max_wagon_area = 0
                    for c in contours_red:
                        area = cv2.contourArea(c)
                        if area > 100 and area > max_wagon_area:
                            max_wagon_area = area
                            M = cv2.moments(c)
                            if M["m00"] > 0:
                                wagon_x = int(M["m10"] / M["m00"])
                                wagon_y = int(M["m01"] / M["m00"]) + split_y_rel

                    # 3. Управление
                    if self.is_bot_active and boot_x is not None and wagon_x is not None:
                        if boot_x < wagon_x - deadzone: self.set_key('a')
                        elif boot_x > wagon_x + deadzone: self.set_key('d')
                        else: self.set_key(None)
                    else:
                        if not self.is_bot_active: self.set_key(None)

                    # 4. Превью дебага
                    if show_preview:
                        debug_img = cv2.cvtColor(crop_img, cv2.COLOR_BGRA2BGR)
                        cv2.rectangle(debug_img, (0, 0), (box_w, split_y_rel), (255, 0, 255), 2)
                        cv2.rectangle(debug_img, (0, split_y_rel), (box_w, box_h), (0, 255, 255), 2)
                        if boot_x is not None: cv2.circle(debug_img, (boot_x, boot_y), 15, (0, 255, 0), 2)
                        if wagon_x is not None: cv2.circle(debug_img, (wagon_x, wagon_y), 20, (0, 0, 255), 2)
                        if boot_x is not None and wagon_x is not None:
                            cv2.line(debug_img, (boot_x, boot_y), (wagon_x, wagon_y), (0, 255, 255), 2)

                        preview_w = 400
                        scale = preview_w / box_w
                        preview_h = int(box_h * scale)
                        resized = cv2.resize(debug_img, (preview_w, preview_h))
                        cv2.imshow("LIVE DEBUG VIEW", resized)
                        cv2.waitKey(1)
                    else:
                        cv2.destroyAllWindows()

            except Exception as e:
                print(f"Ошибка: {e}")

        self.root.after(1, self.master_tick)

if __name__ == "__main__":
    import ctypes
    import sys

    # ТРЮК №1: Говорим Windows 11, что это уникальное приложение, 
    # а не стандартный скрипт Python. Тогда она привяжет иконку к панели задач.
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("dota2.arkanoid.bot.v7")
    except Exception:
        pass

    root = tk.Tk()
    
    # ТРЮК №2: Заставляем само окно использовать иконку.
    # sys.executable автоматически вытащит иконку прямо из твоего собранного .exe файла!
    try:
        root.iconbitmap(default=sys.executable)
    except Exception:
        # Если запускаешь просто как .py и файл иконки лежит рядом
        if os.path.exists("icon.ico"):
            root.iconbitmap(default="icon.ico")
            
    app = DotaBotApp(root)
    root.mainloop()