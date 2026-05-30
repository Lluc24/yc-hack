"""Utilities for converting spoken number/date text to formatted values.

Used in bot-intake.py fill_form_field to normalise patient speech before
storing it in the intake form.
"""

import re
from loguru import logger

# ── Digit-by-digit lookup (phone, IDs, group numbers) ──────────────────────

_DIGIT_MAP: dict[str, str] = {
    "zero": "0", "oh": "0", "o": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
}

_SEPARATOR_WORDS = {"dash", "hyphen", "minus", "slash", "dot", "period", "space"}

# ── Number words for year/day parsing ──────────────────────────────────────

_ONES: dict[str, int] = {
    "zero": 0, "oh": 0,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

_ORDINALS: dict[str, int] = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
    "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
    "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18,
    "nineteenth": 19, "twentieth": 20,
    "twenty-first": 21, "twenty first": 21,
    "twenty-second": 22, "twenty second": 22,
    "twenty-third": 23, "twenty third": 23,
    "twenty-fourth": 24, "twenty fourth": 24,
    "twenty-fifth": 25, "twenty fifth": 25,
    "twenty-sixth": 26, "twenty sixth": 26,
    "twenty-seventh": 27, "twenty seventh": 27,
    "twenty-eighth": 28, "twenty eighth": 28,
    "twenty-ninth": 29, "twenty ninth": 29,
    "thirtieth": 30,
    "thirty-first": 31, "thirty first": 31,
}

_MONTHS: dict[str, str] = {
    "january": "01", "jan": "01",
    "february": "02", "feb": "02",
    "march": "03", "mar": "03",
    "april": "04", "apr": "04",
    "may": "05",
    "june": "06", "jun": "06",
    "july": "07", "jul": "07",
    "august": "08", "aug": "08",
    "september": "09", "sep": "09", "sept": "09",
    "october": "10", "oct": "10",
    "november": "11", "nov": "11",
    "december": "12", "dec": "12",
}

# ── Public API ──────────────────────────────────────────────────────────────


def parse_digits(text: str) -> str:
    """Convert spoken digit sequence to a numeric string.

    Each word is mapped to a single digit. Separator words become '-'.
    Already-numeric tokens are kept as-is.

    Examples:
        "one three four eight"                       → "1348"
        "five five five dash eight six seven"        → "555-867"
        "oh oh one"                                  → "001"
        "555 867 5309"                               → "5558675309"
    """
    clean = text.lower().strip()
    tokens = re.split(r"[\s,]+", clean)
    result: list[str] = []
    for tok in tokens:
        tok = tok.strip("-.,")
        if not tok:
            continue
        if tok in _DIGIT_MAP:
            result.append(_DIGIT_MAP[tok])
        elif tok in _SEPARATOR_WORDS:
            result.append("-")
        elif re.match(r"^\d+$", tok):
            result.extend(list(tok))  # "555" → ['5','5','5']
        elif tok in ("-",):
            result.append("-")
        # Skip unrecognised words (e.g. "and", "the")
    return "".join(result)


def parse_dob(text: str) -> str:
    """Convert natural-language date of birth to MM/DD/YYYY.

    Handles:
        "may second two thousand and five"     → "05/02/2005"
        "march fifteen nineteen ninety"        → "03/15/1990"
        "january 15 1990"                      → "01/15/1990"
        "april third two thousand one"         → "04/03/2001"
        "3/15/1985" or "03-15-1985"            → "03/15/1985"
        "19900315" (YYYYMMDD)                  → "03/15/1990"
    """
    clean = text.strip()

    # Already numeric: MM/DD/YYYY or MM-DD-YYYY
    m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$", clean)
    if m:
        mo, dy, yr = m.groups()
        yr = _expand_2digit_year(yr)
        return f"{int(mo):02d}/{int(dy):02d}/{yr}"

    # YYYYMMDD compact
    m = re.match(r"^(\d{4})(\d{2})(\d{2})$", clean)
    if m:
        yr, mo, dy = m.groups()
        return f"{mo}/{dy}/{yr}"

    tokens = clean.lower().replace(",", "").replace("-", " ").split()
    # Remove filler words
    tokens = [t for t in tokens if t not in ("the", "of", "and", "a")]

    month_num: str | None = None
    day_num: int | None = None
    year_tokens: list[str] = []

    i = 0
    while i < len(tokens):
        tok = tokens[i]

        # Month name
        if tok in _MONTHS and month_num is None:
            month_num = _MONTHS[tok]
            i += 1
            continue

        # Ordinal day (word form: "second", "fifteenth", etc.)
        if tok in _ORDINALS and day_num is None:
            day_num = _ORDINALS[tok]
            i += 1
            continue

        # "twenty first", "thirty first" — two-word ordinals
        if i + 1 < len(tokens):
            two = f"{tok} {tokens[i+1]}"
            if two in _ORDINALS and day_num is None:
                day_num = _ORDINALS[two]
                i += 2
                continue

        # Numeric ordinal: "3rd", "15th", "21st", "2nd"
        m_ord = re.match(r"^(\d+)(?:st|nd|rd|th)$", tok)
        if m_ord and day_num is None:
            day_num = int(m_ord.group(1))
            i += 1
            continue

        # Pure numeric token
        if re.match(r"^\d+$", tok):
            val = int(tok)
            if month_num is None and 1 <= val <= 12:
                month_num = f"{val:02d}"
            elif day_num is None and 1 <= val <= 31:
                day_num = val
            else:
                year_tokens.append(tok)
            i += 1
            continue

        # Cardinal day numbers when month already known: "fifteen" = 15th
        if tok in _ONES and month_num is not None and day_num is None:
            val = _ONES[tok]
            if 1 <= val <= 31:
                day_num = val
                i += 1
                continue

        # Remaining words go to year parsing
        year_tokens.append(tok)
        i += 1

    year_str = _parse_year(year_tokens) if year_tokens else None

    if month_num and day_num and year_str:
        return f"{int(month_num):02d}/{day_num:02d}/{year_str}"

    logger.warning(f"[parse_dob] Could not parse {text!r} → returning as-is")
    return text


