def format_currency(amount_minor: int) -> str:
    zloty = amount_minor // 100
    grosze = abs(amount_minor) % 100
    return f"{zloty},{grosze:02d} zł"


def format_currency_input(amount_minor: int) -> str:
    zloty = amount_minor // 100
    grosze = abs(amount_minor) % 100
    return f"{zloty}.{grosze:02d}"


def parse_currency(amount_str: str) -> int:
    cleaned = amount_str.replace(',', '.').strip()
    
    try:
        amount_float = float(cleaned)
        amount_minor = int(round(amount_float * 100))
        return amount_minor
    except ValueError:
        raise ValueError("Nieprawidłowy format kwoty")
