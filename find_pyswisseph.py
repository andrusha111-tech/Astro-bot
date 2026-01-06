# find_pyswisseph.py
import sys
import os

print("Поиск pyswisseph...")

# Все пути Python
for path in sys.path:
    if os.path.exists(path):
        print(f"\n🔍 Проверяю: {path}")
        # Ищем файлы с 'swiss' или 'ephem'
        for item in os.listdir(path):
            if 'swiss' in item.lower() or 'ephem' in item.lower():
                print(f"  📁 {item}")
                # Если это папка, посмотрим что внутри
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    try:
                        for sub in os.listdir(full_path)[:5]:  # первые 5 файлов
                            print(f"    - {sub}")
                    except:
                        pass

# Проверим site-packages напрямую
import site
site_packages = site.getsitepackages()
print(f"\n🎯 Site-packages пути: {site_packages}")

for sp in site_packages:
    if os.path.exists(sp):
        print(f"\n📦 В {sp}:")
        items = os.listdir(sp)
        swiss_items = [i for i in items if 'swiss' in i.lower()]
        for item in swiss_items:
            print(f"  ➤ {item}")