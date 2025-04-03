from aiogram import types
from keyboards import get_main_menu

async def start(message: types.Message):
    await message.reply("Добро пожаловать! Выберите действие:", reply_markup=get_main_menu(message.from_user.id))