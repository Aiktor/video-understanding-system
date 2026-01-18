"""
CLI для анализа видеофайлов
"""

import os
import json
import argparse
from dotenv import load_dotenv

from models import Instruction
from analyzer import analyze_video


def main():
    """Основная функция для запуска из командной строки"""
    # Загружаем переменные окружения
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description="Анализ видео с помощью AI-агента"
    )
    parser.add_argument(
        "video", 
        help="Путь к видеофайлу (mp4 или avi)"
    )
    parser.add_argument(
        "instruction", 
        help="Путь к JSON файлу с инструкцией"
    )
    parser.add_argument(
        "--api-key",
        help="API ключ (или установите PROXY_API_KEY в .env)"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.3,
        help="Интервал извлечения кадров в секундах (по умолчанию: 0.3)"
    )
    parser.add_argument(
        "--output",
        help="Путь для сохранения результатов в JSON"
    )
    
    args = parser.parse_args()
    
    # Получаем API ключ
    api_key = args.api_key or os.getenv("PROXY_API_KEY")
    if not api_key:
        print("Ошибка: не указан API ключ")
        print("Используйте --api-key или установите переменную окружения PROXY_API_KEY")
        return
    
    # Загружаем инструкцию
    with open(args.instruction, 'r', encoding='utf-8') as f:
        instruction_data = json.load(f)
        instruction = Instruction(**instruction_data)
    
    # Анализируем видео
    result = analyze_video(
        video_path=args.video,
        instruction=instruction,
        api_key=api_key,
        frame_interval=args.interval
    )
    
    # Выводим описание видео от LLM
    print("\n" + "="*60)
    print("ОПИСАНИЕ ВИДЕО ОТ AI:")
    print("="*60)
    print(result.video_summary)
    print()
    
    # Выводим резюме
    print(result.summary)
    
    # Сохраняем результаты
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)
        print(f"\nРезультаты сохранены в {args.output}")


if __name__ == "__main__":
    main()
