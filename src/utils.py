def expandir_capitulos(str_caps: str) -> list[int]:
    """Expande uma string de capítulos (ex: '1-3' ou '5') para uma lista de inteiros.

    Esta função interpreta formatos como:
    - '5': Um único capítulo.
    - '1-3': Um intervalo de capítulos.
    - '119:1-40': Um intervalo de versículos (retorna apenas o capítulo, 119).

    Args:
        str_caps: A string contendo a representação dos capítulos.

    Returns:
        Uma lista de inteiros representando os capítulos expandidos. Retorna
        uma lista vazia em caso de formato inválido.
    """
    str_caps = str(str_caps).strip()
    # Adicionado para lidar com intervalos de versículos como '119:1-40'
    if ":" in str_caps:
        try:
            chapter_part = str_caps.split(":")[0]
            return [int(chapter_part)]
        except (ValueError, TypeError):
            return []
    # Lida com intervalos de capítulos como '1-3'
    elif "-" in str_caps:
        try:
            inicio, fim = map(int, str_caps.split("-"))
            return list(range(inicio, fim + 1))
        except (ValueError, TypeError):
            return []
    # Lida com um único capítulo como '5'
    else:
        try:
            return [int(str_caps)]
        except (ValueError, TypeError):
            return []
