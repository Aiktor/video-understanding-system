"""
Модуль для записи видео с веб-камеры
"""

import cv2
import time
from typing import Optional
from datetime import datetime
from utils import log


class WebcamRecorder:
    """Запись видео с веб-камеры в файл"""
    
    def __init__(
        self, 
        camera_id: int = 0, 
        fps: int = 30,
        width: int = 640,
        height: int = 480,
        codec: str = 'mp4v'
    ):
        """
        Инициализация рекордера
        
        Args:
            camera_id: ID камеры (обычно 0)
            fps: Частота кадров для записи
            width: Ширина видео
            height: Высота видео
            codec: Кодек для записи ('mp4v', 'XVID', 'H264')
        """
        self.camera_id = camera_id
        self.fps = fps
        self.width = width
        self.height = height
        self.codec = codec
        
        self.cap = None
        self.writer = None
        self.is_recording = False
        self.start_time = None
        self.frame_count = 0
        
    def start_recording(self, output_path: str):
        """
        Начать запись видео
        
        Args:
            output_path: Путь к выходному файлу
        """
        # Открываем камеру
        self.cap = cv2.VideoCapture(self.camera_id)
        
        if not self.cap.isOpened():
            raise ValueError(f"Не удалось открыть камеру {self.camera_id}")
        
        # Настройка параметров камеры
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        
        # Получаем фактические значения
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        # Создаем writer для записи
        fourcc = cv2.VideoWriter_fourcc(*self.codec)
        self.writer = cv2.VideoWriter(
            output_path,
            fourcc,
            self.fps,
            (actual_width, actual_height)
        )
        
        if not self.writer.isOpened():
            raise ValueError(f"Не удалось создать файл {output_path}")
        
        self.is_recording = True
        self.start_time = time.time()
        self.frame_count = 0
        
        log(f"Начало записи: {output_path}")
        log(f"Разрешение: {actual_width}x{actual_height}")
        log(f"FPS: {actual_fps:.1f}")
        
        return actual_width, actual_height, actual_fps
    
    def record_frame(self) -> bool:
        """
        Записать один кадр
        
        Returns:
            True если кадр записан, False если ошибка
        """
        if not self.is_recording:
            return False
        
        ret, frame = self.cap.read()
        
        if not ret:
            return False
        
        self.writer.write(frame)
        self.frame_count += 1
        
        return True
    
    def get_frame_for_display(self) -> Optional[tuple]:
        """
        Получить текущий кадр для отображения
        
        Returns:
            (frame, timestamp, frame_count) или None
        """
        if not self.is_recording:
            return None
        
        ret, frame = self.cap.read()
        
        if not ret:
            return None
        
        timestamp = time.time() - self.start_time
        
        # Записываем кадр
        self.writer.write(frame)
        self.frame_count += 1
        
        return frame, timestamp, self.frame_count
    
    def get_stats(self) -> dict:
        """Получить статистику записи"""
        if self.start_time is None:
            return {
                'duration': 0,
                'frames': 0,
                'fps': 0
            }
        
        duration = time.time() - self.start_time
        
        return {
            'duration': duration,
            'frames': self.frame_count,
            'fps': self.frame_count / duration if duration > 0 else 0
        }
    
    def stop_recording(self):
        """Остановить запись"""
        if not self.is_recording:
            return
        
        self.is_recording = False
        
        # Получаем финальную статистику
        stats = self.get_stats()
        
        # Освобождаем ресурсы
        if self.writer:
            self.writer.release()
            self.writer = None
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        cv2.destroyAllWindows()
        
        log(f"Запись завершена")
        log(f"  Длительность: {stats['duration']:.1f}с")
        log(f"  Кадров: {stats['frames']}")
        log(f"  Средний FPS: {stats['fps']:.1f}")
        
        return stats
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_recording()
