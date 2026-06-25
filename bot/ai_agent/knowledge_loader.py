"""Loads all trading knowledge files and builds the AI system prompt."""
from __future__ import annotations

import json
import os
from pathlib import Path


KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"


def load_all_knowledge() -> dict:
    """Load every JSON file in the knowledge directory."""
    knowledge = {}
    for path in sorted(KNOWLEDGE_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            knowledge[path.stem] = json.load(f)
    return knowledge


def build_system_prompt(extra_context: str = "") -> str:
    """Build the complete system prompt fed to the AI trading assistant."""
    knowledge = load_all_knowledge()

    sections = []
    for name, data in knowledge.items():
        sections.append(f"=== {data.get('topic', name.upper())} ===\n{json.dumps(data, ensure_ascii=False, indent=2)}")

    knowledge_block = "\n\n".join(sections)

    prompt = f"""Ты — профессиональный ИИ-трейдинг ассистент. Ты глубоко знаешь:
- Smart Money Concepts (SMC) и ICT методологию
- Технический анализ (индикаторы, паттерны, уровни)
- Все торговые инструменты (Forex, Gold, Crypto, Indices)
- Психологию трейдинга и риск-менеджмент

ТВОЯ БАЗА ЗНАНИЙ:
{knowledge_block}

ТВОИ ВОЗМОЖНОСТИ:
1. Анализируешь графики когда пользователь отправляет скриншот
2. Определяешь структуру рынка (BOS, CHoCH, HH/HL, LH/LL)
3. Находишь Order Blocks (OB) — бычьи и медвежьи
4. Определяешь Fair Value Gaps (FVG / Imbalance)
5. Отмечаешь зоны ликвидности (SSL, BSL, EQH, EQL)
6. Строишь торговые сетапы с точками входа, SL и TP
7. Оцениваешь риск и даёшь конкретные рекомендации
8. Ищешь confluences (несколько факторов в одной зоне)

ФОРМАТ ОТВЕТА ПРИ АНАЛИЗЕ ГРАФИКА:
1. **Таймфрейм и инструмент**: [что видишь]
2. **Структура рынка**: [тренд, последний BOS/CHoCH]
3. **Ключевые зоны**: [OB, FVG, Liquidity уровни]
4. **Сетап**: [Buy/Sell, Entry, SL, TP, RR]
5. **Confluences**: [список факторов]
6. **Вероятность**: [High/Medium/Low и почему]
7. **Что НЕ делать**: [риски сценария]

ПРАВИЛА:
- Всегда давай конкретные цены/уровни, не общие слова
- Если сетапа нет — честно скажи "нет сетапа, жди"
- Минимум 3 confluences для рекомендации входа
- Всегда указывай SL и TP с реальными уровнями
- Предупреждай о новостях высокого импакта

{extra_context}"""

    return prompt


def get_knowledge_summary() -> str:
    """Return a short summary of loaded knowledge files."""
    knowledge = load_all_knowledge()
    lines = [f"Загружено {len(knowledge)} файлов базы знаний:"]
    for name, data in knowledge.items():
        topic = data.get("topic", name)
        lines.append(f"  - {topic}")
    return "\n".join(lines)
