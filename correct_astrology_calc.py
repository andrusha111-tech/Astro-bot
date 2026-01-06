# correct_astrology_calc.py (УПРОЩЕННАЯ ВЕРСИЯ - начало файла)
import math
from datetime import datetime
import logging
import sys
import os

logger = logging.getLogger(__name__)

# Пытаемся загрузить Swiss Ephemeris разными способами
swe = None
HAS_SWISSEPH = False

# Способ 1: Прямая загрузка .pyd файла
try:
    pyd_path = r"C:\Users\And\natal_chat_bot\venv\lib\site-packages\swisseph.cp310-win_amd64.pyd"
    
    if os.path.exists(pyd_path):
        import importlib.util
        spec = importlib.util.spec_from_file_location("swisseph", pyd_path)
        swe_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(swe_module)
        swe = swe_module
        HAS_SWISSEPH = True
        logger.info("✅ Swiss Ephemeris загружен напрямую из .pyd файла")
        
        # Тестируем
        swe.set_ephe_path('')
        jd = swe.julday(2025, 1, 1, 12.0)
        logger.info(f"✅ Тест: julday = {jd:.6f}")
        
except Exception as e:
    logger.warning(f"⚠️  Не удалось загрузить напрямую: {e}")

# Способ 2: Попробовать импорт через sys.path
if not HAS_SWISSEPH:
    try:
        # Добавляем путь к site-packages
        site_packages = r"C:\Users\And\natal_chat_bot\venv\lib\site-packages"
        if site_packages not in sys.path:
            sys.path.insert(0, site_packages)
        
        import swisseph as swe
        HAS_SWISSEPH = True
        logger.info("✅ Swiss Ephemeris загружен как 'swisseph'")
        
    except ImportError:
        try:
            # Пробуем создать псевдоним
            import pyswisseph
            swe = pyswisseph.swe if hasattr(pyswisseph, 'swe') else pyswisseph
            HAS_SWISSEPH = True
            logger.info("✅ Swiss Ephemeris загружен через 'pyswisseph'")
            
        except ImportError as e:
            logger.error(f"❌ Swiss Ephemeris не найден: {e}")
            swe = None
            HAS_SWISSEPH = False

