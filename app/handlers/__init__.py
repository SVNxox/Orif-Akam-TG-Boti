from aiogram import Router
from .form import form_router
from .sync import sync_router

router = Router()
router.include_router(form_router)
router.include_router(sync_router)