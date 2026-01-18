"""
Счетчик приседаний с веб-камеры в реальном времени
"""

import cv2
from typing import Optional
from enum import Enum

from ai_agent import VideoAnalysisAgent
from webcam_processor import WebcamProcessor
from utils import log


class SquatState(Enum):
    """Состояния приседания"""
    STANDING = "стоит"
    SQUATTING = "приседает"
    UNKNOWN = "неизвестно"


class SquatsCounter:
    """Счетчик приседаний"""
    
    def __init__(self, api_key: str, analysis_interval: float = 1.0):
        """
        Инициализация счетчика
        
        Args:
            api_key: API ключ
            analysis_interval: Интервал между анализами в секундах
        """
        self.agent = VideoAnalysisAgent(api_key=api_key)
        self.analysis_interval = analysis_interval
        
        # Счетчики
        self.squat_count = 0
        self.current_state = SquatState.UNKNOWN
        self.last_analysis_time = 0
        
        log("Счетчик приседаний инициализирован")
        log(f"Интервал анализа: {analysis_interval}с")
    
    def should_analyze(self, current_time: float) -> bool:
        """Проверяет, нужно ли делать анализ"""
        return (current_time - self.last_analysis_time) >= self.analysis_interval
    
    def analyze_frame(self, frame_base64: str, timestamp: float) -> dict:
        """
        Анализирует кадр и определяет состояние
        
        Args:
            frame_base64: Кадр в base64
            timestamp: Временная метка
            
        Returns:
            Словарь с результатами анализа
        """
        # Специальный промпт для определения состояния приседания
        state = self._detect_squat_state(frame_base64)
        
        # Переход из стоя в присед не считаем
        # Переход из приседа в стоя = +1 приседание
        if self.current_state == SquatState.SQUATTING and state == SquatState.STANDING:
            self.squat_count += 1
            log(f"✓ ПРИСЕДАНИЕ #{self.squat_count}")
            print(f"\n{'='*50}")
            print(f"  🏋️  ПРИСЕДАНИЙ ВЫПОЛНЕНО: {self.squat_count}")
            print(f"{'='*50}\n")
        
        self.current_state = state
        self.last_analysis_time = timestamp
        
        return {
            'count': self.squat_count,
            'state': state.value,
            'timestamp': timestamp
        }
    
    def _detect_squat_state(self, frame_base64: str) -> SquatState:
        """
        Определяет состояние человека на кадре
        
        Args:
            frame_base64: Кадр в base64
            
        Returns:
            Состояние приседания
        """
        prompt = """Проанализируй изображение и определи положение человека.

Ответь ОДНИМ словом:
- СТОИТ - если человек стоит прямо, ноги выпрямлены
- ПРИСЕДАЕТ - если человек в положении приседа (колени согнуты, бедра параллельны полу или ниже)
- НЕТ - если человека не видно или положение неясно

Отвечай ТОЛЬКО одним из этих слов, без пояснений."""

        from langchain_core.messages import HumanMessage, SystemMessage
        
        messages = [
            SystemMessage(content="Ты эксперт по анализу положения тела человека. Отвечай кратко и точно."),
            HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame_base64}"}}
                ]
            )
        ]
        
        response = self.agent.llm.invoke(messages)
        answer = response.content.strip().upper()
        
        log(f"AI ответ: {answer}")
        
        if "СТОИТ" in answer or "STANDING" in answer:
            return SquatState.STANDING
        elif "ПРИСЕДАЕТ" in answer or "ПРИСЕД" in answer or "SQUAT" in answer:
            return SquatState.SQUATTING
        else:
            return SquatState.UNKNOWN
    
    def get_display_text(self, result: dict) -> str:
        """
        Форматирует текст для отображения на видео
        
        Args:
            result: Результат анализа
            
        Returns:
            Строка для отображения
        """
        lines = []
        lines.append("=== СЧЕТЧИК ПРИСЕДАНИЙ ===")
        lines.append(f"Всего: {result['count']}")
        lines.append(f"Состояние: {result['state']}")
        
        return "\n".join(lines)
    
    def get_summary(self) -> str:
        """Возвращает итоговую статистику"""
        lines = []
        lines.append("\n" + "="*60)
        lines.append("ИТОГОВАЯ СТАТИСТИКА")
        lines.append("="*60)
        lines.append(f"Всего приседаний выполнено: {self.squat_count}")
        lines.append("="*60)
        
        return "\n".join(lines)
