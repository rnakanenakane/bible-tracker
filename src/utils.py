import streamlit as st
import yaml


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


@st.cache_data
def load_book_images_map(path: str = "book_images.yaml") -> dict[str, str]:
    """Carrega o mapeamento de nomes de livros para caminhos de imagem de um arquivo YAML.

    Este método lê um arquivo YAML que associa o nome canônico de um livro da Bíblia
    ao caminho do arquivo de imagem correspondente. Ele é cacheado pelo Streamlit
    para evitar leituras repetidas do disco.

    Args:
        path: O caminho para o arquivo YAML contendo o mapeamento.

    Returns:
        Um dicionário onde as chaves são os nomes dos livros (str) e os valores
        são os caminhos das imagens (str). Retorna um dicionário vazio se o
        arquivo não for encontrado ou se houver um erro de processamento.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if not isinstance(data, dict):
                st.warning(f"Arquivo '{path}' não contém um mapeamento válido (dicionário).")
                return {}
            return data
    except FileNotFoundError:
        # Não é um erro, apenas um modo de operação sem imagens.
        return {}
    except Exception as e:
        st.error(f"Erro ao carregar ou processar o arquivo '{path}': {e}")
        return {}
