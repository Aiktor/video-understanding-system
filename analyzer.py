"""
Функции анализа видео
"""

from datetime import timedelta
from typing import List

from models import (
    Instruction, 
    DetectedAction, 
    ActionMatch, 
    VideoAnalysisResult
)
from video_processor import VideoProcessor
from ai_agent import VideoAnalysisAgent
from utils import log


def analyze_video(
    video_path: str,
    instruction: Instruction,
    api_key: str,
    frame_interval: float = 2.0
) -> VideoAnalysisResult:
    """
    Основная функция анализа видео
    
    Args:
        video_path: Путь к видеофайлу
        instruction: Инструкция для сопоставления
        api_key: API ключ
        frame_interval: Интервал извлечения кадров в секундах
        
    Returns:
        Результат анализа видео
    """
    log(f"Анализ видео: {video_path}")
    
    # Извлекаем кадры
    log("Извлечение кадров...")
    with VideoProcessor(video_path) as vp:
        frames = vp.extract_frames(interval_seconds=frame_interval)
        total_duration = vp.duration
    
    log(f"Извлечено {len(frames)} кадров из {total_duration:.1f}с видео")
    
    # Инициализируем AI-агента
    log("Инициализация AI-агента...")
    agent = VideoAnalysisAgent(api_key=api_key)
    
    # Анализируем видео
    log("Анализ содержимого видео...")
    detected_actions = agent.analyze_video_sequence(frames, instruction)
    log(f"Обнаружено {len(detected_actions)} действий")
    
    # Сопоставляем с инструкцией
    log("Сопоставление с инструкцией...")
    action_matches = agent.match_with_instruction(detected_actions, instruction)
    
    # Генерируем общее описание видео
    log("Генерация общего описания видео...")
    video_summary = agent.generate_video_summary(detected_actions)
    
    # Определяем пропущенные шаги
    missing_steps = [
        match.step_number 
        for match in action_matches 
        if not match.matched
    ]
    
    # Определяем дополнительные действия (не из инструкции)
    matched_action_ids = {id(m.detected_action) for m in action_matches if m.detected_action}
    extra_actions = [a for a in detected_actions if id(a) not in matched_action_ids]
    
    # Генерируем резюме
    summary = generate_summary(
        instruction=instruction,
        action_matches=action_matches,
        detected_actions=detected_actions,
        missing_steps=missing_steps,
        total_duration=total_duration
    )
    
    return VideoAnalysisResult(
        video_path=video_path,
        total_duration=total_duration,
        video_summary=video_summary,
        detected_actions=detected_actions,
        action_matches=action_matches,
        missing_steps=missing_steps,
        extra_actions=extra_actions,
        summary=summary
    )


def generate_summary(
    instruction: Instruction,
    action_matches: List[ActionMatch],
    detected_actions: List[DetectedAction],
    missing_steps: List[int],
    total_duration: float
) -> str:
    """Генерирует текстовое резюме анализа"""
    
    summary_lines = [
        f"=== РЕЗЮМЕ АНАЛИЗА ВИДЕО ===",
        f"",
        f"Инструкция: {instruction.title}",
        f"Длительность видео: {timedelta(seconds=int(total_duration))}",
        f"",
        f"ВЫПОЛНЕННЫЕ ШАГИ ({len([m for m in action_matches if m.matched])}/{len(instruction.steps)}):"
    ]
    
    for match in action_matches:
        step = next(s for s in instruction.steps if s.step_number == match.step_number)
        
        if match.matched and match.detected_action:
            duration = match.detected_action.timestamp_end - match.detected_action.timestamp_start
            time_range = f"[{timedelta(seconds=int(match.detected_action.timestamp_start))} - {timedelta(seconds=int(match.detected_action.timestamp_end))}]"
            summary_lines.append(
                f"✓ Шаг {match.step_number}: {step.description} {time_range} ({duration:.1f}с)"
            )
        else:
            summary_lines.append(
                f"✗ Шаг {match.step_number}: {step.description} - НЕ ВЫПОЛНЕНО"
            )
    
    if missing_steps:
        summary_lines.append(f"")
        summary_lines.append(f"ПРОПУЩЕННЫЕ ШАГИ: {', '.join(map(str, missing_steps))}")
    
    summary_lines.append(f"")
    summary_lines.append(f"Всего обнаружено действий: {len(detected_actions)}")
    
    return "\n".join(summary_lines)
