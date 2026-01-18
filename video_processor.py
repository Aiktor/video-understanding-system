"""
Обработчик видео для извлечения кадров
"""

import cv2
import base64
from typing import List, Dict, Any


class VideoProcessor:
    """Обработчик видео для извлечения кадров"""
    
    def __init__(self, video_path: str):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        
        if not self.cap.isOpened():
            raise ValueError(f"Не удалось открыть видео: {video_path}")
        
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration = self.total_frames / self.fps if self.fps > 0 else 0
    
    def extract_frames(self, interval_seconds: float = 2.0) -> List[Dict[str, Any]]:
        """
        Извлекает кадры из видео с заданным интервалом
        
        Args:
            interval_seconds: Интервал между кадрами в секундах
            
        Returns:
            Список словарей с данными кадров (timestamp, frame_data)
        """
        frames = []
        interval_frames = int(self.fps * interval_seconds)
        
        frame_number = 0
        while True:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = self.cap.read()
            
            if not ret:
                break
            
            timestamp = frame_number / self.fps
            
            # Кодируем кадр в base64 для отправки в API
            _, buffer = cv2.imencode('.jpg', frame)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            frames.append({
                'timestamp': timestamp,
                'frame_data': frame_base64,
                'frame_number': frame_number
            })
            
            frame_number += interval_frames
        
        return frames
    
    def close(self):
        """Закрывает видео файл"""
        self.cap.release()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
