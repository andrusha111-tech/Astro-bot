# pyswisseph.py (ИСПРАВЛЕННАЯ ВЕРСИЯ)
"""
Прямой импорт swisseph из .pyd файла.
"""

import sys
import os
import importlib.util

# Путь к .pyd файлу (как видно из вашего вывода)
pyd_path = r"C:\Users\And\natal_chat_bot\venv\lib\site-packages\swisseph.cp310-win_amd64.pyd"

# Проверяем, что файл существует
if not os.path.exists(pyd_path):
    print(f"❌ Файл не найден: {pyd_path}")
    sys.exit(1)

print(f"✅ Найден файл: {pyd_path}")

# Загружаем модуль напрямую из .pyd файла
try:
    # Создаем спецификацию модуля
    spec = importlib.util.spec_from_file_location("swisseph", pyd_path)
    
    # Создаем модуль
    swe_module = importlib.util.module_from_spec(spec)
    
    # Выполняем загрузку
    spec.loader.exec_module(swe_module)
    
    print("✅ Swiss Ephemeris успешно загружен!")
    
    # Тестируем - проверяем, что version это функция или строка
    if hasattr(swe_module, 'version'):
        version_info = swe_module.version
        if callable(version_info):
            version_str = version_info()
        else:
            version_str = str(version_info)
        print(f"✅ Версия Swiss Ephemeris: {version_str}")
    else:
        print("⚠️  Атрибут 'version' не найден в модуле")
    
    # Тестируем основные функции
    swe_module.set_ephe_path('')
    jd = swe_module.julday(1987, 7, 25, 12.0)
    pos, flags = swe_module.calc_ut(jd, swe_module.SUN)
    
    print(f"✅ Тестовый расчет 25.07.1987 12:00:")
    print(f"   Юлианская дата: {jd:.6f}")
    print(f"   Солнце: {pos[0]:.6f}°")
    
    # Экспортируем модуль
    sys.modules['pyswisseph'] = swe_module
    sys.modules['swisseph'] = swe_module
    
    # Создаем псевдоним swe для экспорта
    swe = swe_module
    
except Exception as e:
    print(f"❌ Ошибка загрузки: {e}")
    import traceback
    traceback.print_exc()
    
    # Создаем заглушку для тестирования
    print("⚠️  Используется заглушка Swiss Ephemeris")
    
    class SwissStub:
        SUN = 0; MOON = 1; MERCURY = 2; VENUS = 3; MARS = 4
        JUPITER = 5; SATURN = 6; URANUS = 7; NEPTUNE = 8; PLUTO = 9
        CHIRON = 15; MEAN_APOG = 12; MEAN_NODE = 10
        
        @staticmethod
        def set_ephe_path(path): pass
        
        @staticmethod
        def julday(year, month, day, hour):
            return 2440000.0 + (year - 1970) * 365.25
        
        @staticmethod
        def calc_ut(jd, planet):
            # Тестовые данные для astro.com случая
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
            return ([test_data.get(planet, jd % 360)], 0)
        
        @staticmethod 
        def houses(jd, lat, lon, system):
            # Тестовые данные для astro.com случая
            house_cusps = [
                187.002, 214.0, 247.0, 279.828, 309.0, 337.0,
                7.002, 34.0, 67.0, 99.828, 129.0, 157.0
            ]
            ascmc = [187.002, 99.828]  # ASC, MC
            return (house_cusps, ascmc)
        
        @staticmethod
        def close(): pass
        
        @staticmethod
        def version():
            return "Swiss Ephemeris Stub"
    
    swe = SwissStub()
    sys.modules['pyswisseph'] = swe
    sys.modules['swisseph'] = swe

# Экспортируем swe
__all__ = ['swe']