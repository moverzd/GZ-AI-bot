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

