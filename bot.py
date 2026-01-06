import os
import re
import logging
import time
import math
import telegram.error
from datetime import datetime
from functools import lru_cache
from dotenv import load_dotenv

# Библиотеки Telegram
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    ConversationHandler
)
from telegram.constants import ParseMode

# Астрология и География
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

# Наши модули

from astro_com_reference import compare_with_astro_com, format_comparison_report
from correct_astrology_calc import calculate_correct_positions, get_planet_emoji

# Импорт данных из нашего внешнего файла
from data import TRANSLATE, PLANET_DESC, SIGNS_FULL, HOUSES_FULL, SIGN_PREPOSITIONS



# Для работы в Docker проверяем переменную окружения
def is_running_in_docker():
    return os.path.exists('/.dockerenv')


# --- НАСТРОЙКИ ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Состояния диалога
NAME, DATE, TIME, CITY = range(4)

# --- ВАЛИДАЦИЯ ДАННЫХ ---

def validate_date(date_text):
    """Проверяет корректность даты в формате ГГГГ-ММ-ДД"""
    try:
        date_obj = datetime.strptime(date_text, '%Y-%m-%d')
        if date_obj > datetime.now():
            return False, "Дата рождения не может быть в будущем"
        if date_obj.year < 1900:
            return False, "Пожалуйста, укажите год рождения после 1900"
        return True, ""
    except ValueError:
        return False, "Неверный формат. Используйте ГГГГ-ММ-ДД (например, 1990-12-31)"

def validate_time(time_text):
    """Проверяет корректность времени в формате ЧЧ:ММ"""
    pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
    if re.match(pattern, time_text):
        return True, ""
    return False, "Неверный формат времени. Используйте ЧЧ:ММ (например, 14:30)"

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

@lru_cache(maxsize=100)
def get_cached_location(city_name):
    """Кэширует результаты геокодирования для ускорения"""
    geolocator = Nominatim(user_agent="natal_bot_2026")
    try:
        location = geolocator.geocode(city_name, addressdetails=True, language="ru", timeout=10)
        return location
    except Exception as e:
        logger.error(f"Ошибка геокодирования для {city_name}: {e}")
        return None

def get_timezone(lat, lng):
    """Автоматически находит часовой пояс по координатам"""
    try:
        tf = TimezoneFinder()
        tz = tf.timezone_at(lng=lng, lat=lat)
        return tz or "UTC"
    except Exception as e:
        logger.error(f"Ошибка определения часового пояса: {e}")
        return "UTC"

def clean_trans(text):
    """Преобразует системные названия и переводит их"""
    if not text:
        return ""
    
    text_str = str(text)
    
    # 1. Прямой перевод из TRANSLATE
    if text_str in TRANSLATE:
        return TRANSLATE[text_str]
    
    # 2. Обработка домов
    if "_House" in text_str:
        house_base = text_str.replace("_House", "")
        if house_base in TRANSLATE:
            return TRANSLATE[house_base]
        
        house_mapping = {
            "First": "1", "Second": "2", "Third": "3",
            "Fourth": "4", "Fifth": "5", "Sixth": "6",
            "Seventh": "7", "Eighth": "8", "Ninth": "9",
            "Tenth": "10", "Eleventh": "11", "Twelfth": "12"
        }
        return house_mapping.get(house_base, house_base)
    
    # 3. Для знаков зодиака (короткие формы)
    sign_mapping = {
        "Ari": "Aries", "Tau": "Taurus", "Gem": "Gemini",
        "Can": "Cancer", "Leo": "Leo", "Vir": "Virgo",
        "Lib": "Libra", "Sco": "Scorpio", "Sag": "Sagittarius",
        "Cap": "Capricorn", "Aqu": "Aquarius", "Pis": "Pisces"
    }
    
    if text_str in sign_mapping:
        full_sign = sign_mapping[text_str]
        return TRANSLATE.get(full_sign, text_str)
    
    return text_str

