import re


AMBIGUITY_KEYWORDS = [
    "easy", "easily", "fast", "quick", "quickly", "slow", "slowly",
    "simple", "simply", "intuitive", "user-friendly", "user friendly", "self-explanatory",
    "robust", "reliable", "sufficient", "sufficiently", "optimal", "optimally",
    "readable", "understandable", "clear", "clearly", "appropriate", "appropriately",
    "adequate", "adequately", "flexible", "scalable", "convenient",
    "many", "few", "several", "some", "most", "various", "numerous",
    "better", "improved", "enhanced", "high-quality", "high quality",
    "soon", "later", "frequently", "occasionally", "periodically", "regularly",
]

WEAK_VERB_KEYWORDS = [
    "may", "can", "could", "might", "should", "would",
    "support", "supports", "supported",
    "handle", "handles", "handled", "handling",
    "manage", "manages", "managed", "managing",
    "process", "processes", "processed", "processing",
    "ensure", "ensures", "ensured",
    "allow", "allows", "allowed",
    "be able to", "is able to", "are able to",
    "is permitted to", "are permitted to",
]


def _build_keyword_regex(keywords):
    escaped = [re.escape(kw) for kw in keywords]
    return re.compile(r"(?<![a-zA-Z])(" + "|".join(escaped) + r")(?![a-zA-Z])", re.IGNORECASE)


AMB_REGEX = _build_keyword_regex(AMBIGUITY_KEYWORDS)
WV_REGEX = _build_keyword_regex(WEAK_VERB_KEYWORDS)

INC_REGEX = re.compile(
    r"<[a-zA-Z][^>]*>"
    r"|\bTBD\b|\bTODO\b|\bFIXME\b|\bXXX\b"
    r"|\bN/?A\b"
    r"|\[(?:INSERT|TBD|TODO|FIXME)[^\]]*\]"
    r"|\.{3,}",
    re.IGNORECASE,
)

NEGATION_PATTERNS = [
    r"\bnot\b", r"\bnever\b", r"\bcannot\b", r"\bcan't\b",
    r"\bwon't\b", r"\bwouldn't\b", r"\bdo not\b", r"\bdoes not\b",
    r"\bshall not\b", r"\bmust not\b", r"\bno longer\b",
]
NEGATION_RE = re.compile("|".join(NEGATION_PATTERNS), re.IGNORECASE)

QTY_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*"
    r"(seconds?|secs?|ms|milliseconds?|minutes?|mins?|hours?|hrs?|days?|weeks?|months?|years?|"
    r"%|percent|tb|gb|mb|kb|terabytes?|gigabytes?|megabytes?|kilobytes?|\$|dollars?|usd)",
    re.IGNORECASE,
)


def rule_incompleteness(text):
    return int(bool(INC_REGEX.search(text)))


def _extract_quantities(text):
    q = {}
    for val, unit in QTY_RE.findall(text):
        q.setdefault(unit.lower().rstrip("s"), set()).add(float(val))
    return q


def detect_conflicts(t1, t2):
    conflicts = []
    if bool(NEGATION_RE.search(t1)) != bool(NEGATION_RE.search(t2)):
        conflicts.append("negation")
    q1, q2 = _extract_quantities(t1), _extract_quantities(t2)
    if any(q1[u] != q2[u] for u in set(q1) & set(q2)):
        conflicts.append("numerical")
    return conflicts
