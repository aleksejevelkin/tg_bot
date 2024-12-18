from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
import signal
import sys
from config import Config
from weather import WeatherService
from keyboard_manager import KeyboardManager

class UserState(StatesGroup):
    waiting_for_city = State()

class WeatherBot:
    def __init__(self):
        self.bot = Bot(token=Config.BOT_TOKEN)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        self.weather_service = WeatherService()
        self.keyboard_manager = KeyboardManager()
        self._register_handlers()
        self._setup_shutdown()

    def _register_handlers(self):
        self.dp.message.register(self.send_welcome, Command('start'))
        self.dp.message.register(self.settings_handler, F.text == "⚙️ Настройки")
        self.dp.message.register(self.process_city, StateFilter(UserState.waiting_for_city))
        self.dp.message.register(self.handle_weather, F.text.in_(["Погода сегодня", "Погода завтра"]))

    async def _close(self):
        """Закрытие всех соединений"""
        print("Закрытие соединений...")
        await self.storage.close()
        await self.bot.session.close()
        await self.dp.storage.close()
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(0.250)
        print("Соединения закрыты")

    def _setup_shutdown(self):
        async def shutdown(signal):
            """Корректное завершение бота"""
            print(f'Получен сигнал {signal.name}...')
            await self._close()
            sys.exit(0)

        for sig in (signal.SIGTERM, signal.SIGINT):
            asyncio.get_event_loop().add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(shutdown(s))
            )

    async def send_welcome(self, message: types.Message, state: FSMContext):
        await state.set_data({
            'city': Config.DEFAULT_CITY,
            'lat': Config.DEFAULT_LATITUDE,
            'lon': Config.DEFAULT_LONGITUDE
        })
        
        await message.reply(
            "Привет! Я помогу тебе узнать погоду и подскажу, как одеться.\n"
            f"Сейчас установлен город: {Config.DEFAULT_CITY}",
            reply_markup=self.keyboard_manager.get_main_keyboard()
        )

    async def settings_handler(self, message: types.Message, state: FSMContext):
        user_data = await state.get_data()
        current_city = user_data.get('city', Config.DEFAULT_CITY)
        
        await message.reply(
            f"Текущий город: {current_city}\n"
            "Напишите название нового города:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(UserState.waiting_for_city)

    async def process_city(self, message: types.Message, state: FSMContext):
        city_data = await self.weather_service.get_coordinates(message.text)
        
        if city_data:
            await state.update_data(
                city=city_data['name'],
                lat=city_data['lat'],
                lon=city_data['lon']
            )
            await message.reply(
                f"Город успешно изменен на: {city_data['name']}",
                reply_markup=self.keyboard_manager.get_main_keyboard()
            )
        else:
            await message.reply(
                "Город не найден. Попробуйте другой город:",
                reply_markup=self.keyboard_manager.get_main_keyboard()
            )
        
        await state.set_state(None)

    async def handle_weather(self, message: types.Message, state: FSMContext):
        user_data = await state.get_data()
        is_today = message.text == "Погода сегодня"
        
        weather_data = await self.weather_service.get_weather(
            is_today,
            lat=user_data.get('lat', Config.DEFAULT_LATITUDE),
            lon=user_data.get('lon', Config.DEFAULT_LONGITUDE)
        )
        
        if weather_data:
            recommendation = self.weather_service.get_clothes_recommendation(weather_data)
            response = (
                f"{'Сегодня' if is_today else 'Завтра'} в {user_data.get('city', Config.DEFAULT_CITY)}:\n"
                f"Температура: {weather_data['temp']}°C\n"
                f"Ощущается как: {weather_data['feels_like']}°C\n"
                f"Состояние: {weather_data['condition']}\n\n"
                f"Рекомендация по одежде:\n{recommendation}"
            )
        else:
            response = "Извините, не удалось получить данные о погоде."
        
        await message.reply(response, reply_markup=self.keyboard_manager.get_main_keyboard())

    async def start(self):
        try:
            print('Бот запущен')
            await self.dp.start_polling(
                self.bot,
                allowed_updates=self.dp.resolve_used_update_types(),
                skip_updates=True  # Пропускаем накопившиеся сообщения
            )
        except Exception as e:
            print(f"Произошла ошибка: {e}")
        finally:
            await self._close()

async def main():
    try:
        # Создаем и запускаем бота
        weather_bot = WeatherBot()
        await weather_bot.start()
    except Exception as e:
        print(f"Критическая ошибка: {e}")
    finally:
        # На всякий случай очищаем все задачи
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот остановлен') 