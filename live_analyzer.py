"""
Анализатор видеопотока в реальном времени с проверкой соблюдения инструкции
"""

import time
from typing import Optional
from datetime import datetime, timedelta

from models import Instruction, DetectedAction
from ai_agent import VideoAnalysisAgent
from utils import log


class LiveAnalyzer:
    """Анализатор видеопотока в реальном времени"""
    
    def __init__(
        self, 
        instruction: Instruction,
        api_key: str,
        analysis_interval: float = 5.0
    ):
        """
        Инициализация анализатора
        
        Args:
            instruction: Инструкция с шагами
            api_key: API ключ
            analysis_interval: Интервал между анализами в секундах
        """
        self.instruction = instruction
        self.agent = VideoAnalysisAgent(api_key=api_key)
        self.analysis_interval = analysis_interval
        
        # Состояние отслеживания
        self.current_step = 0  # Ожидаемый следующий шаг (0-based)
        self.completed_steps = []
        self.last_analysis_time = 0
        self.current_action = None
        self.warnings = []
        
        # История действий
        self.action_history = []
        
        log(f"Инициализирован анализатор для: {instruction.title}")
        log(f"Всего шагов: {len(instruction.steps)}")
    
    def should_analyze(self, current_time: float) -> bool:
        """Проверяет, нужно ли делать анализ"""
        return (current_time - self.last_analysis_time) >= self.analysis_interval
    
    def analyze_frame(self, frame_base64: str, timestamp: float) -> dict:
        """
        Анализирует текущий кадр
        
        Args:
            frame_base64: Кадр в base64
            timestamp: Временная метка
            
        Returns:
            Словарь со статусом анализа
        """
        # Анализируем действие в кадре
        description = self.agent.analyze_frame(frame_base64, timestamp)
        
        self.current_action = DetectedAction(
            description=description,
            timestamp_start=timestamp,
            timestamp_end=timestamp,
            confidence=0.8
        )
        
        self.action_history.append(self.current_action)
        
        # Проверяем соответствие текущему ожидаемому шагу
        result = self._check_instruction_compliance()
        
        self.last_analysis_time = timestamp
        
        return result
    
    def _check_instruction_compliance(self) -> dict:
        """
        Проверяет соответствие текущего действия инструкции
        
        Returns:
            Словарь с результатами проверки
        """
        if not self.current_action:
            return {
                'status': 'waiting',
                'message': 'Ожидание действий...',
                'current_step': None,
                'warnings': []
            }
        
        # Если все шаги выполнены
        if self.current_step >= len(self.instruction.steps):
            return {
                'status': 'completed',
                'message': '✓ Все шаги инструкции выполнены!',
                'current_step': None,
                'warnings': self.warnings,
                'completed': True
            }
        
        # Получаем текущий ожидаемый шаг
        expected_step = self.instruction.steps[self.current_step]
        
        # Проверяем соответствие действия ожидаемому шагу
        match_score = self.agent._calculate_match_score(
            expected_step.description,
            self.current_action.description
        )
        
        log(f"Текущее действие: {self.current_action.description[:50]}...")
        log(f"Ожидается шаг {expected_step.step_number}: {expected_step.description}")
        log(f"Совпадение: {match_score:.2f}")
        
        # Если действие соответствует ожидаемому шагу
        if match_score > 0.3:
            self.completed_steps.append(expected_step.step_number)
            self.current_step += 1
            
            message = f"✓ Шаг {expected_step.step_number} выполнен: {expected_step.description}"
            log(message)
            
            return {
                'status': 'step_completed',
                'message': message,
                'current_step': expected_step.step_number,
                'expected_next': self.instruction.steps[self.current_step].step_number if self.current_step < len(self.instruction.steps) else None,
                'warnings': [],
                'progress': f"{len(self.completed_steps)}/{len(self.instruction.steps)}"
            }
        
        # Проверяем, не выполняется ли шаг не по порядку
        for i, step in enumerate(self.instruction.steps):
            if i <= self.current_step:  # Пропускаем уже выполненные
                continue
            
            score = self.agent._calculate_match_score(
                step.description,
                self.current_action.description
            )
            
            if score > 0.3:
                warning = f"⚠ ВНИМАНИЕ: Выполняется шаг {step.step_number} вместо шага {expected_step.step_number}!"
                self.warnings.append(warning)
                log(warning)
                
                return {
                    'status': 'warning',
                    'message': warning,
                    'current_step': expected_step.step_number,
                    'detected_step': step.step_number,
                    'warnings': [warning],
                    'progress': f"{len(self.completed_steps)}/{len(self.instruction.steps)}"
                }
        
        # Действие не соответствует ни одному шагу
        return {
            'status': 'in_progress',
            'message': f"Ожидается: Шаг {expected_step.step_number} - {expected_step.description}",
            'current_step': expected_step.step_number,
            'warnings': [],
            'progress': f"{len(self.completed_steps)}/{len(self.instruction.steps)}"
        }
    
    def get_status_display(self, result: dict) -> str:
        """
        Форматирует статус для отображения
        
        Args:
            result: Результат анализа
            
        Returns:
            Строка для отображения
        """
        lines = []
        lines.append(f"=== {self.instruction.title} ===")
        lines.append(f"Прогресс: {result.get('progress', '0/0')}")
        lines.append("")
        
        if result.get('status') == 'completed':
            lines.append("✓✓✓ ВСЕ ШАГИ ВЫПОЛНЕНЫ ✓✓✓")
        else:
            lines.append(result.get('message', ''))
        
        if result.get('warnings'):
            lines.append("")
            for warning in result['warnings']:
                lines.append(warning)
        
        # Показываем выполненные шаги
        if self.completed_steps:
            lines.append("")
            lines.append("Выполнено:")
            for step_num in self.completed_steps:
                step = next(s for s in self.instruction.steps if s.step_number == step_num)
                lines.append(f"  ✓ {step_num}. {step.description}")
        
        return "\n".join(lines)
    
    def get_summary(self) -> str:
        """Возвращает итоговое резюме"""
        lines = []
        lines.append("\n" + "="*60)
        lines.append("ИТОГОВОЕ РЕЗЮМЕ")
        lines.append("="*60)
        lines.append(f"Инструкция: {self.instruction.title}")
        lines.append(f"Выполнено шагов: {len(self.completed_steps)}/{len(self.instruction.steps)}")
        lines.append("")
        
        for step in self.instruction.steps:
            if step.step_number in self.completed_steps:
                lines.append(f"✓ Шаг {step.step_number}: {step.description}")
            else:
                lines.append(f"✗ Шаг {step.step_number}: {step.description} - НЕ ВЫПОЛНЕНО")
        
        if self.warnings:
            lines.append("")
            lines.append("ПРЕДУПРЕЖДЕНИЯ:")
            for warning in self.warnings:
                lines.append(f"  {warning}")
        
        lines.append("")
        lines.append(f"Всего действий зафиксировано: {len(self.action_history)}")
        
        return "\n".join(lines)