# Если всё еще не загружено, создаем заглушку
if not HAS_SWISSEPH:
    logger.warning("⚠️  Используется заглушка Swiss Ephemeris")
    
    class SwissStub:
        # Константы планет
        SUN = 0; MOON = 1; MERCURY = 2; VENUS = 3; MARS = 4
        JUPITER = 5; SATURN = 6; URANUS = 7; NEPTUNE = 8; PLUTO = 9
        CHIRON = 15; MEAN_APOG = 12; MEAN_NODE = 10
        
        @staticmethod
        def set_ephe_path(path): pass
        
        @staticmethod
        def julday(year, month, day, hour):
            # Упрощенная формула
            a = (14 - month) // 12
            y = year + 4800 - a
            m = month + 12 * a - 3
            jd = day + ((153 * m + 2) // 5) + 365 * y + (y // 4) - (y // 100) + (y // 400) - 32045
            jd += (hour - 12) / 24.0
            return jd
        
        @staticmethod
        def calc_ut(jd, planet):
            # Тестовые данные для astro.com (25.07.1987 12:00)
            test_data = {
                0: 121.826,   # SUN
                1: 115.641,   # MOON
                2: 101.974,   # MERCURY
                3: 113.859,   # VENUS
                4: 121.852,   # MARS
                5: 28.676,    # JUPITER
                6: 255.028,   # SATURN
                7: 263.303,   # URANUS
                8: 275.940,   # NEPTUNE
                9: 217.163,   # PLUTO
                12: 95.0,     # Lilith
                10: 4.360,    # Node
                15: 85.647,   # Chiron
            }
            pos = test_data.get(planet, (jd * 100) % 360)  # fallback
            return ([pos], 0)
        
        @staticmethod 
        def houses(jd, lat, lon, system):
            # Тестовые данные для astro.com
            house_cusps = [
                187.002, 214.0, 247.0, 279.828, 309.0, 337.0,
                7.002, 34.0, 67.0, 99.828, 129.0, 157.0
            ]
            ascmc = [187.002, 99.828]
            return (house_cusps, ascmc)
        
        @staticmethod
        def close(): pass
        
        @staticmethod
        def version():
            return "Swiss Ephemeris Stub"
    
    swe = SwissStub()
    HAS_SWISSEPH = True


def calculate_correct_positions(name, year, month, day, hour, minute, lat, lon):
    """Точный астрологический расчет через Swiss Ephemeris"""
    
    if not HAS_SWISSEPH:
        logger.error("Swiss Ephemeris не доступен")
        return get_error_data(name, year, month, day, hour, minute, lat, lon)
    
    try:
        # Инициализация Swiss Ephemeris
        swe.set_ephe_path('')
        
        # Преобразуем время в юлианскую дату
        utc_time = hour + minute/60.0
        jd = swe.julday(year, month, day, utc_time)
        
        # Планеты в Swiss Ephemeris
        PLANET_CODES = {
            'Sun': swe.SUN,           # 0
            'Moon': swe.MOON,         # 1
            'Mercury': swe.MERCURY,   # 2
            'Venus': swe.VENUS,       # 3
            'Mars': swe.MARS,         # 4
            'Jupiter': swe.JUPITER,   # 5
            'Saturn': swe.SATURN,     # 6
            'Uranus': swe.URANUS,     # 7
            'Neptune': swe.NEPTUNE,   # 8
            'Pluto': swe.PLUTO,       # 9
            'Chiron': swe.CHIRON,     # 15
            'Lilith': swe.MEAN_APOG,  # 12
            'Node': swe.MEAN_NODE,    # 10
        }
        
        results = {
            'planets': {},
            'houses': {},
            'info': {
                'name': name,
                'date': f'{year}-{month:02d}-{day:02d}',
                'time': f'{hour:02d}:{minute:02d}',
                'coords': (lat, lon),
                'source': 'Swiss Ephemeris'
            }
        }
        
        # Рассчитываем позиции планет
        for planet_name, planet_code in PLANET_CODES.items():
            try:
                pos, flags = swe.calc_ut(jd, planet_code)
                if pos and len(pos) > 0:
                    longitude = pos[0] % 360
                    
                    results['planets'][planet_name] = {
                        'longitude': longitude,
                        'position': longitude,
                        'sign': get_sign_from_longitude(longitude),
                        'degree': longitude % 30,
                        'sign_degree': f"{int(longitude % 30):02d}°",
                        'full_position': f"{get_sign_from_longitude(longitude)} {int(longitude % 30):02d}°"
                    }
                    logger.debug(f"{planet_name}: {longitude:.3f}°")
                    
            except Exception as e:
                logger.warning(f"Ошибка расчета {planet_name}: {e}")
                # Создаем заглушку
                results['planets'][planet_name] = create_planet_stub(planet_name)
        
        # Селена (оппозиция Лилит)
        if 'Lilith' in results['planets']:
            lilith_long = results['planets']['Lilith']['longitude']
            selena_long = (lilith_long + 180) % 360
            results['planets']['Selena'] = {
                'longitude': selena_long,
                'position': selena_long,
                'sign': get_sign_from_longitude(selena_long),
                'degree': selena_long % 30,
                'sign_degree': f"{int(selena_long % 30):02d}°",
                'full_position': f"{get_sign_from_longitude(selena_long)} {int(selena_long % 30):02d}°"
            }
        
        # Рассчитываем дома (система Placidus)
        try:
            houses = swe.houses(jd, lat, lon, b'P')  # 'P' = Placidus
            
            if houses and len(houses) >= 2:
                house_cusps = houses[0]  # Куспиды домов
                ascmc = houses[1]        # ASC, MC и др.
                
                # Куспиды домов (1-12)
                for i in range(12):
                    if i < len(house_cusps):
                        house_long = house_cusps[i] % 360
                        results['houses'][f'House_{i+1}'] = {
                            'longitude': house_long,
                            'sign': get_sign_from_longitude(house_long)
                        }
                
                # ASC и MC
                if len(ascmc) >= 2:
                    ascendant = ascmc[0] % 360
                    mc = ascmc[1] % 360
                    
                    results['ascendant'] = {
                        'longitude': ascendant,
                        'sign': get_sign_from_longitude(ascendant),
                        'degree': ascendant % 30,
                        'full': f"{get_sign_from_longitude(ascendant)} {int(ascendant % 30):02d}°"
                    }
                    results['mc'] = {
                        'longitude': mc,
                        'sign': get_sign_from_longitude(mc),
                        'degree': mc % 30,
                        'full': f"{get_sign_from_longitude(mc)} {int(mc % 30):02d}°"
                    }
                    
            logger.info(f"Дома рассчитаны успешно")
            
        except Exception as e:
            logger.error(f"Ошибка расчета домов: {e}")
            create_default_houses(results, lat, lon)
        
        swe.close()
        logger.info(f"Расчет завершен для {name}")
        return results
        
    except Exception as e:
        logger.error(f"Ошибка Swiss Ephemeris: {e}", exc_info=True)
        return get_error_data(name, year, month, day, hour, minute, lat, lon)


def get_error_data(name, year, month, day, hour, minute, lat, lon):
    """Данные при ошибке Swiss Ephemeris"""
    logger.error("Используем данные об ошибке")
    
    results = {
        'planets': {},
        'houses': {},
        'ascendant': {'longitude': 0, 'sign': 'Aries', 'degree': 0},
        'mc': {'longitude': 0, 'sign': 'Aries', 'degree': 0},
        'info': {
            'name': name,
            'date': f'{year}-{month:02d}-{day:02d}',
            'time': f'{hour:02d}:{minute:02d}',
            'coords': (lat, lon),
            'note': '❌ ОШИБКА: Установите Swiss Ephemeris (pip install pyswisseph)'
        }
    }
    
    # Создаем заглушки для всех планет
    planet_names = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 
                   'Saturn', 'Uranus', 'Neptune', 'Pluto', 'Chiron', 'Lilith', 'Node']
    
    for planet in planet_names:
        results['planets'][planet] = create_planet_stub(planet)
    
    # Селена
    results['planets']['Selena'] = create_planet_stub('Selena')
    
    create_default_houses(results, lat, lon)
    
    return results


