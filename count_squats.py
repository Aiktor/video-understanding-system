"""
CLI для подсчета приседаний с веб-камеры
"""

import os
import cv2
from dotenv import load_dotenv

from webcam_processor import WebcamProcessor
from squats_counter import SquatsCounter
from utils import log


def main():
    """Основная функция для подсчета приседаний"""
    import argparse
    
    # Загружаем переменные окружения
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description="Подсчет приседаний с веб-камеры в реальном времени"
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
        default=0.5,
        help="Интервал между анализами в секундах (по умолчанию: 0.5)"
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=0,
        help="Частота кадров камеры (по умолчанию: auto, рекомендуется 8-15 или 0 для авто)"
    )
    parser.add_argument(
        "--width",
        type=int,
        default=320,
        help="Ширина кадра (по умолчанию: 320, варианты: 320, 640, 1280)"
    )
    parser.add_argument(
        "--height",
        type=int,
        default=240,
        help="Высота кадра (по умолчанию: 240, варианты: 240, 480, 720)"
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=70,
        help="Качество JPEG 1-100 (по умолчанию: 70, ниже=быстрее)"
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Не показывать видео (только консоль)"
    )
    
    args = parser.parse_args()
    
    # Автоматический расчет оптимального FPS
    if args.fps == 0:
        # FPS = 1/interval * 2 (минимум для плавности)
        # Но не меньше 5 и не больше 15
        auto_fps = max(5, min(15, int(1 / args.interval * 2)))
        args.fps = auto_fps
        print(f"Авто FPS: {auto_fps} (на основе interval {args.interval}с)")
    
    # Получаем API ключ
    api_key = args.api_key or os.getenv("PROXY_API_KEY")
    if not api_key:
        print("Ошибка: не указан API ключ")
        print("Используйте --api-key или установите переменную окружения PROXY_API_KEY")
        return
    
    print("\n" + "="*60)
    print("🏋️  СЧЕТЧИК ПРИСЕДАНИЙ")
    print("="*60)
    print(f"Интервал анализа: {args.interval}с")
    print(f"Разрешение: {args.width}x{args.height}")
    print(f"FPS: {args.fps}, Качество: {args.quality}%")
    print("\nИнструкция:")
    print("1. Встаньте перед камерой так, чтобы было видно всё тело")
    print("2. Начинайте приседать")
    print("3. После каждого приседания счетчик увеличится")
    print("\nНажмите 'q' для выхода")
    print("="*60)
    print()
    
    # Инициализация счетчика
    counter = SquatsCounter(
        api_key=api_key,
        analysis_interval=args.interval
    )
    
    try:
        with WebcamProcessor(
            camera_id=args.camera, 
            fps=args.fps,
            width=args.width,
            height=args.height,
            jpeg_quality=args.quality
        ) as webcam:
            log("Начало подсчета приседаний...")
            print("\n⏳ Подготовка... Встаньте перед камерой\n")
            
            while True:
                # Получаем кадр
                frame_data = webcam.get_frame()
                if frame_data is None:
                    break
                
                frame, frame_base64, timestamp = frame_data
                
                # Анализируем, если пришло время
                if counter.should_analyze(timestamp):
                    result = counter.analyze_frame(frame_base64, timestamp)
                    
                    # Отображение видео
                    if not args.no_display:
                        display_text = counter.get_display_text(result)
                        webcam.show_frame(frame, "Squats Counter", display_text)
                else:
                    # Просто показываем видео
                    if not args.no_display:
                        result = {
                            'count': counter.squat_count,
                            'state': counter.current_state.value,
                            'timestamp': timestamp
                        }
                        display_text = counter.get_display_text(result)
                        webcam.show_frame(frame, "Squats Counter", display_text)
                
                # Проверка выхода
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    log("Остановка по команде пользователя")
                    break
        
        # Выводим итоговую статистику
        print(counter.get_summary())
        
    except KeyboardInterrupt:
        log("\nОстановка по Ctrl+C")
        print(counter.get_summary())
    except Exception as e:
        log(f"Ошибка: {e}")
        raise
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
