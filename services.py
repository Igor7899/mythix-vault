from database import DatabaseManager, User, Note, Tag
from security import SecurityManager
from datetime import datetime

class AuthService:
    """Сервіс для реєстрації та авторизації користувачів (Без змін)."""
    
    def __init__(self):
        self.db = DatabaseManager()

    def register_user(self, username, password) -> tuple[bool, str]:
        session = self.db.get_session()
        try:
            existing_user = session.query(User).filter_by(username=username).first()
            if existing_user:
                return False, "Користувач з таким ім'ям вже існує."

            hashed_pw = SecurityManager.hash_password(password)
            new_user = User(username=username, password_hash=hashed_pw)
            
            session.add(new_user)
            session.commit()
            return True, "Реєстрація успішна!"
        except Exception as e:
            session.rollback()
            return False, f"Помилка БД: {str(e)}"
        finally:
            session.close()

    def login_user(self, username, password) -> tuple[bool, str, User]:
        session = self.db.get_session()
        try:
            user = session.query(User).filter_by(username=username).first()
            if not user or not SecurityManager.verify_password(user.password_hash, password):
                return False, "Невірний логін або пароль.", None
            return True, "Вхід успішний!", user
        finally:
            session.close()


class NoteService:
    """Оновлений сервіс для управління нотатками (З фільтрацією тегів)."""
    
    def __init__(self, user_id):
        self.db = DatabaseManager()
        self.user_id = user_id

    def get_all_unique_tags(self):
        """Збирає всі унікальні теги, які використовує поточний користувач."""
        session = self.db.get_session()
        try:
            notes = session.query(Note).filter_by(user_id=self.user_id, is_deleted=False).all()
            tags = set()
            for n in notes:
                for t in n.tags:
                    tags.add(t.name)
            return sorted(list(tags))
        finally:
            session.close()

    def get_all_notes(self, is_trash=False, tag_filter="Всі теги"):
        """Отримує нотатки з можливістю фільтрації за конкретним тегом."""
        session = self.db.get_session()
        try:
            # Базовий запит (тільки нотатки юзера і перевірка на кошик)
            query = session.query(Note).filter_by(user_id=self.user_id, is_deleted=is_trash)
            
            # МАГІЯ SQLALCHEMY: Фільтруємо за тегом, якщо він вказаний
            if tag_filter and tag_filter != "Всі теги":
                # Шукаємо тільки ті нотатки, у яких в списку тегів є потрібне ім'я
                query = query.filter(Note.tags.any(Tag.name == tag_filter))
                
            notes = query.all()
            
            result = []
            for n in notes:
                time_left_str = ""
                urgency_status = "normal" 
                
                if n.due_date:
                    delta = n.due_date - datetime.now()
                    if delta.total_seconds() < 0:
                        time_left_str = "Прострочено!"
                        urgency_status = "expired"
                    elif delta.days == 0:
                        hours = int(delta.total_seconds() // 3600)
                        time_left_str = f"Залишилося годин: {hours}"
                        urgency_status = "warning"
                    else:
                        time_left_str = f"Залишилося днів: {delta.days}"

                tags_list = [t.name for t in n.tags]
                tags_str = ", ".join(tags_list) if tags_list else "Без тегів"

                result.append({
                    "id": n.id,
                    "title": n.title,
                    "tags": tags_str,
                    "content": SecurityManager.decrypt_text(n.encrypted_content),
                    "is_pinned": n.is_pinned,
                    "created_at": n.created_at.strftime("%d.%m.%Y %H:%M"),
                    "due_date_raw": n.due_date,
                    "due_date_str": n.due_date.strftime("%d.%m.%Y %H:%M") if n.due_date else "",
                    "time_left": time_left_str,
                    "urgency_status": urgency_status
                })
            
            # Розумне сортування: Дедлайни -> Закріплені -> Найновіші
            result.sort(key=lambda x: (
                x["due_date_raw"] is None,          # 1. Спочатку ті, що МАЮТЬ дедлайн (False йде перед True)
                x["due_date_raw"] or datetime.max,  # 2. Чим ближче дедлайн, тим вище в списку
                not x["is_pinned"],                 # 3. Потім закріплені нотатки
                x["created_at"]                     # 4. В кінці сортуємо за часом створення
            ), reverse=False)
            
            return result
        finally:
            session.close()

    def add_or_update_note(self, note_id, title, tags_input, content, is_pinned, due_date=None):
        session = self.db.get_session()
        try:
            encrypted_text = SecurityManager.encrypt_text(content)
            
            tags_list = []
            if tags_input:
                tag_names = [t.strip() for t in tags_input.split(",") if t.strip()]
                for name in tag_names:
                    tag = session.query(Tag).filter_by(name=name).first()
                    if not tag:
                        tag = Tag(name=name)
                        session.add(tag)
                    tags_list.append(tag)

            if note_id:
                note = session.query(Note).filter_by(id=note_id, user_id=self.user_id).first()
                if note:
                    note.title = title
                    note.encrypted_content = encrypted_text
                    note.is_pinned = is_pinned
                    note.due_date = due_date
                    note.tags = tags_list 
            else:
                new_note = Note(user_id=self.user_id, title=title, encrypted_content=encrypted_text,
                                is_pinned=is_pinned, due_date=due_date, tags=tags_list)
                session.add(new_note)
            
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    def move_to_trash(self, note_id):
        session = self.db.get_session()
        try:
            note = session.query(Note).filter_by(id=note_id, user_id=self.user_id).first()
            if note:
                note.is_deleted = True
                note.is_pinned = False
                session.commit()
                return True
            return False
        finally:
            session.close()

    def restore_note(self, note_id):
        session = self.db.get_session()
        try:
            note = session.query(Note).filter_by(id=note_id, user_id=self.user_id).first()
            if note:
                note.is_deleted = False
                session.commit()
                return True
            return False
        finally:
            session.close()

    def hard_delete(self, note_id):
        session = self.db.get_session()
        try:
            note = session.query(Note).filter_by(id=note_id, user_id=self.user_id).first()
            if note:
                session.delete(note)
                session.commit()
                return True
            return False
        finally:
            session.close()