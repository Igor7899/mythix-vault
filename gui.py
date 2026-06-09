import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from plyer import notification
from services import AuthService, NoteService

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class AuthWindow(ctk.CTk):
    """Вікно авторизації (Без змін)."""
    def __init__(self):
        super().__init__()
        self.title("Mythix Vault - Авторизація")
        self.geometry("400x500")
        self.resizable(False, False)
        self.auth_service = AuthService()
        self.authenticated_user_id = None
        self.setup_ui()

    def setup_ui(self):
        self.frame = ctk.CTkFrame(self, corner_radius=15)
        self.frame.pack(pady=40, padx=40, fill="both", expand=True)

        ctk.CTkLabel(self.frame, text="Вхід у систему", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(30, 20))
        self.entry_username = ctk.CTkEntry(self.frame, placeholder_text="Логін", width=200)
        self.entry_username.pack(pady=10)
        self.entry_password = ctk.CTkEntry(self.frame, placeholder_text="Пароль", show="*", width=200)
        self.entry_password.pack(pady=10)

        ctk.CTkButton(self.frame, text="Увійти", command=self.login, width=200).pack(pady=(20, 10))
        ctk.CTkButton(self.frame, text="Зареєструватися", command=self.register, 
                      width=200, fg_color="transparent", border_width=1).pack(pady=10)

    def login(self):
        # .strip() видаляє випадкові пробіли, які користувач міг поставити випадково
        username = self.entry_username.get().strip()
        password = self.entry_password.get().strip()

        if not username or not password:
            messagebox.showwarning("Увага", "Будь ласка, введіть логін та пароль!")
            return

        success, msg, user = self.auth_service.login_user(username, password)
        if success:
            self.authenticated_user_id = user.id
            self.destroy()
        else:
            messagebox.showerror("Помилка", msg)

    def register(self):
        username = self.entry_username.get().strip()
        password = self.entry_password.get().strip()

        # Жорстка перевірка на порожні поля та довжину (Захист від дурня)
        if len(username) < 3:
            messagebox.showwarning("Увага", "Логін має містити мінімум 3 символи!")
            return
        if len(password) < 4:
            messagebox.showwarning("Увага", "Пароль має містити мінімум 4 символи!")
            return

        success, msg = self.auth_service.register_user(username, password)
        if success:
            messagebox.showinfo("Успіх", msg)
        else:
            messagebox.showerror("Помилка", msg)