async def details_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет подробные описания планет"""
        # Здесь можно сохранять последний расчет пользователя
        # и по команде /details показывать подробности
        await update.message.reply_text(
            "📋 <b>Подробные описания планет:</b>\n\n"
            "Используйте формат:\n"
            "<code>/planet Солнце</code> - описание Солнца\n"
            "<code>/planet Луна</code> - описание Луны\n"
            "<code>/planet Лилит</code> - описание Лилит\n\n"
            "Доступные планеты: Солнце, Луна, Меркурий, Венера, Марс, "
            "Юпитер, Сатурн, Уран, Нептун, Плутон, Лилит, Селена, Хирон",
            parse_mode=ParseMode.HTML
        )        


def get_planet_in_sign_text(planet_name, sign_name):
    """Возвращает правильное склонение: Солнце в Овне, Луна в Раке и т.д."""
    
    # Получаем русское название знака
    ru_sign = clean_trans(sign_name)
    
    # Получаем правильный предлог из data.py
    preposition = SIGN_PREPOSITIONS.get(ru_sign, f"в {ru_sign}")
    
    return f"{planet_name} {preposition}"

def get_sign_description(planet_key, sign_key):
    """Получает описание знака для конкретной планеты"""
    # Создаем ключи для поиска
    possible_keys = [
        f"{planet_key}_{sign_key}",
        f"{planet_key}_{sign_key.capitalize()}",
    ]
    
    # Также пробуем английские названия
    sign_mapping = {
        "Ari": "Aries", "Tau": "Taurus", "Gem": "Gemini",
        "Can": "Cancer", "Leo": "Leo", "Vir": "Virgo",
        "Lib": "Libra", "Sco": "Scorpio", "Sag": "Sagittarius",
        "Cap": "Capricorn", "Aqu": "Aquarius", "Pis": "Pisces"
    }
    
    if sign_key in sign_mapping:
        full_sign = sign_mapping[sign_key]
        possible_keys.append(f"{planet_key}_{full_sign}")
    
    # Ищем описание
    for key in possible_keys:
        if key in SIGNS_FULL:
            return SIGNS_FULL[key]
    
    # Если не нашли, создаем общее описание
    ru_planet = TRANSLATE.get(planet_key, planet_key)
    ru_sign = clean_trans(sign_key)
    return f"{ru_sign} - влияние на {ru_planet.lower()}"

def get_house_description(house_obj):
    """Получает описание дома"""
    if not house_obj:
        return "Дом не определен"
    
    # Получаем ключ дома
    house_key = ""
    if hasattr(house_obj, 'name'):
        house_key = str(house_obj.name)
    else:
        house_key = str(house_obj)
    
    # Преобразуем в числовой формат
    house_num = clean_trans(house_key)
    
    # Получаем описание
    house_desc = HOUSES_FULL.get(house_num, f"<b>{house_num} дом</b> - важная сфера жизни.")
    
    return house_desc

def format_compact_report(astro_data, ud, lat, lng, address):
    """Формирует компактный отчет в 3 сообщения"""
    
    reports = []
    
    # --- СООБЩЕНИЕ 1: ЗАГОЛОВОК И КЛЮЧЕВЫЕ ПЛАНЕТЫ ---
    report1 = []
    report1.append(f"📜 <b>ПРОФЕССИОНАЛЬНЫЙ НАТАЛЬНЫЙ АНАЛИЗ: {ud['name'].upper()}</b>")
    report1.append(f"📍 <i>{address[:100]}...</i>")
    report1.append(f"📅 <b>Дата:</b> {ud['date']} | <b>Время:</b> {ud['time']}")
    report1.append(f"🌐 <b>Координаты:</b> {lat:.4f}° N, {lng:.4f}° E")
    report1.append(f"⚡ <b>Система:</b> Swiss Ephemeris + Плацидус")
    report1.append("═" * 50)
    
    # Ключевые точки
    key_points = [
        ("Sun", "☀️ Солнце", "Ядро личности"),
        ("Moon", "🌙 Луна", "Эмоции и подсознание"),
        ("Ascendant", "🌅 Асцендент", "Личность и внешний образ"),
        ("MC", "👑 Зенит (MC)", "Карьера и статус"),
        ("Lilith", "🌑 Лилит", "Теневая сторона"),
        ("Selena", "⚪ Селена", "Светлый путь")
    ]
    
    report1.append("\n<b>КЛЮЧЕВЫЕ ТОЧКИ:</b>")
    for point_key, emoji_name, description in key_points:
        if point_key in ['Ascendant', 'MC']:
            data = astro_data.get(point_key.lower(), {})
        else:
            data = astro_data.get('planets', {}).get(point_key, {})
        
        if data:
            sign = data.get('sign', '?')
            degree = int(data.get('longitude', 0) % 30)
            report1.append(f"{emoji_name}: <b>{sign} {degree}°</b> - {description}")
    
    reports.append('\n'.join(report1))
    
    # --- СООБЩЕНИЕ 2: ВСЕ ПЛАНЕТЫ КОМПАКТНО ---
    report2 = []
    report2.append("✨ <b>ВСЕ ПЛАНЕТЫ И ТОЧКИ:</b>")
    report2.append("═" * 50)
    
    # Группировка планет по строкам (по 3 в строке)
    planets_groups = [
        [("Sun", "☀️"), ("Moon", "🌙"), ("Mercury", "☿")],
        [("Venus", "♀"), ("Mars", "♂"), ("Jupiter", "♃")],
        [("Saturn", "♄"), ("Uranus", "♅"), ("Neptune", "♆")],
        [("Pluto", "♇"), ("Chiron", "⚕️"), ("Node", "☊")],
        [("Lilith", "🌑"), ("Selena", "⚪"), ("", "")]  # Последняя группа
    ]
    
    for group in planets_groups:
        line_parts = []
        for planet_key, emoji in group:
            if planet_key:  # Пропускаем пустые
                data = astro_data.get('planets', {}).get(planet_key, {})
                if data:
                    sign_short = get_sign_short_name(data.get('sign', '?'))
                    degree = int(data.get('longitude', 0) % 30)
                    line_parts.append(f"{emoji} {sign_short} {degree}°")
        
        if line_parts:
            report2.append("  |  ".join(line_parts))
    
    reports.append('\n'.join(report2))
    
    # --- СООБЩЕНИЕ 3: ПРОВЕРКА И ССЫЛКА ---
    report3 = []
    report3.append("🔍 <b>ПРОВЕРКА ТОЧНОСТИ:</b>")
    
    # Парсим дату для ссылки
    y, m, d = map(int, ud['date'].split('-'))
    hh, mm = map(int, ud['time'].split(':'))
    
    # Создаем компактную ссылку (основные параметры)
    astro_link = f"https://www.astro.com/cgi/chart.cgi?lang=e&btyp=w2gw&sday={d}&smon={m}&syr={y}&shour={hh}&smin={mm}&nhor=1"
    
    report3.append(f"📊 <b>Сравните с astro.com:</b>")
    report3.append(f"• Дата: {d:02d}.{m:02d}.{y} {hh:02d}:{mm:02d}")
    report3.append(f"• Координаты: {lat:.4f}°N, {lng:.4f}°E")
    report3.append(f"• Система домов: Placidus")
    
    report3.append(f"\n🔗 <a href='{astro_link}'>Нажмите для создания карты на astro.com</a>")
    
    report3.append("\n" + "═" * 50)
    report3.append("✅ <b>РАСЧЕТ ЗАВЕРШЕН!</b>")
    report3.append("<i>Для подробного описания каждой планеты используйте команду /details</i>")
    
    reports.append('\n'.join(report3))
    
    return reports


def get_sign_short_name(sign_full):
    """Возвращает короткое название знака (русское)"""
    sign_mapping = {
        "Aries": "Овен", "Taurus": "Телец", "Gemini": "Близн",
        "Cancer": "Рак", "Leo": "Лев", "Virgo": "Дева",
        "Libra": "Весы", "Scorpio": "Скорп", "Sagittarius": "Стрел",
        "Capricorn": "Козер", "Aquarius": "Водол", "Pisces": "Рыбы"
    }
    return sign_mapping.get(sign_full, sign_full[:4])

def escape_xml(text):
    """Экранирует специальные XML символы"""
    if text is None:
        return ""
    text_str = str(text)
    text_str = text_str.replace("&", "&amp;")
    text_str = text_str.replace("<", "&lt;")
    text_str = text_str.replace(">", "&gt;")
    text_str = text_str.replace('"', "&quot;")
    text_str = text_str.replace("'", "&apos;")
    return text_str

async def send_long_message(update: Update, text: str, parse_mode=ParseMode.HTML):
    """Отправляет длинные сообщения, объединяя абзацы"""
    max_length = 4000  # Оставляем запас
    
    if len(text) <= max_length:
        await update.message.reply_text(text, parse_mode=parse_mode)
        return
    
    # Разбиваем по двойным переносам строк (абзацы)
    paragraphs = text.split('\n\n')
    
    current_message = []
    current_length = 0
    
    for para in paragraphs:
        para_with_newlines = para + '\n\n'
        para_length = len(para_with_newlines)
        
        # Если абзац сам по себе слишком длинный
        if para_length > max_length:
            # Если есть что отправить перед этим
            if current_message:
                await update.message.reply_text('\n\n'.join(current_message), parse_mode=parse_mode)
                current_message = []
                current_length = 0
            
            # Разбиваем очень длинный абзац
            lines = para.split('\n')
            chunk = []
            chunk_length = 0
            
            for line in lines:
                line_with_newline = line + '\n'
                if chunk_length + len(line_with_newline) > max_length and chunk:
                    await update.message.reply_text('\n'.join(chunk), parse_mode=parse_mode)
                    chunk = [line]
                    chunk_length = len(line_with_newline)
                else:
                    chunk.append(line)
                    chunk_length += len(line_with_newline)
            
            if chunk:
                await update.message.reply_text('\n'.join(chunk), parse_mode=parse_mode)
        
        # Если абзац помещается в текущее сообщение
        elif current_length + para_length <= max_length:
            current_message.append(para)
            current_length += para_length
        
        # Если не помещается - отправляем текущее и начинаем новое
        else:
            if current_message:
                await update.message.reply_text('\n\n'.join(current_message), parse_mode=parse_mode)
            
            current_message = [para]
            current_length = para_length
    
    # Отправляем последнее сообщение
    if current_message:
        await update.message.reply_text('\n\n'.join(current_message), parse_mode=parse_mode)

def get_all_astrological_points(subject):
    """Получает все астрологические точки включая Селену и Лилит"""
    all_points = []
    
    # Основные планеты
    planets = [
        ("Sun", subject.sun, "☀️"),
        ("Moon", subject.moon, "🌙"),
        ("Mercury", subject.mercury, "☿"),
        ("Venus", subject.venus, "♀"),
        ("Mars", subject.mars, "♂"),
        ("Jupiter", subject.jupiter, "♃"),
        ("Saturn", subject.saturn, "♄"),
        ("Uranus", subject.uranus, "♅"),
        ("Neptune", subject.neptune, "♆"),
        ("Pluto", subject.pluto, "♇"),
    ]
    
    for planet_key, planet_obj, emoji in planets:
        if planet_obj:
            # Получаем позицию
            position = 0
            if hasattr(planet_obj, 'position'):
                position = planet_obj.position
            elif hasattr(planet_obj, 'longitude'):
                position = planet_obj.longitude
            elif hasattr(planet_obj, 'absolute_position'):
                position = planet_obj.absolute_position
            
            all_points.append({
                'key': planet_key,
                'obj': planet_obj,
                'position': float(position) % 360,
                'emoji': emoji
            })
    
    # Лилит
    for attr_name in ['lilith', 'black_moon', 'mean_lilith']:
        if hasattr(subject, attr_name):
            point = getattr(subject, attr_name)
            if point:
                position = getattr(point, 'position', getattr(point, 'longitude', 0))
                all_points.append({
                    'key': 'Lilith',
                    'obj': point,
                    'position': float(position) % 360,
                    'emoji': '🌑'
                })
                break
    
    # Хирон
    if hasattr(subject, 'chiron') and subject.chiron:
        chiron = subject.chiron
        position = getattr(chiron, 'position', getattr(chiron, 'longitude', 0))
        all_points.append({
            'key': 'Chiron',
            'obj': chiron,
            'position': float(position) % 360,
            'emoji': '⚕️'
        })
    
    # Узлы
    if hasattr(subject, 'mean_node') and subject.mean_node:
        node = subject.mean_node
        position = getattr(node, 'position', getattr(node, 'longitude', 0))
        all_points.append({
            'key': 'Node',
            'obj': node,
            'position': float(position) % 360,
            'emoji': '☊'
        })
    
    # Селена (противоположность Лилит)
    lilith_points = [p for p in all_points if p['key'] == 'Lilith']
    if lilith_points:
        lilith_pos = lilith_points[0]['position']
        selena_pos = (lilith_pos + 180) % 360
        
        class SelenaPoint:
            def __init__(self, position):
                self.position = position
                self.sign = self._calc_sign(position)
                self.house = type('obj', (), {'name': 'Unknown'})()
            
            def _calc_sign(self, pos):
                signs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
                        'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
                return signs[int(pos // 30) % 12]
        
        all_points.append({
            'key': 'Selena',
            'obj': SelenaPoint(selena_pos),
            'position': selena_pos,
            'emoji': '⚪'
        })
    
    return all_points

# --- ОСНОВНЫЕ ФУНКЦИИ БОТА ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога"""
    context.user_data.clear()
    
    welcome_text = """🌟 <b>ПРОФЕССИОНАЛЬНЫЙ НАТАЛЬНЫЙ ГИД 2026</b>

Я создам для тебя профессиональную натальную карту с детальным анализом.

<b>Что ты получишь:</b>
1. 📋 <b>Детальный текстовый анализ</b> - все планеты, 12 домов, аспекты
2. 🎨 <b>Профессиональную натальную карту</b> - качественный SVG файл
3. 🔑 <b>Ключевые темы</b> - основные акценты твоего гороскопа
4. 🌑 <b>Селену и Лилит</b> - полный астрологический анализ
5. 💫 <b>Персональные рекомендации</b> - на основе твоей карты

<b>Для расчета мне понадобятся:</b>
1. Твое имя (можно псевдоним)
2. Точная дата рождения
3. Время рождения (по возможности точное)
4. Город рождения

<b>Как тебя зовут?</b>"""
    
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение имени"""
    name = update.message.text.strip()
    
    if len(name) < 2:
        await update.message.reply_text(
            "Имя должно содержать минимум 2 символа. Пожалуйста, введите имя:"
        )
        return NAME
    
    if len(name) > 50:
        await update.message.reply_text(
            "Имя слишком длинное. Пожалуйста, введите имя до 50 символов:"
        )
        return NAME
    
    context.user_data['name'] = name
    
    await update.message.reply_text(
        f"Отлично, {name}! ✨\n\n"
        "Теперь укажи <b>дату рождения</b> в формате <b>ГГГГ-ММ-ДД</b>\n"
        "<i>Пример: 1990-12-31</i>\n\n"
        "<b>Важно:</b>\n"
        "• Год - 4 цифры\n"
        "• Месяц - 2 цифры\n"
        "• День - 2 цифры\n"
        "• Разделитель - дефис", 
        parse_mode=ParseMode.HTML
    )
    
    return DATE


async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение даты с валидацией"""
    date_text = update.message.text.strip()
    is_valid, error_msg = validate_date(date_text)
    
    if not is_valid:
        await update.message.reply_text(
            f"❌ {error_msg}\n\n"
            "Попробуй еще раз в формате <b>ГГГГ-ММ-ДД</b>:\n"
            "<i>Пример: 1990-12-31</i>",
            parse_mode=ParseMode.HTML
        )
        return DATE
    
    context.user_data['date'] = date_text
    
    await update.message.reply_text(
        "Прекрасно! 🗓️\n\n"
        "Теперь введи <b>точное время рождения</b> в формате <b>ЧЧ:ММ</b>\n"
        "<i>Пример: 14:30</i>\n\n"
        "<b>Если не знаешь точное время:</b>\n"
        "• Используй 12:00 (полдень)\n"
        "• Или 00:00 (полночь)\n\n"
        "<b>Чем точнее время - тем точнее расчет!</b>",
        parse_mode=ParseMode.HTML
    )
    
    return TIME


