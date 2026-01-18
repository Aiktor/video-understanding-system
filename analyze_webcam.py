"""
CLI для анализа видеопотока с веб-камеры в реальном времени
"""

import os
import json
import cv2
from dotenv import load_dotenv

from models import Instruction
from webcam_processor import WebcamProcessor
from live_analyzer import LiveAnalyzer
from utils import log


def main():
    """Основная функция для запуска анализа с веб-камеры"""
    import argparse
    
    # Загружаем переменные окружения
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description="Анализ видео с веб-камеры в реальном времени"
    )
    parser.add_argument(
        "instruction", 
        help="Путь к JSON файлу с инструкцией"
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="ID камеры (по умолчанию: 0)"
    )
    parser.add_argument(
        "--api-key",
        help="API ключ (или установите PROXY_API_KEY в .env)"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Интервал между анализами в секундах (по умолчанию: 5.0)"
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Не показывать видео (только консоль)"
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
    
    print("\n" + "="*60)
    print("АНАЛИЗ ВИДЕОПОТОКА С ВЕБ-КАМЕРЫ")
    print("="*60)
    print(f"Инструкция: {instruction.title}")
    print(f"Количество шагов: {len(instruction.steps)}")
    print(f"Интервал анализа: {args.interval}с")
    print("\nНажмите 'q' для выхода")
    print("="*60)
    print()
    
    # Инициализация
    analyzer = LiveAnalyzer(
        instruction=instruction,
        api_key=api_key,
        analysis_interval=args.interval
    )
    
    try:
        with WebcamProcessor(camera_id=args.camera) as webcam:
            log("Начало анализа...")
            
            last_status_text = ""
            
            while True:
                # Получаем кадр
                frame_data = webcam.get_frame()
                if frame_data is None:
                    break
                
                frame, frame_base64, timestamp = frame_data
                
                # Анализируем, если пришло время
                if analyzer.should_analyze(timestamp):
                    log(f"Анализ кадра (время: {timestamp:.1f}с)...")
                    result = analyzer.analyze_frame(frame_base64, timestamp)
                    
                    # Формируем текст статуса
                    status_text = analyzer.get_status_display(result)
                    
                    # Выводим в консоль если изменился
                    if status_text != last_status_text:
                        print("\n" + status_text)
                        last_status_text = status_text
                    
                    # Проверяем завершение
                    if result.get('completed'):
                        log("Все шаги инструкции выполнены!")
                        
                        if not args.no_display:
                            # Показываем финальный кадр с сообщением
                            webcam.show_frame(
                                frame,
                                "Webcam Analysis",
                                "ЗАВЕРШЕНО!\nВсе шаги выполнены\nНажмите 'q' для выхода"
                            )
                        
                        # Ждем нажатия клавиши
                        print("\nАнализ завершен. Нажмите 'q' для выхода или продолжайте наблюдение...")
                
                # Отображение видео
                if not args.no_display:
                    # Текст для наложения на видео
                    overlay_text = f"Прогресс: {len(analyzer.completed_steps)}/{len(instruction.steps)}"
                    if analyzer.current_step < len(instruction.steps):
                        current_expected = instruction.steps[analyzer.current_step]
                        overlay_text += f"\nОжидается: {current_expected.step_number}. {current_expected.description[:40]}"
                    else:
                        overlay_text += "\nВСЕ ШАГИ ВЫПОЛНЕНЫ!"
                    
                    webcam.show_frame(frame, "Webcam Analysis", overlay_text)
                
                # Проверка выхода
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    log("Остановка по команде пользователя")
                    break
        
        # Выводим итоговое резюме
        print(analyzer.get_summary())
        
    except KeyboardInterrupt:
        log("\nОстановка по Ctrl+C")
    except Exception as e:
        log(f"Ошибка: {e}")
        raise
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
