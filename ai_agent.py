"""
AI-агент для анализа видео с помощью LangChain
"""

import os
import re
from typing import List, Optional, Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from models import DetectedAction, Instruction, ActionMatch
from utils import log


class VideoAnalysisAgent:
    """AI-агент для анализа видео с помощью LangChain"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-5-nano-2025-08-07"): # "gpt-5-nano-2025-08-07" "gpt-4o-mini"
        """
        Инициализация агента
        
        Args:
            api_key: API ключ (опционально, можно использовать PROXY_API_KEY из .env)
            model: Модель для использования (должна поддерживать vision)
        """
        self.llm = ChatOpenAI(
            model=model,
            base_url=os.getenv("PROXY_BASE_URL"),
            api_key=api_key or os.getenv("PROXY_API_KEY"),
            temperature=0.1
        )
    
    def analyze_frame(self, frame_base64: str, timestamp: float) -> str:
        """
        Анализирует отдельный кадр
        
        Args:
            frame_base64: Кадр в формате base64
            timestamp: Временная метка кадра
            
        Returns:
            Описание действия в кадре
        """
        messages = [
            SystemMessage(content="Ты эксперт по анализу видео. Опиши что происходит в этом кадре кратко и точно."),
            HumanMessage(
                content=[
                    {"type": "text", "text": f"Временная метка: {timestamp:.2f}с. Что происходит в этом кадре?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame_base64}"}}
                ]
            )
        ]
        
        response = self.llm.invoke(messages)
        return response.content
    
    def generate_video_summary(self, detected_actions: List[DetectedAction]) -> str:
        """
        Генерирует общее описание видео
        
        Args:
            detected_actions: Список обнаруженных действий
            
        Returns:
            Текстовое описание видео
        """
        actions_text = "\n".join([
            f"- [{a.timestamp_start:.1f}s - {a.timestamp_end:.1f}s] {a.description}"
            for a in detected_actions
        ])
        
        prompt = f"""Analyze this sequence of actions from a video and create a detailed description of what is happening.

Detected actions:
{actions_text}

Provide a coherent narrative description of the video content, combining all actions into a logical story.
Describe:
1. What kind of process or activity is shown
2. Main stages and their sequence
3. Overall impression of what is happening

Answer in Russian."""
        
        messages = [
            SystemMessage(content="You are an expert at analyzing videos and creating narrative descriptions."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        return response.content
    
    def analyze_video_sequence(
        self, 
        frames: List[Dict[str, Any]], 
        instruction: Optional[Instruction] = None
    ) -> List[DetectedAction]:
        """
        Анализирует последовательность кадров и определяет действия
        
        Args:
            frames: Список кадров с временными метками
            instruction: Инструкция для сопоставления
            
        Returns:
            Список обнаруженных действий
        """
        detected_actions = []
        
        # Создаем промпт для анализа последовательности
        instruction_context = ""
        if instruction:
            instruction_context = f"\n\nИнструкция для сопоставления:\n"
            for step in instruction.steps:
                instruction_context += f"{step.step_number}. {step.description}\n"
        
        # Анализируем кадры группами для определения действий
        total_batches = (len(frames) + 2) // 3
        
        for batch_idx, i in enumerate(range(0, len(frames), 3), 1):
            # Прогресс каждые 20 кадров
            if batch_idx % 20 == 0 or batch_idx == 1:
                log(f"Обработано батчей: {batch_idx}/{total_batches} ({i}/{len(frames)} кадров)")
            
            batch = frames[i:i+3]
            
            # Формируем сообщение с несколькими кадрами
            content = [
                {
                    "type": "text", 
                    "text": f"""Проанализируй эти кадры из видео и определи какое действие выполняется.
                    {instruction_context}
                    
                    Опиши действие кратко и укажи, если видно его начало или завершение."""
                }
            ]
            
            for frame in batch:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{frame['frame_data']}",
                        "detail": "low"
                    }
                })
                content.append({
                    "type": "text",
                    "text": f"[Кадр на {frame['timestamp']:.1f}с]"
                })
            
            messages = [
                SystemMessage(content="Ты эксперт по анализу видео производственных процессов."),
                HumanMessage(content=content)
            ]
            
            response = self.llm.invoke(messages)
            description = response.content
            
            # Создаем обнаруженное действие
            timestamp_start = batch[0]['timestamp']
            timestamp_end = batch[-1]['timestamp']
            
            detected_actions.append(DetectedAction(
                description=description,
                timestamp_start=timestamp_start,
                timestamp_end=timestamp_end,
                confidence=0.8
            ))
        
        # Объединяем похожие последовательные действия
        merged_actions = self._merge_similar_actions(detected_actions)
        
        return merged_actions
    
    def _merge_similar_actions(self, actions: List[DetectedAction]) -> List[DetectedAction]:
        """Объединяет похожие последовательные действия"""
        if not actions:
            return []
        
        merged = [actions[0]]
        
        for action in actions[1:]:
            last_action = merged[-1]
            time_gap = action.timestamp_start - last_action.timestamp_end
            
            if time_gap < 10 and self._are_similar_descriptions(
                last_action.description, 
                action.description
            ):
                last_action.timestamp_end = action.timestamp_end
            else:
                merged.append(action)
        
        return merged
    
    def _are_similar_descriptions(self, desc1: str, desc2: str) -> bool:
        """Проверяет схожесть описаний"""
        words1 = set(desc1.lower().split())
        words2 = set(desc2.lower().split())
        
        if not words1 or not words2:
            return False
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union > 0.5
    
    def match_with_instruction(
        self, 
        detected_actions: List[DetectedAction],
        instruction: Instruction
    ) -> List[ActionMatch]:
        """
        Сопоставляет обнаруженные действия с инструкцией
        
        Args:
            detected_actions: Обнаруженные в видео действия
            instruction: Инструкция с ожидаемыми шагами
            
        Returns:
            Список сопоставлений
        """
        matches = []
        
        # Формируем промпт для сопоставления
        actions_text = "\n".join([
            f"- [{a.timestamp_start:.1f}с - {a.timestamp_end:.1f}с] {a.description}"
            for a in detected_actions
        ])
        
        steps_text = "\n".join([
            f"{s.step_number}. {s.description}"
            for s in instruction.steps
        ])
        
        prompt = f"""Сопоставь обнаруженные действия в видео с шагами инструкции.
        
