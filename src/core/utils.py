import html
import re
from typing import List, Optional

"""
utils.py
Различные функции утилиты:
- Функция для экранизации html кода
- Обработка поля advantages из бд
"""

CYR_TO_LAT   = str.maketrans("АВСЕНКМОРТХМ", "ABCEHKMOPTHM")
LAT_TO_CYR   = str.maketrans("ABCEHKMOPTXM", "АВСЕНКМОРТХМ")
SENTENCES_RE = re.compile(r"""[.;]\s+(?=[А-ЯA-Z0-9•-])""", re.VERBOSE)

def esc(s: Optional[str]) -> str:
    """
    Экранизирование строк, для безопастного отображения в HTML
    """
    return  html.escape(s) if s else "-"

def validate_html_tags(text: str) -> bool:
    """
    Проверяет, что все HTML теги правильно закрыты
    """
    # Ищем все открывающие и закрывающие теги
    open_tags = re.findall(r'<([^/][^>]*)>', text)
    close_tags = re.findall(r'</([^>]*)>', text)
    
    # Создаем счетчики для каждого типа тегов
    tag_counts = {}
    
    # Считаем открывающие теги
    for tag in open_tags:
        tag_name = tag.split()[0].lower()  # Берем только имя тега, игнорируем атрибуты
        tag_counts[tag_name] = tag_counts.get(tag_name, 0) + 1
    
    # Вычитаем закрывающие теги
    for tag in close_tags:
        tag_name = tag.strip().lower()
        tag_counts[tag_name] = tag_counts.get(tag_name, 0) - 1
    
    # Проверяем, что все теги закрыты
    for tag_name, count in tag_counts.items():
        if count != 0:
            print(f"HTML validation error: Tag <{tag_name}> not properly closed. Count: {count}")
            return False
    
    return True

def fix_html_tags(text: str) -> str:
    """
    Пытается исправить незакрытые HTML теги
    """
    if not validate_html_tags(text):
        # Простое исправление: закрываем все bold теги в конце
        open_b_count = text.count('<b>') - text.count('</b>')
        if open_b_count > 0:
            text += '</b>' * open_b_count
    
    return text

def truncate_caption(text: str, max_length: int = 1020) -> str:
    """
    Безопасно обрезает текст для caption Telegram до указанной длины.
    Лимит caption в Telegram: 1024 символа, оставляем запас.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def split_advantages(raw: Optional[str]) -> List[str]:
    """
    Обработка поля из бд "advantages".
    Убираем все префиксы-буллиты и возвращаем чистый текст
    """
    if not raw:
        return []
    text = raw.strip("•-–— ").replace("\n", " ").strip()

    # делим текст на предложения по символамт точки и точки с запятой, за которым следует пробел и заглавная/цифрой
    cand = SENTENCES_RE.split(text)
    items = []
    for s in cand:
        s = s.strip(" .;—•-–— ").strip()
        if s: 
            items.append(s)
    
    return items

def format_advantages_for_telegram(advantages_text: Optional[str]) -> str:
    """
    Форматирует преимущества для отображения в Telegram с использованием bullet points.
    Поддерживает два формата:
    1. Через точку с запятой: "преимущество1; преимущество2; преимущество3"
    2. Через точки (предложения): "Первое преимущество. Второе преимущество. Третье преимущество."
    """
    if not advantages_text or not advantages_text.strip():
        return ""
    
    text = advantages_text.strip()
    
    # Сначала проверяем, есть ли точка с запятой (старый формат)
    if ';' in text:
        items = [item.strip() for item in text.split(';') if item.strip()]
    else:
        # Используем парсинг по точкам (новый формат)
        items = split_advantages(text)
    
    if not items:
        return text
    
    if len(items) == 1:
        # Если только одно преимущество, выводим без буллета
        return items[0]
    
    # Форматируем как список с буллетами
    formatted_lines = []
    for item in items:
        formatted_lines.append(f"• {item}")
    
    return '\n'.join(formatted_lines)