def format_phone(text: str) -> str:
    """Convert spoken phone number to formatted string.

    Returns digits + dashes in a sensible format:
        "five five five eight six seven five three zero nine" → "555-867-5309"
        "one 800 555 1234"                                   → "1-800-555-1234"
    """
    digits = parse_digits(text)
    # Remove any dashes already inserted by parse_digits, then reformat
    raw = digits.replace("-", "")
    if len(raw) == 10:
        return f"{raw[:3]}-{raw[3:6]}-{raw[6:]}"
    if len(raw) == 11 and raw[0] == "1":
        return f"1-{raw[1:4]}-{raw[4:7]}-{raw[7:]}"
    # Non-standard length — just return digits with original separators
    return digits if digits else text


# ── Year helpers ────────────────────────────────────────────────────────────

def _expand_2digit_year(yr: str) -> str:
    y = int(yr)
    if len(yr) == 2:
        return f"20{y:02d}" if y <= 30 else f"19{y:02d}"
    return yr


def _parse_year(tokens: list[str]) -> str | None:
    """Parse year from a list of tokens.

    Handles:
        ["two", "thousand", "and", "five"] → "2005"
        ["two", "thousand", "twenty"]      → "2020"
        ["nineteen", "ninety", "five"]     → "1995"
        ["1990"]                           → "1990"
        ["2005"]                           → "2005"
    """
    tokens = [t for t in tokens if t not in ("and", "a")]
    text = " ".join(tokens)

    # Direct 4-digit year
    if re.match(r"^\d{4}$", text):
        return text

    # "two thousand [and] X" / "two thousand X"
    m = re.match(r"^two thousand(?:\s+(?:and\s+)?(\w[\w\s]*))?$", text)
    if m:
        rest = (m.group(1) or "").strip()
        if not rest:
            return "2000"
        # Could be a cardinal ("five" → 5, "twenty five" → 25)
        val = _word_to_int(rest.split())
        if val is not None and 1 <= val <= 99:
            return f"20{val:02d}"
        return None

    # "nineteen XY" / "eighteen XY" style
    centuries = {"nineteen": "19", "eighteen": "18", "seventeen": "17", "twenty": "20"}
    parts = text.split()
    if len(parts) >= 2 and parts[0] in centuries:
        suffix_val = _word_to_int(parts[1:])
        if suffix_val is not None and 0 <= suffix_val <= 99:
            return f"{centuries[parts[0]]}{suffix_val:02d}"

    # Try parsing as plain integer (handles "1990", "2005")
    try:
        y = int(text)
        if 1900 <= y <= 2099:
            return str(y)
    except ValueError:
        pass

    return None


def _word_to_int(tokens: list[str]) -> int | None:
    """Convert a short list of number words to an integer (<1000).

    "five"         → 5
    "twenty five"  → 25
    "ninety"       → 90
    """
    total = 0
    for tok in tokens:
        tok = tok.strip()
        if tok in _ONES:
            total += _ONES[tok]
        elif re.match(r"^\d+$", tok):
            total += int(tok)
        else:
            return None
    return total if total > 0 else None


# ── Field-level dispatcher ──────────────────────────────────────────────────

_PHONE_FIELDS = {"phone-number", "emergency-phone"}
_DIGIT_FIELDS = {"member-id", "group-number"}
_DATE_FIELDS = {"date-of-birth"}


def normalise_field(field_id: str, value: str) -> str:
    """Normalise a spoken value to the appropriate format for the given field.

    Returns the normalised string, or the original if no conversion applies.
    """
    # Skip if already looks formatted (contains digits or slashes)
    if field_id in _DATE_FIELDS:
        result = parse_dob(value)
        logger.info(f"[NORMALISE] DOB: {value!r} → {result!r}")
        return result

    if field_id in _PHONE_FIELDS:
        result = format_phone(value)
        logger.info(f"[NORMALISE] Phone: {value!r} → {result!r}")
        return result

    if field_id in _DIGIT_FIELDS:
        result = parse_digits(value)
        if result:
            logger.info(f"[NORMALISE] Digits: {value!r} → {result!r}")
            return result

    return value


def to_spoken(field_id: str, value: str) -> str:
    """Return a TTS-friendly version of the stored value for the LLM to read back.

    For ID / phone fields, inserts spaces between digits so Gradium TTS reads
    "123456" as "one two three four five six" instead of "one hundred
    twenty-three thousand...". Other fields (including dates) pass through
    unchanged. The form still stores/displays the compact value.
    """
    if field_id in _DIGIT_FIELDS or field_id in _PHONE_FIELDS:
        spaced = " ".join(ch for ch in value if ch.isdigit())
        return spaced or value
    return value