Инструкция:
{steps_text}

Обнаруженные действия:
{actions_text}

Для каждого шага инструкции определи:
1. Был ли он выполнен (да/нет) - даже если действие описано другими словами, но по смыслу соответствует
2. Какое обнаруженное действие соответствует шагу (укажи временной отрезок)
3. Есть ли отклонения от инструкции

ВАЖНО: Сопоставляй по СМЫСЛУ, а не по точным словам. Например:
- "Приготовление раствора" = "смешивание" = "замес смеси"
- "Подготовка формы" = "очистка формы" = "смазка формы"

Ответ дай в формате: для каждого шага напиши одну строку:
Шаг N: [DA/NET] - [временной отрезок] - [комментарий]

Пример:
Шаг 1: DA - [0.0с-15.5с] - Выполнено подготовка формы
Шаг 2: NET - - Действие не обнаружено"""
        
        messages = [
            SystemMessage(content="Ты эксперт по анализу соответствия действий инструкциям."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        llm_response = response.content
        
        log(f"LLM ответ по сопоставлению:\n{llm_response}")
        
        # Парсим ответ LLM
        for step in instruction.steps:
            matched = False
            best_match = None
            deviation = None
            
            pattern = rf"Шаг {step.step_number}:\s*(DA|NET|YES|NO|ДА|НЕТ)\s*-\s*\[?([^\]\-]+)?\]?\s*-?\s*(.*)"
            regex_match = re.search(pattern, llm_response, re.IGNORECASE | re.MULTILINE)
            
            if regex_match:
                status = regex_match.group(1).upper()
                matched = status in ['DA', 'YES', 'ДА']
                time_range = regex_match.group(2)
                comment = regex_match.group(3) if regex_match.group(3) else None
                
                log(f"Шаг {step.step_number}: status={status}, matched={matched}, time_range={time_range}")
                
                if matched and time_range:
                    time_match = re.search(r'([0-9.]+)\s*с?\s*(?:-\s*([0-9.]+)\s*с?)?', time_range)
                    if time_match:
                        start_time = float(time_match.group(1))
                        end_time = float(time_match.group(2)) if time_match.group(2) else start_time
                        
                        log(f"  → Парсинг времени: start={start_time}, end={end_time}")
                        
                        best_overlap = 0
                        for action in detected_actions:
                            overlap_start = max(action.timestamp_start, start_time)
                            overlap_end = min(action.timestamp_end, end_time)
                            overlap = max(0, overlap_end - overlap_start)
                            
                            if overlap > best_overlap:
                                best_overlap = overlap
                                best_match = action
                        
                        if not best_match or start_time == end_time:
                            min_distance = float('inf')
                            for action in detected_actions:
                                if action.timestamp_start <= start_time <= action.timestamp_end:
                                    best_match = action
                                    break
                                distance = min(
                                    abs(action.timestamp_start - start_time),
                                    abs(action.timestamp_end - end_time)
                                )
                                if distance < min_distance and distance < 30:
                                    min_distance = distance
                                    best_match = action
                        
                        log(f"  → Найдено действие: {best_match.timestamp_start if best_match else 'None'}-{best_match.timestamp_end if best_match else 'None'}")
                
                if not matched and comment:
                    deviation = comment.strip()
            else:
                best_score = 0
                for action in detected_actions:
                    score = self._calculate_match_score(step.description, action.description)
                    if score > best_score:
                        best_score = score
                        best_match = action
                matched = best_score > 0.25
                if not matched:
                    deviation = "Действие не обнаружено"
            
            action_match = ActionMatch(
                step_number=step.step_number,
                matched=matched,
                detected_action=best_match if matched else None,
                deviation=deviation
            )
            matches.append(action_match)
        
        return matches
    
    def _calculate_match_score(self, instruction_desc: str, action_desc: str) -> float:
        """Вычисляет степень соответствия действия шагу инструкции"""
        words1 = set(instruction_desc.lower().split())
        words2 = set(action_desc.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union
