CREATE TABLE tb_usuarios (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE tb_planos (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE tb_livros (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE tb_plano_entradas (
    id SERIAL PRIMARY KEY,
    plano_id INTEGER NOT NULL REFERENCES tb_planos(id),
    data_leitura DATE NOT NULL,
    id_livro INTEGER NOT NULL REFERENCES tb_livros(id),
    capitulos TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE tb_leituras (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES tb_usuarios(id),
    plano_id INTEGER NOT NULL REFERENCES tb_planos(id),
    id_livro INTEGER NOT NULL REFERENCES tb_livros(id),
    capitulo INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE tb_perguntas (
    id SERIAL PRIMARY KEY,
    pergunta_texto TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE tb_respostas (
    id SERIAL PRIMARY KEY,
    pergunta_id INTEGER NOT NULL REFERENCES tb_perguntas(id) ON DELETE CASCADE,
    usuario_id INTEGER NOT NULL REFERENCES tb_usuarios(id),
    resposta_texto TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
