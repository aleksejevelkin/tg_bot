import aiohttp
from config import Config
from datetime import datetime
import ssl

class WeatherService:
    def __init__(self):
        self.ssl_context = self._create_ssl_context()

    @staticmethod
    def _create_ssl_context():
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context

    async def get_coordinates(self, city_name):
        """Получение координат по названию города"""
        params = {
            'q': city_name,
            'limit': 1,
            'appid': Config.OPENWEATHER_API_KEY
        }
        
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=self.ssl_context)) as session:
            async with session.get(Config.GEOCODING_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data:
                        return {
                            'lat': str(data[0]['lat']),
                            'lon': str(data[0]['lon']),
                            'name': data[0]['local_names'].get('ru', data[0]['name']) if 'local_names' in data[0] else data[0]['name']
                        }
        return None

    async def get_weather(self, is_today=True, lat=None, lon=None):
        """Получение погоды по координатам"""
        params = {
            'lat': lat or Config.DEFAULT_LATITUDE,
            'lon': lon or Config.DEFAULT_LONGITUDE,
            'appid': Config.OPENWEATHER_API_KEY,
            'units': 'metric',
            'lang': 'ru'
        }
        
        url = f"{Config.OPENWEATHER_URL}/{'weather' if is_today else 'forecast'}"
        
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=self.ssl_context)) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_weather_data(data, is_today)
        return None

    def _parse_weather_data(self, data, is_today):
        if is_today:
            return {
                'temp': round(data['main']['temp']),
                'feels_like': round(data['main']['feels_like']),
                'condition': data['weather'][0]['description']
            }
        else:
            tomorrow = datetime.now().date().day + 1
            for forecast in data['list']:
                forecast_date = datetime.fromtimestamp(forecast['dt'])
                if forecast_date.day == tomorrow and forecast_date.hour in [14, 15, 16]:
                    return {
                        'temp': round(forecast['main']['temp']),
                        'feels_like': round(forecast['main']['feels_like']),
                        'condition': forecast['weather'][0]['description']
                    }
        return None

    @staticmethod
    def get_clothes_recommendation(weather_data):
        temp = weather_data['temp']
        condition = weather_data['condition'].lower()
        
        base_recommendations = []
        
        # Рекомендации по температуре
        if temp <= 0:
            base_recommendations.extend([
                "Тёплая зимняя куртка",
                "Шапка и шарф",
                "Тёплые перчатки",
                "Зимняя обувь"
            ])
        elif 0 < temp <= 10:
            base_recommendations.extend([
                "Демисезонная куртка",
                "Шапка",
                "Перчатки"
            ])
        elif 10 < temp <= 20:
            base_recommendations.extend([
                "Лёгкая куртка или кардиган",
                "Джинсы или брюки"
            ])
        else:
            base_recommendations.extend([
                "Футболка",
                "Шорты или лёгкие брюки"
            ])
        
        # Дополнительные рекомендации по условиям
        if any(word in condition for word in ['дождь', 'ливень']):
            base_recommendations.extend([
                "Зонт",
                "Водонепроницаемая обувь"
            ])
        elif any(word in condition for word in ['снег', 'метель']):
            base_recommendations.append("Непромокаемая обувь")
        
        return "\n".join(f"• {item}" for item in base_recommendations) 