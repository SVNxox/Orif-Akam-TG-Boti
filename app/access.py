import json
import os
from typing import Dict, Optional

ALLOWED_FILE = "allowed_users.json"


def _load() -> Dict[int, str]:
    """
    Загружает ID и имена из файла. 
    Автоматически конвертирует старый формат списка в новый формат словаря.
    """
    if os.path.exists(ALLOWED_FILE):
        try:
            with open(ALLOWED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

                # Поддержка старого формата (если users был списком ID)
                if isinstance(data.get("users"), list):
                    return {int(uid): "" for uid in data["users"] if str(uid).strip().isdigit()}

                # Новый формат (если users — это словарь {ID: Имя})
                if isinstance(data.get("users"), dict):
                    return {int(uid): str(name) for uid, name in data["users"].items() if str(uid).strip().isdigit()}
        except Exception:
            pass
    return {}


def _save(users: Dict[int, str]):
    """Сохраняет словарь пользователей в JSON, сортируя по ID."""
    # Сортируем по ID для красивого порядка в файле
    sorted_users = {str(k): users[k] for k in sorted(users.keys())}
    with open(ALLOWED_FILE, "w", encoding="utf-8") as f:
        json.dump({"users": sorted_users}, f, indent=2, ensure_ascii=False)


def is_allowed_user(user_id: int) -> bool:
    """Проверяет доступ (работает так же, как раньше)."""
    allowed = _load()
    return user_id in allowed


def add_user(user_id: int, name: str = "") -> bool:
    """Добавляет пользователя. Если он есть — обновляет имя."""
    users = _load()

    # Если пользователь уже есть И имя совпадает, ничего не меняем
    if user_id in users and users[user_id] == name:
        return False

    users[user_id] = name
    _save(users)
    return True


def remove_user(user_id: int) -> bool:
    """Удаляет пользователя по ID."""
    users = _load()
    if user_id not in users:
        return False
    users.pop(user_id, None)
    _save(users)
    return True


def get_all_users() -> Dict[int, str]:
    """Возвращает всех пользователей для команды /azolar."""
    return _load()