class MainWindow(ctk.CTk):
    """Головне вікно із системою тегів, дедлайнами, кошиком та ФІЛЬТРАЦІЄЮ."""
    def __init__(self, user_id):
        super().__init__()
        self.title("Mythix Vault - Захищений Нотатник")
        self.geometry("1200x700")
        
        self.note_service = NoteService(user_id)
        self.current_note_id = None
        self.current_tab = "Активні"
        
        # Сет для збереження ID нотаток, про які вже було повідомлено (щоб не спамити)
        self.notified_alerts = set()
        
        self.setup_ui()
        self.refresh_list()
        
        # Запускаємо фонову перевірку дедлайнів (Уведомления)
        self.check_notifications()

    def setup_ui(self):
        # --- ЛІВА ПАНЕЛЬ ---
        self.sidebar_frame = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)

        ctk.CTkLabel(self.sidebar_frame, text="Mythix Vault", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=15)

        self.btn_add = ctk.CTkButton(self.sidebar_frame, text="+ Створити нотатку", command=self.add_note_click, fg_color="#2ecc71", hover_color="#27ae60")
        self.btn_add.pack(pady=5, padx=20, fill="x")

        self.tab_switch = ctk.CTkSegmentedButton(self.sidebar_frame, values=["Активні", "Кошик"], command=self.switch_tab)
        self.tab_switch.pack(pady=10, padx=20, fill="x")
        self.tab_switch.set("Активні")

        # --- НОВИЙ ЕЛЕМЕНТ: ФІЛЬТР ТЕГІВ ---
        self.filter_var = ctk.StringVar(value="Всі теги")
        self.cb_filter = ctk.CTkOptionMenu(self.sidebar_frame, variable=self.filter_var, command=self.on_filter_change)
        self.cb_filter.pack(pady=(0, 10), padx=20, fill="x")

        self.scrollable_notes_frame = ctk.CTkScrollableFrame(self.sidebar_frame)
        self.scrollable_notes_frame.pack(pady=10, padx=10, fill="both", expand=True)

        # --- ПРАВА ПАНЕЛЬ ---
        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        self.toolbar = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.toolbar.pack(fill="x", pady=10, padx=20)

        self.btn_save = ctk.CTkButton(self.toolbar, text="💾 Зберегти", command=self.save_click, width=120)
        self.btn_save.pack(side="left")
        
        self.btn_restore = ctk.CTkButton(self.toolbar, text="♻️ Відновити", command=self.restore_click, width=120, fg_color="#f39c12", hover_color="#d68910")
        
        self.btn_trash = ctk.CTkButton(self.toolbar, text="🗑 У кошик", command=self.trash_click, width=120, fg_color="#e74c3c", hover_color="#c0392b")
        self.btn_trash.pack(side="right")
        
        self.btn_hard_delete = ctk.CTkButton(self.toolbar, text="💀 Знищити", command=self.hard_delete_click, width=120, fg_color="#8e44ad", hover_color="#732d91")

        self.settings_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.settings_frame.pack(fill="x", padx=20, pady=5)

        row1 = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        self.entry_title = ctk.CTkEntry(row1, font=ctk.CTkFont(size=18, weight="bold"), placeholder_text="Заголовок нотатки...")
        self.entry_title.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.switch_pin = ctk.CTkSwitch(row1, text="📌 Закріпити", command=self.save_click)
        self.switch_pin.pack(side="right")

        row2 = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        
        ctk.CTkLabel(row2, text="Теги (через кому):").pack(side="left", padx=(0, 5))
        self.entry_tags = ctk.CTkEntry(row2, placeholder_text="Наприклад: Навчання, Важливо", width=250)
        self.entry_tags.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(row2, text="Дедлайн:").pack(side="left", padx=(0, 5))
        self.entry_date = ctk.CTkEntry(row2, placeholder_text="ДД.ММ.РРРР ГГ:ХХ", width=150)
        self.entry_date.pack(side="left")
        
        self.lbl_timer = ctk.CTkLabel(row2, text="", font=ctk.CTkFont(weight="bold"))
        self.lbl_timer.pack(side="right")

        self.textbox = ctk.CTkTextbox(self.main_frame, font=ctk.CTkFont(family="Consolas", size=14))
        self.textbox.pack(fill="both", expand=True, padx=20, pady=10)

        self.toggle_editor_state(False, clear=True)

    # --- ЛОГІКА ІНТЕРФЕЙСУ ---

    def on_filter_change(self, choice):
        """Метод, який викликається при виборі тегу з випадаючого списку"""
        self.toggle_editor_state(False, clear=True)
        self.current_note_id = None
        self.refresh_list()

    def switch_tab(self, value):
        self.current_tab = value
        self.current_note_id = None
        
        # При переході між активними і кошиком скидаємо фільтр на "Всі теги"
        self.filter_var.set("Всі теги") 
        self.toggle_editor_state(False, clear=True)
        self.refresh_list()
        
        if value == "Активні":
            self.btn_restore.pack_forget()
            self.btn_hard_delete.pack_forget()
            self.cb_filter.configure(state="normal") # Дозволяємо фільтр
            self.btn_save.pack(side="left")
            self.btn_trash.pack(side="right")
            self.btn_add.configure(state="normal")
        else:
            self.btn_save.pack_forget()
            self.btn_trash.pack_forget()
            self.cb_filter.configure(state="disabled") # У кошику фільтр вимикаємо
            self.btn_restore.pack(side="left")
            self.btn_hard_delete.pack(side="right")
            self.btn_add.configure(state="disabled")

    def toggle_editor_state(self, active, clear=False):
        self.entry_title.configure(state="normal")
        self.entry_tags.configure(state="normal")
        self.entry_date.configure(state="normal")
        self.textbox.configure(state="normal")
        self.switch_pin.configure(state="normal")
        
        if clear:
            self.entry_title.delete(0, "end")
            self.entry_tags.delete(0, "end")
            self.entry_date.delete(0, "end")
            self.textbox.delete("1.0", "end")
            self.lbl_timer.configure(text="")
            self.switch_pin.deselect()

        final_state = "normal" if active else "disabled"
        self.entry_title.configure(state=final_state)
        self.entry_tags.configure(state=final_state)
        self.entry_date.configure(state=final_state)
        self.switch_pin.configure(state=final_state)
        self.textbox.configure(state=final_state)

    def refresh_list(self):
        # 1. Оновлюємо випадаючий список фільтрів динамічно
        if self.current_tab == "Активні":
            unique_tags = self.note_service.get_all_unique_tags()
            filter_options = ["Всі теги"] + unique_tags
            self.cb_filter.configure(values=filter_options)
            
            # Якщо обраний тег видалили, повертаємось на "Всі теги"
            if self.filter_var.get() not in filter_options:
                self.filter_var.set("Всі теги")

        # 2. Очищуємо старі кнопки
        for widget in self.scrollable_notes_frame.winfo_children():
            widget.destroy()

        # 3. Витягуємо нотатки з БД із врахуванням фільтра
        is_trash = (self.current_tab == "Кошик")
        selected_filter = self.filter_var.get() if not is_trash else "Всі теги"
        notes = self.note_service.get_all_notes(is_trash=is_trash, tag_filter=selected_filter)
        
        for note in notes:
            text_color = "gray80"
            if note["urgency_status"] == "expired":
                text_color = "#e74c3c"
            elif note["urgency_status"] == "warning":
                text_color = "#f1c40f"
            elif note["urgency_status"] == "normal" and note["due_date_str"]:
                text_color = "#2ecc71"

            pin_icon = "📌 " if note["is_pinned"] else ""
            btn_text = f"{pin_icon}{note['title']}\n[{note['tags']}]"
            if note["time_left"]:
                btn_text += f"\n⏳ {note['time_left']}"
            
            btn = ctk.CTkButton(
                self.scrollable_notes_frame, text=btn_text, 
                fg_color="transparent", text_color=text_color, 
                border_width=1, border_color="#333333", anchor="w",
                command=lambda n=note: self.load_note_into_editor(n)
            )
            btn.pack(pady=5, padx=5, fill="x")

    def load_note_into_editor(self, note_dict):
        self.toggle_editor_state(True, clear=True) 
        
        self.current_note_id = note_dict["id"]
        self.entry_title.insert(0, note_dict["title"])
        self.entry_tags.insert(0, note_dict["tags"])
        self.entry_date.insert(0, note_dict["due_date_str"])
        self.switch_pin.select() if note_dict["is_pinned"] else self.switch_pin.deselect()
        self.textbox.insert("1.0", note_dict["content"])
        
        if note_dict["time_left"]:
            self.lbl_timer.configure(text=f"⏳ {note_dict['time_left']}")
            if note_dict["urgency_status"] == "expired":
                self.lbl_timer.configure(text_color="#e74c3c")
            elif note_dict["urgency_status"] == "warning":
                self.lbl_timer.configure(text_color="#f1c40f")
            else:
                self.lbl_timer.configure(text_color="#2ecc71")

        if self.current_tab == "Кошик":
            self.toggle_editor_state(False, clear=False) 

    def add_note_click(self):
        self.toggle_editor_state(True, clear=True)
        self.current_note_id = None
        self.entry_title.insert(0, "Нова нотатка")

    def parse_date(self, date_str):
        if not date_str.strip():
            return None
        try:
            return datetime.strptime(date_str.strip(), "%d.%m.%Y %H:%M")
        except ValueError:
            return False

    def save_click(self):
        if self.entry_title.cget("state") == "disabled":
            return
            
        title = self.entry_title.get()
        tags = self.entry_tags.get()
        content = self.textbox.get("1.0", "end").strip()
        is_pinned = self.switch_pin.get() == 1
        
        due_date = self.parse_date(self.entry_date.get())
        if due_date is False:
            messagebox.showerror("Помилка дати", "Введіть дату у форматі: ДД.ММ.РРРР ГГ:ХХ\nАбо залиште поле порожнім.")
            return
        
        success = self.note_service.add_or_update_note(self.current_note_id, title, tags, content, is_pinned, due_date)
        if success:
            self.refresh_list()
        else:
            messagebox.showerror("Помилка", "Не вдалося зберегти нотатку.")

    def trash_click(self):
        if self.current_note_id and messagebox.askyesno("У кошик", "Перемістити нотатку в кошик?"):
            if self.note_service.move_to_trash(self.current_note_id):
                self.toggle_editor_state(False, clear=True)
                self.current_note_id = None
                self.refresh_list()

    def restore_click(self):
        if self.current_note_id:
            if self.note_service.restore_note(self.current_note_id):
                self.toggle_editor_state(False, clear=True)
                self.current_note_id = None
                self.refresh_list()
                messagebox.showinfo("Успіх", "Нотатку успішно відновлено!")

    def hard_delete_click(self):
        if self.current_note_id and messagebox.askyesno("Знищення", "Видалити назавжди? Цю дію неможливо скасувати!"):
            if self.note_service.hard_delete(self.current_note_id):
                self.toggle_editor_state(False, clear=True)
                self.current_note_id = None
                self.refresh_list()
    
    def check_notifications(self):
        """Фоновий процес для перевірки дедлайнів та відправки Push-повідомлень Windows"""
        if self.current_tab == "Активні":
            notes = self.note_service.get_all_notes(is_trash=False)
            for note in notes:
                if note["due_date_raw"]:
                    delta = note["due_date_raw"] - datetime.now()
                    days_left = delta.total_seconds() / 86400 # Переводимо секунди в дні
                    
                    alert_type = None
                    # Якщо залишилось менше 1 дня (але час ще не вийшов)
                    if 0 < days_left <= 1.0:
                        alert_type = "1_day"
                    # Якщо залишилось від 1 до 3 днів
                    elif 1.0 < days_left <= 3.0:
                        alert_type = "3_days"
                        
                    if alert_type:
                        # Створюємо унікальний ключ, щоб не показувати одне й те саме повідомлення двічі за сесію
                        alert_key = f"{note['id']}_{alert_type}"
                        if alert_key not in self.notified_alerts:
                            try:
                                notification.notify(
                                    title="⏳ Дедлайн близько!",
                                    message=f"Нотатка: {note['title']}\nЧас закінчення: {note['due_date_str']}",
                                    app_name="Mythix Vault",
                                    app_icon=None, 
                                    timeout=10
                                )
                                self.notified_alerts.add(alert_key)
                            except Exception as e:
                                print(f"Помилка повідомлення: {e}")
        
        # Зациклюємо перевірку: метод викликатиме сам себе кожні 10 хвилин (600000 мілісекунд)
        self.after(600000, self.check_notifications)