# app/handlers/__init__.py
from aiogram import Router
from aiogram.fsm.context import FSMContext  # ← Если ещё не добавлен

from .form import form_router
from .sync import router as sync_router  # ← Импортируем как sync_router

main_router = Router()
main_router.include_router(form_router)
main_router.include_router(sync_router)  # ← Подключаем

router = main_router  # ← Экспортируем как router