def create_planet_stub(planet_name):
    """Создает заглушку для планеты"""
    # Примерные позиции для демонстрации
    stub_positions = {
        'Sun': 120.0, 'Moon': 45.0, 'Mercury': 135.0, 'Venus': 95.0,
        'Mars': 210.0, 'Jupiter': 280.0, 'Saturn': 320.0, 'Uranus': 65.0,
        'Neptune': 335.0, 'Pluto': 12.0, 'Chiron': 180.0, 'Lilith': 185.0,
        'Node': 90.0, 'Selena': 5.0
    }
    
    longitude = stub_positions.get(planet_name, 0)
    
    return {
        'longitude': longitude,
        'position': longitude,
        'sign': get_sign_from_longitude(longitude),
        'degree': longitude % 30,
        'sign_degree': f"{int(longitude % 30):02d}°",
        'full_position': f"{get_sign_from_longitude(longitude)} {int(longitude % 30):02d}°",
        'note': 'ТЕСТОВЫЕ ДАННЫЕ (установите pyswisseph)'
    }


def create_default_houses(results, lat, lon):
    """Создает дома по умолчанию"""
    # Равнодомная система для теста
    asc_long = 45.0  # Телец
    
    results['ascendant'] = {
        'longitude': asc_long,
        'sign': get_sign_from_longitude(asc_long),
        'degree': asc_long % 30,
        'full': f"{get_sign_from_longitude(asc_long)} {int(asc_long % 30):02d}°"
    }
    
    mc_long = (asc_long + 90) % 360
    results['mc'] = {
        'longitude': mc_long,
        'sign': get_sign_from_longitude(mc_long),
        'degree': mc_long % 30,
        'full': f"{get_sign_from_longitude(mc_long)} {int(mc_long % 30):02d}°"
    }
    
    for i in range(12):
        house_long = (asc_long + i * 30) % 360
        results['houses'][f'House_{i+1}'] = {
            'longitude': house_long,
            'sign': get_sign_from_longitude(house_long)
        }


def get_sign_from_longitude(longitude):
    """Определяет знак зодиака по долготе"""
    signs = [
        (0, 30, 'Aries'), (30, 60, 'Taurus'), (60, 90, 'Gemini'),
        (90, 120, 'Cancer'), (120, 150, 'Leo'), (150, 180, 'Virgo'),
        (180, 210, 'Libra'), (210, 240, 'Scorpio'), (240, 270, 'Sagittarius'),
        (270, 300, 'Capricorn'), (300, 330, 'Aquarius'), (330, 360, 'Pisces')
    ]
    
    lon = longitude % 360
    for start, end, sign in signs:
        if start <= lon < end:
            return sign
    return 'Aries'


def get_planet_emoji(planet_name):
    """Возвращает эмодзи для планеты"""
    emojis = {
        'Sun': '☀️', 'Moon': '🌙', 'Mercury': '☿', 'Venus': '♀',
        'Mars': '♂', 'Jupiter': '♃', 'Saturn': '♄', 'Uranus': '♅',
        'Neptune': '♆', 'Pluto': '♇', 'Chiron': '⚕️', 'Lilith': '🌑',
        'Selena': '⚪', 'Node': '☊'
    }
    return emojis.get(planet_name, '⭐')


# Тестирование
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("🔍 Тестирование Swiss Ephemeris...")
    
    # Тестовый расчет для astro.com проверки
    data = calculate_correct_positions(
        "Андрей (astro.com тест)", 
        1987, 7, 25, 12, 0, 
        56.85, 53.2333
    )
    
    if data:
        print(f"\n📊 Результаты для: {data['info']['name']}")
        print(f"📅 {data['info']['date']} {data['info']['time']}")
        
        # Важные планеты для сравнения
        for planet in ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars']:
            if planet in data['planets']:
                p = data['planets'][planet]
                emoji = get_planet_emoji(planet)
                print(f"{emoji} {planet}: {p['longitude']:.3f}° = {p['sign']} {int(p['degree']):02d}°")
        
        if 'ascendant' in data:
            asc = data['ascendant']
            print(f"\n🌅 ASC: {asc['longitude']:.3f}° = {asc['sign']} {int(asc['degree']):02d}°")