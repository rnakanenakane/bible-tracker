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


-- insert into tb_leituras (usuario_id, plano_id, id_livro, capitulo, created_at)
-- select tb_usuarios.id,
--        tb_planos.id,
--        tb_livros.id,
--        capitulo,
--        leituras.created_at
-- from leituras inner join tb_usuarios
-- on tb_usuarios.nome = leituras.usuario
-- inner join tb_planos
-- on tb_planos.nome = leituras.plano
-- inner join tb_livros
-- on tb_livros.nome = leituras.livro
-- order by created_at