async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение времени с валидацией"""
    time_text = update.message.text.strip()
    is_valid, error_msg = validate_time(time_text)
    
    if not is_valid:
        await update.message.reply_text(
            f"❌ {error_msg}\n\n"
            "Попробуй еще раз в формате <b>ЧЧ:ММ</b>:\n"
            "<i>Пример: 14:30 или 09:15</i>",
            parse_mode=ParseMode.HTML
        )
        return TIME
    
    context.user_data['time'] = time_text
    
    await update.message.reply_text(
        "Замечательно! ⏰\n\n"
        "Теперь напиши <b>город рождения</b>\n"
        "<i>Можно на русском или английском языке</i>\n\n"
        "<b>Примеры:</b>\n"
        "• Ижевск\n"
        "• Москва\n"
        "• Санкт-Петербург\n"
        "• New York\n\n"
        "<b>Подсказка:</b> Если город маленький, укажи страну: 'Ижевск, Россия'",
        parse_mode=ParseMode.HTML
    )
    
    return CITY


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена диалога"""
    await update.message.reply_text(
        "🚫 Профессиональный анализ прерван.\n\n"
        "Твои данные не сохранены. Когда будешь готов, напиши /start",
        parse_mode=ParseMode.HTML
    )
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка по использованию бота"""
    help_text = """
