"""
Обработчик видеопотока с веб-камеры
"""

import cv2
import base64
import time
from typing import Optional, Callable
from datetime import datetime


class WebcamProcessor:
    """Обработчик видеопотока с веб-камеры"""
    
    def __init__(self, camera_id: int = 0, fps: int = 30, width: int = 640, height: int = 480, jpeg_quality: int = 85):
        """
        Инициализация процессора веб-камеры
        
        Args:
            camera_id: ID камеры (обычно 0 для встроенной)
            fps: Частота кадров (рекомендуется 15-30)
            width: Ширина кадра (320, 640, 1280)
            height: Высота кадра (240, 480, 720)
            jpeg_quality: Качество сжатия JPEG 1-100 (ниже = быстрее, хуже качество)
        """
        self.camera_id = camera_id
        self.fps = fps
        self.width = width
        self.height = height
        self.jpeg_quality = jpeg_quality
        self.cap = None
        self.is_running = False
        self.start_time = None
    
    def start(self):
        """Запуск захвата видео"""
        self.cap = cv2.VideoCapture(self.camera_id)
        
        if not self.cap.isOpened():
            raise ValueError(f"Не удалось открыть камеру {self.camera_id}")
        
        # Настройка параметров
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        # Оптимизация буфера для уменьшения задержки
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        self.is_running = True
        self.start_time = time.time()
        
        # Получаем фактические значения
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"✓ Камера {self.camera_id} запущена")
        print(f"  Разрешение: {actual_width}x{actual_height}")
        print(f"  FPS: {actual_fps:.1f}")
        print(f"  Качество JPEG: {self.jpeg_quality}%")
    
    def get_frame(self) -> Optional[tuple]:
        """
        Получить текущий кадр
        
        Returns:
            Tuple (frame_image, frame_base64, timestamp) или None
        """
        if not self.is_running or self.cap is None:
            return None
        
        ret, frame = self.cap.read()
        
        if not ret:
            return None
        
        # Текущее время относительно старта
        timestamp = time.time() - self.start_time
        
        # Кодируем в base64 для AI с настраиваемым качеством
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
        _, buffer = cv2.imencode('.jpg', frame, encode_params)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return frame, frame_base64, timestamp
    
    def stop(self):
        """Остановка захвата"""
        self.is_running = False
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        print("✓ Камера остановлена")
    
    def show_frame(self, frame, title: str = "Video", text: str = None):
        """
        Показать кадр с наложенным текстом
        
        Args:
            frame: Кадр для отображения
            title: Заголовок окна
            text: Текст для наложения на кадр
        """
        if frame is None:
            return
        
        display_frame = frame.copy()
        
        # Наложение текста
        if text:
            lines = text.split('\n')
            y_offset = 30
            for line in lines:
                cv2.putText(
                    display_frame, 
                    line, 
                    (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )
                y_offset += 30
        
        cv2.imshow(title, display_frame)
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
