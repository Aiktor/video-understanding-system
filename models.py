"""
Pydantic модели для структурирования данных
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class InstructionStep(BaseModel):
    """Шаг инструкции с описанием действия"""
    step_number: int = Field(description="Номер шага")
    description: str = Field(description="Описание действия")
    expected_duration_seconds: Optional[float] = Field(
        default=None, 
        description="Ожидаемая длительность в секундах (может быть дробным числом)"
    )
    critical: bool = Field(
        default=False, 
        description="Является ли шаг критически важным"
    )


class Instruction(BaseModel):
    """Инструкция с последовательностью шагов"""
    title: str = Field(description="Название инструкции")
    steps: List[InstructionStep] = Field(description="Список шагов")


class DetectedAction(BaseModel):
    """Обнаруженное действие в видео"""
    description: str = Field(description="Описание обнаруженного действия")
    timestamp_start: float = Field(description="Время начала в секундах")
    timestamp_end: float = Field(description="Время окончания в секундах")
    confidence: float = Field(
        ge=0.0, 
        le=1.0, 
        description="Уверенность определения (0-1)"
    )


class ActionMatch(BaseModel):
    """Сопоставление действия с инструкцией"""
    step_number: int = Field(description="Номер шага инструкции")
    matched: bool = Field(description="Было ли действие выполнено")
    detected_action: Optional[DetectedAction] = Field(
        default=None, 
        description="Обнаруженное действие"
    )
    deviation: Optional[str] = Field(
        default=None, 
        description="Отклонение от инструкции"
    )


class VideoAnalysisResult(BaseModel):
    """Результат анализа видео"""
    video_path: str = Field(description="Путь к видеофайлу")
    total_duration: float = Field(description="Общая длительность видео в секундах")
    video_summary: str = Field(description="Описание видео от AI")
    detected_actions: List[DetectedAction] = Field(description="Обнаруженные действия")
    action_matches: List[ActionMatch] = Field(description="Сопоставление с инструкцией")
    missing_steps: List[int] = Field(description="Пропущенные шаги")
    extra_actions: List[DetectedAction] = Field(description="Дополнительные действия")
    summary: str = Field(description="Краткое резюме анализа")
