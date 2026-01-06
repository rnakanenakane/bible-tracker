def expandir_capitulos(str_caps: str) -> list[int]:
    """Expande uma string de capítulos (ex: '1-3' ou '5') para uma lista de inteiros."""
    str_caps = str(str_caps).strip()
    if "-" in str_caps:
        try:
            inicio, fim = map(int, str_caps.split("-"))
            return list(range(inicio, fim + 1))
        except (ValueError, TypeError):
            return []
    else:
        try:
            return [int(str_caps)]
        except (ValueError, TypeError):
            return []
