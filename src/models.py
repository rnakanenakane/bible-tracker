from datetime import datetime

from pydantic import BaseModel, Field


class Usuario(BaseModel):
    id: int
    nome: str


class Plano(BaseModel):
    id: int
    nome: str


class Livro(BaseModel):
    id: int
    nome: str


class Resposta(BaseModel):
    id: int
    pergunta_id: int
    resposta_texto: str
    created_at: datetime
    autor: Usuario


class Pergunta(BaseModel):
    id: int
    pergunta_texto: str
    created_at: datetime
    respostas: list[Resposta] = Field(default_factory=list)


class Leitura(BaseModel):
    capitulo: int
    created_at: datetime
    livro: Livro
