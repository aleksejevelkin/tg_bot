from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

class KeyboardManager:
    @staticmethod
    def get_main_keyboard():
        buttons = [
            [KeyboardButton(text="Погода сегодня")],
            [KeyboardButton(text="Погода завтра")],
            [KeyboardButton(text="⚙️ Настройки")]
        ]
        return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True) 