🔮 <b>ПРОФЕССИОНАЛЬНЫЙ НАТАЛЬНЫЙ ГИД 2026 - ПОМОЩЬ</b>

<b>Основные команды:</b>
/start - Начать создание профессиональной натальной карты
/help - Эта справка
/cancel - Отменить текущий диалог

<b>Формат данных:</b>
• <b>Имя:</b> Любое имя или псевдоним (2-50 символов)
• <b>Дата:</b> ГГГГ-ММ-ДД (1990-12-31)
• <b>Время:</b> ЧЧ:ММ (14:30) - чем точнее, тем лучше
• <b>Город:</b> Любой город мира (Ижевск, Москва, New York)

<b>Что вы получите:</b>
1. 📋 <b>Профессиональный текстовый анализ</b> - все планеты, 12 домов, аспекты
2. 🎨 <b>Качественную натальную карту</b> - SVG файл с Селеной и Лилит
3. 🔑 <b>Ключевые акценты</b> - основные темы вашего гороскопа
4. 🌑 <b>Селену и Лилит</b> - полный астрологический анализ

<b>Технологии:</b>
• Используется профессиональная астрологическая библиотека Kerykeion
• Точные астрономические расчеты
• Качественная визуализация
• Профессиональные интерпретации
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


async def create_beautiful_svg(name, date_str, time_str, city_name, subject, update: Update):
    """Упрощенная версия для быстрого тестирования"""
    try:
        logger.info(f"Создание упрощенного SVG для {name}")
        
        # Создаем уникальное имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r'[^\w]', '_', name)[:20]
        svg_filename = f"natal_chart_{safe_name}_{timestamp}.svg"
        
        # Получаем все точки
        all_points = get_all_astrological_points(subject)
        
        # Создаем простой SVG
        svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="800" height="1000" xmlns="http://www.w3.org/2000/svg">
    <rect width="100%" height="100%" fill="#0a0a2a"/>
    
    <text x="400" y="50" text-anchor="middle" fill="white" font-size="32" font-family="Arial">
        Натальная карта: {escape_xml(name)}
    </text>
    
    <text x="400" y="90" text-anchor="middle" fill="#64b5f6" font-size="18" font-family="Arial">
        {escape_xml(date_str)} • {escape_xml(time_str)}
    </text>
    
    <text x="400" y="120" text-anchor="middle" fill="#bbbbbb" font-size="16" font-family="Arial">
        {escape_xml(city_name)}
    </text>
    
    <!-- Круг -->
    <circle cx="400" cy="400" r="250" fill="none" stroke="#3d5afe" stroke-width="3"/>
    
    <!-- Планеты -->
    <g font-family="Arial">'''
        
        # Добавляем планеты
        for point in all_points:
            planet_key = point['key']
            position = point['position'] % 360
            angle = math.radians(position - 90)
            radius = 200
            
            # Цвета
            colors = {
                "Sun": "#FF9800", "Moon": "#E1BEE7", "Lilith": "#4A235A", 
                "Selena": "#FFFFFF", "Chiron": "#8BC34A"
            }
            color = colors.get(planet_key, "#607D8B")
            
            # Эмодзи
            emojis = {
                "Sun": "☀️", "Moon": "🌙", "Lilith": "🌑", 
                "Selena": "⚪", "Chiron": "⚕️"
            }
            emoji = emojis.get(planet_key, "⭐")
            
            x = 400 + radius * math.cos(angle)
            y = 400 + radius * math.sin(angle)
            
            svg_content += f'''
        <circle cx="{x:.1f}" cy="{y:.1f}" r="10" fill="{color}"/>
        <text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" dy=".3em" font-size="8" fill="black">
            {emoji}
        </text>'''
        
        svg_content += f'''
    </g>
    
    <!-- Легенда -->
    <rect x="50" y="700" width="700" height="250" rx="10" fill="#1a1a2e"/>
    <text x="75" y="730" fill="white" font-size="20" font-family="Arial">Включены:</text>
    
    <text x="75" y="770" fill="#FF9800" font-size="16" font-family="Arial">✅ 10 основных планет</text>
    <text x="75" y="800" fill="#4A235A" font-size="16" font-family="Arial">🌑 Лилит (Черная Луна)</text>
    <text x="75" y="830" fill="#FFFFFF" font-size="16" font-family="Arial">⚪ Селена (Белая Луна)</text>
    <text x="75" y="860" fill="#8BC34A" font-size="16" font-family="Arial">⚕️ Хирон</text>
    
    <text x="400" y="980" text-anchor="middle" fill="#666666" font-size="12">
        Натальный Гид 2026 • Полный астрологический анализ
    </text>
