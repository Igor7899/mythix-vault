import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()

# ==========================================
# ПРОМІЖНА ТАБЛИЦЯ ДЛЯ ТЕГІВ (Багато-до-багатьох)
# ==========================================
note_tags_association = Table(
    'note_tags',
    Base.metadata,
    Column('note_id', String, ForeignKey('notes.id'), primary_key=True),
    Column('tag_id', String, ForeignKey('tags.id'), primary_key=True)
)

# ==========================================
# 1. МОДЕЛЬ КОРИСТУВАЧА
# ==========================================
class User(Base):
    __tablename__ = 'users'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    notes = relationship("Note", back_populates="owner", cascade="all, delete-orphan")

# ==========================================
# 2. МОДЕЛЬ ТЕГУ (Нова фіча)
# ==========================================
class Tag(Base):
    __tablename__ = 'tags'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(30), unique=True, nullable=False)
    
    # Зворотний зв'язок з нотатками
    notes = relationship("Note", secondary=note_tags_association, back_populates="tags")

# ==========================================
# 3. МОДЕЛЬ НОТАТКИ (Оновлена)
# ==========================================
class Note(Base):
    __tablename__ = 'notes'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    
    title = Column(String(100), nullable=False)
    encrypted_content = Column(Text, nullable=False) 
    
    # --- НОВІ ПОЛЯ ---
    due_date = Column(DateTime, nullable=True)       # Дедлайн (може бути порожнім, якщо таймер не потрібен)
    is_deleted = Column(Boolean, default=False)      # М'яке видалення (Корзина)
    # -----------------
    
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    owner = relationship("User", back_populates="notes")
    tags = relationship("Tag", secondary=note_tags_association, back_populates="notes")

# ==========================================
# ПАТЕРН SINGLETON ДЛЯ РОБОТИ З БД
# ==========================================
class DatabaseManager:
    _instance = None

    def __new__(cls, db_name="mythix_vault.db"):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.engine = create_engine(f'sqlite:///{db_name}', echo=False)
            Base.metadata.create_all(cls._instance.engine)
            cls._instance.Session = sessionmaker(bind=cls._instance.engine)
        return cls._instance

    def get_session(self):
        return self.Session()