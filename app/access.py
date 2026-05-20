# app/access.py
import json
import os
from typing import Set

ALLOWED_FILE = "allowed_users.json"

def _load() -> Set[int]:
    """Загружает ID из файла. Если файла нет — возвращает пустое множество."""
    if os.path.exists(ALLOWED_FILE):
        try:
            with open(ALLOWED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(int(uid) for uid in data.get("users", []) if str(uid).strip().isdigit())
        except Exception:
            pass
    return set()

def _save(users: Set[int]):
    """Сохраняет множество ID в JSON."""
    with open(ALLOWED_FILE, "w", encoding="utf-8") as f:
        json.dump({"users": sorted(list(users))}, f, indent=2)

def is_allowed_user(user_id: int) -> bool:
    """
    Проверяет доступ.
    • Если список пуст → разрешено ВСЕМ (режим разработки)
    • Если в списке есть хотя бы 1 ID → доступ только им (режим продакшена)
    """
    allowed = _load()
    # return len(allowed) == 0 or user_id in allowed
    return user_id in allowed

def add_user(user_id: int) -> bool:
    users = _load()
    if user_id in users:
        return False
    users.add(user_id)
    _save(users)
    return True

def remove_user(user_id: int) -> bool:
    users = _load()
    if user_id not in users:
        return False
    users.discard(user_id)
    _save(users)
    return True