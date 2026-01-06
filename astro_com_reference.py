# astro_com_reference.py
"""
Эталонные данные с astro.com для проверки точности расчетов.
Данные для: Андрей, 25.07.1987 12:00, Ижевск (53°14'E, 56°51'N)
"""

ASTRO_COM_REFERENCE = {
    # Данные с PDF
    'name': 'Andrey',
    'date': '1987-07-25',
    'time': '12:00',
    'city': 'Izhevsk, RU',
    'coords': (56.85, 53.2333),  # 56°51'N, 53°14'E
    
    # Позиции планет в градусах (0-360)
    'planets': {
        'Sun': {
            'longitude': 121.826,      # 1°49'37" Лев = 120° + 1.826°
            'sign': 'Leo',
            'degrees': 1.826,
            'minutes': 49,
            'seconds': 37,
            'full': '1°49\'37" Лев'
        },
        'Moon': {
            'longitude': 115.641,      # 25°38'26" Рак = 90° + 25.641°
            'sign': 'Cancer',
            'degrees': 25.641,
            'minutes': 38,
            'seconds': 26,
            'full': '25°38\'26" Рак'
        },
        'Mercury': {
            'longitude': 101.974,      # 11°58'27" Рак = 90° + 11.974°
            'sign': 'Cancer',
            'degrees': 11.974,
            'minutes': 58,
            'seconds': 27,
            'full': '11°58\'27" Рак'
        },
        'Venus': {
            'longitude': 113.859,      # 23°51'33" Рак = 90° + 23.859°
            'sign': 'Cancer',
            'degrees': 23.859,
            'minutes': 51,
            'seconds': 33,
            'full': '23°51\'33" Рак'
        },
        'Mars': {
            'longitude': 121.852,      # 1°51'6" Лев = 120° + 1.852°
            'sign': 'Leo',
            'degrees': 1.852,
            'minutes': 51,
            'seconds': 6,
            'full': '1°51\'6" Лев'
        },
        'Jupiter': {
            'longitude': 28.676,       # 28°40'35" Овен = 0° + 28.676°
            'sign': 'Aries',
            'degrees': 28.676,
            'minutes': 40,
            'seconds': 35,
            'full': '28°40\'35" Овен'
        },
        'Saturn': {
            'longitude': 255.028,      # 15°1'42" Стрелец = 240° + 15.028°
            'sign': 'Sagittarius',
            'degrees': 15.028,
            'minutes': 1,
            'seconds': 42,
            'full': '15°1\'42" Стрелец'
        },
        'Uranus': {
            'longitude': 263.303,      # 23°18'13" Стрелец = 240° + 23.303°
            'sign': 'Sagittarius',
            'degrees': 23.303,
            'minutes': 18,
            'seconds': 13,
            'full': '23°18\'13" Стрелец'
        },
        'Neptune': {
            'longitude': 275.940,      # 5°56'24" Козерог = 270° + 5.940°
            'sign': 'Capricorn',
            'degrees': 5.940,
            'minutes': 56,
            'seconds': 24,
            'full': '5°56\'24" Козерог'
        },
        'Pluto': {
            'longitude': 217.163,      # 7°9'47" Скорпион = 210° + 7.163°
            'sign': 'Scorpio',
            'degrees': 7.163,
            'minutes': 9,
            'seconds': 47,
            'full': '7°9\'47" Скорпион'
        },
        'Node': {  # Истинный узел
            'longitude': 4.360,        # 4°21'37" Овен = 0° + 4.360°
            'sign': 'Aries',
            'degrees': 4.360,
            'minutes': 21,
            'seconds': 37,
            'full': '4°21\'37" Овен'
        },
        'Chiron': {
            'longitude': 85.647,       # 25°38'51" Близнецы = 60° + 25.647°
            'sign': 'Gemini',
            'degrees': 25.647,
            'minutes': 38,
            'seconds': 51,
            'full': '25°38\'51" Близнецы'
        },
        'Lilith': {  # Средняя Лилит из данных
            'longitude': 95.0,         # Приблизительно
            'sign': 'Cancer',
            'degrees': 5.0,
            'full': '5°00\'00" Рак'
        },
        'Selena': {  # Оппозиция Лилит
            'longitude': 275.0,        # 5° Козерог (оппозиция)
            'sign': 'Capricorn',
            'degrees': 5.0,
            'full': '5°00\'00" Козерог'
        }
    },
    
    # Дома
    'houses': {
        'ascendant': {
            'longitude': 187.002,      # 7°0'7" Весы = 180° + 7.002°
            'sign': 'Libra',
            'degrees': 7.002,
            'minutes': 0,
            'seconds': 7,
            'full': '7°0\'7" Весы'
        },
        'mc': {
            'longitude': 99.828,       # 9°49'40" Рак = 90° + 9.828°
            'sign': 'Cancer',
            'degrees': 9.828,
            'minutes': 49,
            'seconds': 40,
            'full': '9°49\'40" Рак'
        }
    },
    
    # Система
    'system': 'Placidus',
    'source': 'astro.com PDF 2026-01-06',
    'note': 'Точные данные для проверки Swiss Ephemeris'
}


