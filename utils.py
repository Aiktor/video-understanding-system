"""
Вспомогательные функции
"""

from datetime import datetime


def log(message: str):
    """Вывод сообщения с временной меткой"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")
