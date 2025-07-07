import html
import re
from typing import List, Optional

CYR_TO_LAT   = str.maketrans("АВСЕНКМОРТХ", "ABCEHKMOPTH")
LAT_TO_CYR   = str.maketrans("ABCEHKMOPTX", "АВСЕНКМОРТХ")
SENTENCES_RE = re.compile(r"""[.;]\s+(?=[А-ЯA-Z0-9•-])""", re.VERBOSE)

def esc(s: Optional[str]) -> str:
    """
    Making HTML symbols save ( showing &, <>, "")
    """
    return  html.escape(s) if s else "-"

def split_advantages(raw: Optional[str]) -> List[str]:
    """
    Converting text from advantages table from db in line with markers
    """
    if not raw:
        return []
    text = raw.strip("•-–— ").replace("\n", " ").strip()

    cand = SENTENCES_RE.split(text)
    items = []
    for s in cand:
        s = s.strip(" .;—")
        if s: 
            items.append(s)
    
    return items