def compare_with_astro_com(bot_results, tolerance=1.0):
    """
    Сравнивает результаты бота с эталонными данными astro.com
    
    Args:
        bot_results: результаты расчета бота
        tolerance: допустимая погрешность в градусах
        
    Returns:
        dict: результаты сравнения
    """
    if not bot_results or 'planets' not in bot_results:
        return {'error': 'Нет данных бота для сравнения'}
    
    comparison = {
        'total_planets': 0,
        'matched_planets': 0,
        'perfect_matches': 0,
        'sign_matches': 0,
        'details': {},
        'summary': {}
    }
    
    # Сравниваем планеты
    for planet_name, astro_data in ASTRO_COM_REFERENCE['planets'].items():
        if planet_name not in bot_results.get('planets', {}):
            continue
            
        bot_planet = bot_results['planets'][planet_name]
        comparison['total_planets'] += 1
        
        # Получаем долготу
        bot_long = bot_planet.get('longitude', 0)
        astro_long = astro_data['longitude']
        
        # Разница в градусах
        diff = abs(bot_long - astro_long)
        
        # Проверяем знак
        bot_sign = bot_planet.get('sign', 'Unknown')
        astro_sign = astro_data['sign']
        sign_match = bot_sign == astro_sign
        
        # Оценка точности
        if diff <= 0.1:  # 6 минут дуги
            match_level = 'ИДЕАЛЬНО'
            comparison['perfect_matches'] += 1
        elif diff <= 0.5:  # 30 минут
            match_level = 'ОТЛИЧНО'
        elif diff <= 1.0:  # 1 градус
            match_level = 'ХОРОШО'
        elif diff <= 2.0:  # 2 градуса
            match_level = 'УДОВЛЕТВОРИТЕЛЬНО'
        else:
            match_level = 'РАСХОЖДЕНИЕ'
        
        if sign_match and diff <= tolerance:
            comparison['matched_planets'] += 1
            
        if sign_match:
            comparison['sign_matches'] += 1
        
        # Сохраняем детали
        comparison['details'][planet_name] = {
            'bot_longitude': round(bot_long, 3),
            'astro_longitude': round(astro_long, 3),
            'difference': round(diff, 3),
            'bot_sign': bot_sign,
            'astro_sign': astro_sign,
            'sign_match': sign_match,
            'match_level': match_level,
            'astro_full': astro_data.get('full', '')
        }
    
    # Сравниваем дома
    if 'ascendant' in bot_results and 'houses' in ASTRO_COM_REFERENCE:
        asc_data = ASTRO_COM_REFERENCE['houses']['ascendant']
        bot_asc = bot_results.get('ascendant', {})
        
        if bot_asc:
            bot_asc_long = bot_asc.get('longitude', 0)
            astro_asc_long = asc_data['longitude']
            asc_diff = abs(bot_asc_long - astro_asc_long)
            asc_sign_match = bot_asc.get('sign') == asc_data['sign']
            
            comparison['details']['Ascendant'] = {
                'bot_longitude': round(bot_asc_long, 3),
                'astro_longitude': round(astro_asc_long, 3),
                'difference': round(asc_diff, 3),
                'bot_sign': bot_asc.get('sign'),
                'astro_sign': asc_data['sign'],
                'sign_match': asc_sign_match,
                'astro_full': asc_data['full']
            }
    
    # Итоговая статистика
    if comparison['total_planets'] > 0:
        match_percent = (comparison['matched_planets'] / comparison['total_planets']) * 100
        sign_match_percent = (comparison['sign_matches'] / comparison['total_planets']) * 100
        perfect_match_percent = (comparison['perfect_matches'] / comparison['total_planets']) * 100
    else:
        match_percent = sign_match_percent = perfect_match_percent = 0
    
    comparison['summary'] = {
        'match_percent': round(match_percent, 1),
        'sign_match_percent': round(sign_match_percent, 1),
        'perfect_match_percent': round(perfect_match_percent, 1),
        'total_checked': comparison['total_planets'],
        'tolerance_used': tolerance
    }
    
    return comparison