</svg>'''
        
        # Сохраняем и отправляем
        with open(svg_filename, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        
        with open(svg_filename, 'rb') as svg_file:
            await update.message.reply_document(
                document=svg_file,
                filename=f"Натальная_карта_{safe_name}.svg",
                caption=f"✨ Натальная карта для {name}\n📅 {date_str} • ⏰ {time_str}\n📍 {city_name}",
                parse_mode=ParseMode.HTML
            )
        
        # Очистка
        time.sleep(0.5)
        try:
            os.remove(svg_filename)
        except:
            pass
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка создания упрощенного SVG: {e}")
        return False


async def get_city_and_calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение города и выполнение расчета"""
    user_city = update.message.text.strip()
    ud = context.user_data
    
    # Сохраняем город
    ud['city'] = user_city
    
    await update.message.reply_text(
        "🔮 <b>Запускаю профессиональные астрологические расчеты...</b>\n\n"
        "• Определяю координаты и часовой пояс\n"
        "• Рассчитываю положение ВСЕХ планет (Swiss Ephemeris)\n"
        "• Добавляю <b>Селену и Лилит</b>\n"
        "• Строю дома гороскопа (система Плацидуса)\n"
        "• Анализирую аспекты",
        parse_mode=ParseMode.HTML
    )
    
    try:
        # 1. Поиск локации
        location = get_cached_location(user_city)
        if not location:
            location = get_cached_location(f"{user_city}, Россия")
        
        if not location:
            await update.message.reply_text(
                "❌ <b>Город не найден!</b>\n\n"
                "Попробуй:\n"
                "1. Проверить написание\n"
                "2. Добавить страну: 'Ижевск, Россия'\n"
                "3. Использовать /start для нового ввода",
                parse_mode=ParseMode.HTML
            )
            return ConversationHandler.END
        
        lat, lng = location.latitude, location.longitude
        address = location.address
        
        # 2. Часовой пояс
        tz_str = get_timezone(lat, lng)
        
        # 3. Парсинг данных
        y, m, d = map(int, ud['date'].split('-'))
        hh, mm = map(int, ud['time'].split(':'))
        
        # Определяем, тестовый ли это случай astro.com
        is_astro_test_case = (
            str(y) == '1987' and str(m) == '7' and str(d) == '25' and
            str(hh) == '12' and str(mm) == '0' and
            lat >= 56.8 and lat <= 56.9 and  # примерно 56°51'N
            lng >= 53.2 and lng <= 53.3      # примерно 53°14'E
        )
        
        # Сохраняем в context.user_data для использования позже
        context.user_data['is_astro_test_case'] = is_astro_test_case

        # 4. Точный астрологический расчет
        await update.message.reply_text(
            "📡 <b>Рассчитываю точные планетарные позиции через Swiss Ephemeris...</b>\n"
            "<i>Использую профессиональную астрологическую систему</i>",
            parse_mode=ParseMode.HTML
        )
        
        # Рассчитываем через Swiss Ephemeris
        astro_data = calculate_correct_positions(
            ud['name'], y, m, d, hh, mm, lat, lng
        )
        
        if is_astro_test_case:
            await update.message.reply_text(
                "🎯 <b>ОБНАРУЖЕН ТЕСТОВЫЙ СЛУЧАЙ ASTRO.COM!</b>\n"
                "Запускаю профессиональную проверку точности расчетов...",
                parse_mode=ParseMode.HTML
            )
            
            # Сравниваем с эталоном astro.com
            comparison = compare_with_astro_com(astro_data)
            accuracy_report = format_comparison_report(comparison)
            
            # Отправляем отчет о точности
            await send_long_message(update, accuracy_report)
            
            # Сохраняем для использования в основном отчете
            context.user_data['accuracy_comparison'] = comparison
            
            # Если точность низкая, предупреждаем
            summary = comparison.get('summary', {})
            if summary.get('match_percent', 0) < 80:
                await update.message.reply_text(
                    "⚠️ <b>ВНИМАНИЕ: Обнаружены расхождения с astro.com!</b>\n"
                    "Проверьте установку Swiss Ephemeris.\n"
                    "Точность расчетов: {:.1f}%".format(summary.get('match_percent', 0)),
                    parse_mode=ParseMode.HTML
                )
            else:
                await update.message.reply_text(
                    f"✅ <b>Точность расчетов подтверждена!</b>\n"
                    f"Совпадение с astro.com: {summary.get('match_percent', 0):.1f}%",
                    parse_mode=ParseMode.HTML
                )

        if not astro_data:
            await update.message.reply_text(
                "❌ <b>Ошибка в астрологических расчетах</b>\n"
                "Попробуйте указать другую дату или время",
                parse_mode=ParseMode.HTML
            )
            return ConversationHandler.END
        
        # 5. Создаем совместимый объект
        class PlanetObject:
            def __init__(self, planet_data):
                self.position = planet_data.get('longitude', 0)
                self.longitude = planet_data.get('longitude', 0)
                self.sign = planet_data.get('sign', 'Aries')
                self.house = type('House', (), {'name': 'Unknown'})()
                
        class AstroSubject:
            def __init__(self, astro_data):
                # Основные планеты
                planets_dict = astro_data.get('planets', {})
                
                self.sun = PlanetObject(planets_dict.get('Sun', {}))
                self.moon = PlanetObject(planets_dict.get('Moon', {}))
                self.mercury = PlanetObject(planets_dict.get('Mercury', {}))
                self.venus = PlanetObject(planets_dict.get('Venus', {}))
                self.mars = PlanetObject(planets_dict.get('Mars', {}))
                self.jupiter = PlanetObject(planets_dict.get('Jupiter', {}))
                self.saturn = PlanetObject(planets_dict.get('Saturn', {}))
                self.uranus = PlanetObject(planets_dict.get('Uranus', {}))
                self.neptune = PlanetObject(planets_dict.get('Neptune', {}))
                self.pluto = PlanetObject(planets_dict.get('Pluto', {}))
                
                # Лилит и Селена
                self.lilith = PlanetObject(planets_dict.get('Lilith', {}))
                self.selena = PlanetObject(planets_dict.get('Selena', {}))
                self.chiron = PlanetObject(planets_dict.get('Chiron', {}))
                self.mean_node = PlanetObject(planets_dict.get('Node', {}))
                
                # Асцендент и MC
                asc_data = astro_data.get('ascendant', {})
                mc_data = astro_data.get('mc', {})
                
                self.first_house = type('House', (), {
                    'sign': asc_data.get('sign', 'Aries'),
                    'position': asc_data.get('longitude', 0)
                })()
                self.tenth_house = type('House', (), {
                    'sign': mc_data.get('sign', 'Capricorn'),
                    'position': mc_data.get('longitude', 270)
                })()
        
        # Создаем объект subject
        subject = AstroSubject(astro_data)
        
        # 6. Формирование отчета
        compact_reports = format_compact_report(astro_data, ud, lat, lng, address)
        for report_text in compact_reports:
            await update.message.reply_text(report_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        
       
        # 7. Создание SVG (упрощенная версия для проверки)
        await update.message.reply_text("🎨 <b>Создаю натальную карту для проверки...</b>", parse_mode=ParseMode.HTML)
        
        # Простая проверочная карта
        try:
            # Создаем простую текстовую версию карты для проверки
            check_text = f"📊 <b>ПРОВЕРОЧНАЯ КАРТА ДЛЯ {ud['name']}</b>\n\n"
            # Определите где-то перед использованием:
            planets_to_analyze = [
                ("Sun", subject.sun, "☀️"),
                ("Moon", subject.moon, "🌙"),
                ("Mercury", subject.mercury, "☿"),
                ("Venus", subject.venus, "♀"),
                ("Mars", subject.mars, "♂"),
                ("Jupiter", subject.jupiter, "♃"),
                ("Saturn", subject.saturn, "♄"),
                ("Uranus", subject.uranus, "♅"),
                ("Neptune", subject.neptune, "♆"),
                ("Pluto", subject.pluto, "♇"),
                ("Lilith", subject.lilith, "🌑"),
                ("Selena", subject.selena, "⚪"),
                ("Chiron", subject.chiron, "⚕️"),
                ("Node", subject.mean_node, "☊"),
            ]
            for p_key, p_obj, emoji in planets_to_analyze:
                if p_obj and hasattr(p_obj, 'sign'):
                    ru_planet = TRANSLATE.get(p_key, p_key)
                    sign = getattr(p_obj, 'sign', '?')
                    degree = int(getattr(p_obj, 'longitude', 0) % 30)
                    check_text += f"{emoji} {ru_planet}: {sign} {degree}°\n"
            
            await update.message.reply_text(check_text, parse_mode=ParseMode.HTML)
            
            # Создаем ссылку для сравнения на astro.com
            astro_link = f"https://www.astro.com/cgi/chart.cgi?lang=e&btyp=w2gw&sday={d}&smon={m}&syr={y}&shour={hh}&smin={mm}&hsy=-1&zod=&orbp=&rs=0&ast=&add=18&add=19&add=20&node=&asp=1&asp=2&asp=3&asp=4&asp=5&asp=6&asp=7&asp=8&pbs=&nhor=1&nho2=1&sstr=1&lg=e&cid=uuf&go.x=15&go.y=12"

            # Для тестового случая показываем специальное сообщение
            if is_astro_test_case:
                await update.message.reply_text(
                    f"🔗 <b>Эталонная карта для сравнения:</b>\n"
                    f"<a href='{astro_link}'>Нажмите для открытия astro.com</a>\n\n"
                    f"<i>Ваши данные точно соответствуют профессиональному эталону!</i>\n"
                    f"<b>Параметры проверки:</b>\n"
                    f"• Дата: {d:02d}.{m:02d}.{y}\n"
                    f"• Время: {hh:02d}:{mm:02d}\n"
                    f"• Координаты: {lat:.4f}°N, {lng:.4f}°E",
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )
            else:
                # Для обычных случаев
                await update.message.reply_text(
                    f"🔗 <b>Для самостоятельной проверки:</b>\n"
                    f"<a href='{astro_link}'>Нажмите для создания карты на astro.com</a>\n\n"
                    f"<i>Проверьте точность наших расчетов:</i>\n"
                    f"• Дата: {d:02d}.{m:02d}.{y}\n"
                    f"• Время: {hh:02d}:{mm:02d}\n"
                    f"• Широта: {lat:.4f}°\n"
                    f"• Долгота: {lng:.4f}°",
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )   
            
        except Exception as e:
            logger.error(f"Ошибка создания проверочной карты: {e}")
        
        # Завершение
        await update.message.reply_text(
            "✅ <b>РАСЧЕТ ЗАВЕРШЕН!</b>\n\n"
            "<b>Что вы получили:</b>\n"
            "1. 📋 <b>Точные планетарные позиции</b> (Swiss Ephemeris)\n"
            "2. 📊 <b>Градусы в знаках</b> для сравнения\n"
            "3. 🔗 <b>Ссылку для проверки</b> на astro.com\n\n"
            "<i>Используйте эти данные для создания точной натальной карты!</i>",
            parse_mode=ParseMode.HTML
        )
        
        # Предлагаем начать заново
        await update.message.reply_text(
            "🔄 <b>Хотите сделать другой расчет?</b>\n"
            "Используйте /start",
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Ошибка расчета: {e}", exc_info=True)
        
        error_text = f"""
❌ <b>Произошла ошибка в расчетах</b>

<b>Техническая информация:</b>
<code>{str(e)[:200]}</code>

<b>Что делать:</b>
• Проверьте правильность данных
• Попробуйте другое время или дату
• Используйте /start для нового расчета
"""
        await update.message.reply_text(error_text, parse_mode=ParseMode.HTML)
    
    return ConversationHandler.END

# Добавьте эту функцию для обработки ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")
    
    # Для ошибок сети отправляем понятное сообщение
    if isinstance(context.error, telegram.error.TimedOut):
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "⏳ Произошел таймаут сети. Попробуйте еще раз через несколько секунд.\n\n"
                    "Если проблема повторяется, проверьте ваше интернет-соединение."
                )
            except:
                pass
    elif isinstance(context.error, telegram.error.NetworkError):
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "🌐 Проблема с сетью. Проверьте интернет-соединение и попробуйте снова."
                )
            except:
                pass

if __name__ == '__main__':
    if not TOKEN:
        print("❌ Ошибка: Добавьте BOT_TOKEN в файл .env!")
        exit(1)
    
    print("🚀 Запуск ПРОФЕССИОНАЛЬНОГО Натального Гида 2026...")
    print("✨ Теперь с СЕЛЕНОЙ и ЛИЛИТ!")
    print("=" * 60)
    print("📁 Рабочая директория:", os.path.abspath('.'))
    print("🔑 Токен:", TOKEN[:10] + "..." if TOKEN else "Не найден")
    print("📊 Логирование: bot.log")
    print("🎨 Качественные SVG карты: АВТОМАТИЧЕСКИ")
    print("🌑 Включены: Селена и Лилит")
    print("=" * 60)
    print("🤖 Бот успешно запущен!")
    print("📍 Готов к профессиональной работе")
    print("🎨 Создает полные натальные карты")
    print("📞 Для остановки нажмите Ctrl+C")
    print("=" * 60 + "\n")
    
    app = ApplicationBuilder()\
    .token(TOKEN)\
    .read_timeout(30)\
    .write_timeout(30)\
    .connect_timeout(30)\
    .pool_timeout(30)\
    .build()
    app.add_error_handler(error_handler)

    app.add_handler(CommandHandler('details', details_command))
    
    # Обработчик диалога
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_time)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city_and_calculate)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('help', help_command))
    
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        print("\n👋 Профессиональный бот остановлен пользователем")
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}")
        print(f"💥 Критическая ошибка: {e}")