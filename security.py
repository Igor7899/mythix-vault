import hashlib
import hmac  # <-- Добавили правильный модуль
import os
import base64
from cryptography.fernet import Fernet
from tkinter import messagebox

class SecurityManager:
    _FERNET_KEY = base64.urlsafe_b64encode(b'MythixVault_Diploma_Key_32_bytes')
    _cipher_suite = Fernet(_FERNET_KEY)

    @staticmethod
    def hash_password(password: str) -> str:
        """Створює криптографічний хеш пароля."""
        salt = os.urandom(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return salt.hex() + ":" + pwd_hash.hex()

    @staticmethod
    def verify_password(stored_hash: str, provided_password: str) -> bool:
        """Перевіряє, чи співпадає введений пароль зі збереженим хешем."""
        try:
            salt_hex, hash_hex = stored_hash.split(":")
            salt = bytes.fromhex(salt_hex)
            stored_pwd_hash = bytes.fromhex(hash_hex)
            
            pwd_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
            
            # ИСПРАВЛЕНО: используем hmac.compare_digest вместо hashlib
            return hmac.compare_digest(pwd_hash, stored_pwd_hash)
        except Exception as e:
            messagebox.showerror("Системна помилка", f"Помилка читання пароля!\n\nДеталі: {e}")
            return False

    @classmethod
    def encrypt_text(cls, plain_text: str) -> str:
        if not plain_text:
            return ""
        encrypted_bytes = cls._cipher_suite.encrypt(plain_text.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')

    @classmethod
    def decrypt_text(cls, encrypted_text: str) -> str:
        if not encrypted_text:
            return ""
        try:
            decrypted_bytes = cls._cipher_suite.decrypt(encrypted_text.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception:
            return "[ПОМИЛКА РОЗШИФРУВАННЯ: Дані пошкоджено або ключ невірний]"