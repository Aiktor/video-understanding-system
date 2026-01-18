"""
CLI для записи видео с веб-камеры
"""

import os
import cv2
from datetime import datetime
from utils import log


def main():
    """Основная функция для записи видео"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Запись видео с веб-камеры для последующего анализа"
    )
    parser.add_argument(
        "output",
        nargs="?",
        help="Путь к выходному файлу (по умолчанию: video_YYYYMMDD_HHMMSS.mp4)"
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="ID камеры (по умолчанию: 0)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        help="Длительность записи в секундах (по умолчанию: до нажатия 'q')"
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="Частота кадров (по умолчанию: 30)"
    )
    parser.add_argument(
        "--width",
        type=int,
        default=640,
        help="Ширина видео (по умолчанию: 640)"
    )
    parser.add_argument(
        "--height",
        type=int,
        default=480,
        help="Высота видео (по умолчанию: 480)"
    )
    parser.add_argument(
        "--codec",
        default="H264",
        choices=["mp4v", "XVID", "H264"],
        help="Видео кодек (по умолчанию: H264)"
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Не показывать видео во время записи"
    )
    parser.add_argument(
        "--countdown",
        type=int,
        default=3,
        help="Обратный отсчет перед началом записи в секундах (по умолчанию: 3)"
    )
    
    args = parser.parse_args()
    
    # Генерируем имя файла если не указано
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"video_{timestamp}.mp4"
    
    # Проверяем что файл не существует
    if os.path.exists(args.output):
        response = input(f"Файл {args.output} существует. Перезаписать? (y/n): ")
        if response.lower() != 'y':
            print("Отменено")
            return
    
    print("\n" + "="*60)
    print("📹 ЗАПИСЬ ВИДЕО С ВЕБ-КАМЕРЫ")
    print("="*60)
    print(f"Выходной файл: {args.output}")
    print(f"Разрешение: {args.width}x{args.height}")
    print(f"FPS: {args.fps}")
    print(f"Кодек: {args.codec}")
    if args.duration:
        print(f"Длительность: {args.duration}с")
    else:
        print("Длительность: до нажатия 'q'")
    print("\nУправление:")
    print("  'q' - остановить запись")
    print("  SPACE - пауза/продолжить")
    print("="*60)
    print()
    
    # Обратный отсчет
    if args.countdown > 0:
        print(f"Начало записи через {args.countdown} секунд...")
        import time
        for i in range(args.countdown, 0, -1):
            print(f"{i}...")
            time.sleep(1)
        print("▶ ЗАПИСЬ!")
        print()
    
    from webcam_recorder import WebcamRecorder
    
    try:
        recorder = WebcamRecorder(
            camera_id=args.camera,
            fps=args.fps,
            width=args.width,
            height=args.height,
            codec=args.codec
        )
        
        recorder.start_recording(args.output)
        
        paused = False
        start_time = None
        import time
        start_time = time.time()
        
        while True:
            frame_data = recorder.get_frame_for_display()
            
            if frame_data is None:
                log("Ошибка захвата кадра")
                break
            
            frame, timestamp, frame_count = frame_data
            
            # Проверка длительности
            if args.duration and timestamp >= args.duration:
                log(f"Достигнута заданная длительность: {args.duration}с")
                break
            
            # Отображение видео
            if not args.no_display:
                display_frame = frame.copy()
                
                # Наложение информации
                status = "⏸ ПАУЗА" if paused else "● REC"
                color = (0, 165, 255) if paused else (0, 0, 255)
                
                cv2.putText(
                    display_frame,
                    status,
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    color,
                    2
                )
                
                # Таймер
                timer_text = f"{int(timestamp//60):02d}:{int(timestamp%60):02d}"
                cv2.putText(
                    display_frame,
                    timer_text,
                    (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (255, 255, 255),
                    2
                )
                
                # Счетчик кадров
                cv2.putText(
                    display_frame,
                    f"Frames: {frame_count}",
                    (10, 110),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    1
                )
                
                cv2.imshow("Recording", display_frame)
            
            # Обработка клавиш
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                log("Остановка по команде пользователя")
                break
            elif key == ord(' '):
                paused = not paused
                if paused:
                    log("⏸ Пауза")
                else:
                    log("▶ Продолжение")
        
        # Останавливаем запись
        stats = recorder.stop_recording()
        
        print("\n" + "="*60)
        print("✓ ЗАПИСЬ ЗАВЕРШЕНА")
        print("="*60)
        print(f"Файл: {args.output}")
        print(f"Длительность: {stats['duration']:.1f}с")
        print(f"Кадров: {stats['frames']}")
        print(f"Средний FPS: {stats['fps']:.1f}")
        print("="*60)
        
        # Проверяем размер файла
        if os.path.exists(args.output):
            size_mb = os.path.getsize(args.output) / (1024 * 1024)
            print(f"Размер файла: {size_mb:.1f} МБ")
        
        print("\n💡 Теперь можно проанализировать видео:")
        print(f"   python analyze_video.py {args.output} instruction.json")
        print()
        
    except KeyboardInterrupt:
        log("\nОстановка по Ctrl+C")
        recorder.stop_recording()
    except Exception as e:
        log(f"Ошибка: {e}")
        raise
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
