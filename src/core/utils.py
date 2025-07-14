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


