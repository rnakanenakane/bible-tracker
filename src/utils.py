import streamlit as st
import yaml


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


@st.cache_data
def load_book_images_map(path: str = "book_images.yaml") -> dict[str, str]:
    """Carrega o mapeamento de livros para imagens de um arquivo YAML."""
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


BIBLE_BOOKS_DATA = {
    # Antigo Testamento
    "Gênesis": {"order": 1, "chapters": 50},
    "Êxodo": {"order": 2, "chapters": 40},
    "Levítico": {"order": 3, "chapters": 27},
    "Números": {"order": 4, "chapters": 36},
    "Deuteronômio": {"order": 5, "chapters": 34},
    "Josué": {"order": 6, "chapters": 24},
    "Juízes": {"order": 7, "chapters": 21},
    "Rute": {"order": 8, "chapters": 4},
    "1 Samuel": {"order": 9, "chapters": 31},
    "2 Samuel": {"order": 10, "chapters": 24},
    "1 Reis": {"order": 11, "chapters": 22},
    "2 Reis": {"order": 12, "chapters": 25},
    "1 Crônicas": {"order": 13, "chapters": 29},
    "2 Crônicas": {"order": 14, "chapters": 36},
    "Esdras": {"order": 15, "chapters": 10},
    "Neemias": {"order": 16, "chapters": 13},
    "Ester": {"order": 17, "chapters": 10},
    "Jó": {"order": 18, "chapters": 42},
    "Salmos": {"order": 19, "chapters": 150},
    "Provérbios": {"order": 20, "chapters": 31},
    "Eclesiastes": {"order": 21, "chapters": 12},
    "Cantares": {"order": 22, "chapters": 8},
    "Isaías": {"order": 23, "chapters": 66},
    "Jeremias": {"order": 24, "chapters": 52},
    "Lamentações": {"order": 25, "chapters": 5},
    "Ezequiel": {"order": 26, "chapters": 48},
    "Daniel": {"order": 27, "chapters": 12},
    "Oseias": {"order": 28, "chapters": 14},
    "Joel": {"order": 29, "chapters": 3},
    "Amós": {"order": 30, "chapters": 9},
    "Obadias": {"order": 31, "chapters": 1},
    "Jonas": {"order": 32, "chapters": 4},
    "Miqueias": {"order": 33, "chapters": 7},
    "Naum": {"order": 34, "chapters": 3},
    "Habacuque": {"order": 35, "chapters": 3},
    "Sofonias": {"order": 36, "chapters": 3},
    "Ageu": {"order": 37, "chapters": 2},
    "Zacarias": {"order": 38, "chapters": 14},
    "Malaquias": {"order": 39, "chapters": 4},
    # Novo Testamento
    "Mateus": {"order": 40, "chapters": 28},
    "Marcos": {"order": 41, "chapters": 16},
    "Lucas": {"order": 42, "chapters": 24},
    "João": {"order": 43, "chapters": 21},
    "Atos": {"order": 44, "chapters": 28},
    "Romanos": {"order": 45, "chapters": 16},
    "1 Coríntios": {"order": 46, "chapters": 16},
    "2 Coríntios": {"order": 47, "chapters": 13},
    "Gálatas": {"order": 48, "chapters": 6},
    "Efésios": {"order": 49, "chapters": 6},
    "Filipenses": {"order": 50, "chapters": 4},
    "Colossenses": {"order": 51, "chapters": 4},
    "1 Tessalonicenses": {"order": 52, "chapters": 5},
    "2 Tessalonicenses": {"order": 53, "chapters": 3},
    "1 Timóteo": {"order": 54, "chapters": 6},
    "2 Timóteo": {"order": 55, "chapters": 4},
    "Tito": {"order": 56, "chapters": 3},
    "Filemom": {"order": 57, "chapters": 1},
    "Hebreus": {"order": 58, "chapters": 13},
    "Tiago": {"order": 59, "chapters": 5},
    "1 Pedro": {"order": 60, "chapters": 5},
    "2 Pedro": {"order": 61, "chapters": 3},
    "1 João": {"order": 62, "chapters": 5},
    "2 João": {"order": 63, "chapters": 1},
    "3 João": {"order": 64, "chapters": 1},
    "Judas": {"order": 65, "chapters": 1},
    "Apocalipse": {"order": 66, "chapters": 22},
}


def get_total_bible_chapters() -> int:
    """Calcula o número total de capítulos na Bíblia a partir de um mapa estático."""
    return sum(book_data["chapters"] for book_data in BIBLE_BOOKS_DATA.values())