def format_comparison_report(comparison):
    """Форматирует отчет о сравнении в читаемый вид"""
    if 'error' in comparison:
        return f"❌ Ошибка сравнения: {comparison['error']}"
    
    report = []
    report.append("════════════════════════════════════════")
    report.append("🔍 <b>ПРОВЕРКА ТОЧНОСТИ (vs astro.com)</b>")
    report.append("════════════════════════════════════════")
    
    # Итоговая статистика
    summary = comparison['summary']
    report.append(f"📊 <b>ИТОГ:</b>")
    report.append(f"• Проверено планет: {summary['total_checked']}")
    report.append(f"• Совпадение знаков: {summary['sign_match_percent']}%")
    report.append(f"• Точность до 1°: {summary['match_percent']}%")
    report.append(f"• Идеальные совпадения: {summary['perfect_match_percent']}%")
    
    # Детали по планетам
    report.append("\n📋 <b>ДЕТАЛЬНОЕ СРАВНЕНИЕ:</b>")
    
    # Группируем по уровню точности
    accuracy_groups = {}
    for planet, data in comparison['details'].items():
        level = data['match_level']
        if level not in accuracy_groups:
            accuracy_groups[level] = []
        accuracy_groups[level].append(planet)
    
    # Выводим по группам точности
    levels_order = ['ИДЕАЛЬНО', 'ОТЛИЧНО', 'ХОРОШО', 'УДОВЛЕТВОРИТЕЛЬНО', 'РАСХОЖДЕНИЕ']
    
    for level in levels_order:
        if level in accuracy_groups:
            planets = accuracy_groups[level]
            report.append(f"\n<b>{level}:</b>")
            for planet in planets:
                data = comparison['details'][planet]
                sign_icon = "✅" if data['sign_match'] else "❌"
                report.append(f"{sign_icon} {planet}: {data['bot_longitude']:.3f}° vs {data['astro_longitude']:.3f}° (Δ={data['difference']:.3f}°)")
    
    # Критические проверки
    report.append("\n🔑 <b>КРИТИЧЕСКИЕ ПОКАЗАТЕЛИ:</b>")
    
    critical_planets = ['Sun', 'Moon', 'Ascendant', 'MC']
    for planet in critical_planets:
        if planet in comparison['details']:
            data = comparison['details'][planet]
            status = "✅ ПРОЙДЕНО" if data['difference'] <= 1.0 else "⚠️ ВНИМАНИЕ"
            report.append(f"{status} {planet}: Δ={data['difference']:.3f}° ({data['astro_full']})")
    
    report.append("\n════════════════════════════════════════")
    report.append("<i>Эталон: astro.com PDF от 06.01.2026</i>")
    
    return "\n".join(report)


# Функция для быстрого тестирования
def test_comparison():
    """Тестовая функция для проверки сравнения"""
    # Создаем тестовые данные бота
    test_bot_data = {
        'planets': {
            'Sun': {'longitude': 121.8, 'sign': 'Leo'},
            'Moon': {'longitude': 115.6, 'sign': 'Cancer'},
            'Mercury': {'longitude': 102.0, 'sign': 'Cancer'},
            'Venus': {'longitude': 113.9, 'sign': 'Cancer'},
            'Mars': {'longitude': 121.9, 'sign': 'Leo'},
            'Jupiter': {'longitude': 28.7, 'sign': 'Aries'},
            'Saturn': {'longitude': 255.0, 'sign': 'Sagittarius'},
            'Uranus': {'longitude': 263.3, 'sign': 'Sagittarius'},
            'Neptune': {'longitude': 275.9, 'sign': 'Capricorn'},
            'Pluto': {'longitude': 217.2, 'sign': 'Scorpio'},
            'Node': {'longitude': 4.4, 'sign': 'Aries'},
            'Chiron': {'longitude': 85.6, 'sign': 'Gemini'},
            'Lilith': {'longitude': 95.0, 'sign': 'Cancer'},
            'Selena': {'longitude': 275.0, 'sign': 'Capricorn'}
        },
        'ascendant': {'longitude': 187.0, 'sign': 'Libra'},
        'mc': {'longitude': 99.8, 'sign': 'Cancer'}
    }
    
    # Сравниваем
    result = compare_with_astro_com(test_bot_data)
    report = format_comparison_report(result)
    
    print(report)
    
    return result


if __name__ == "__main__":
    print("🔍 Тест сравнения с astro.com...")
    test_comparison()