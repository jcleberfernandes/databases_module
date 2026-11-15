# Challenge 01 — Escritas concorrentes: ficheiro JSON vs PostgreSQL

Ficheiros: `json_race.py`, `pg_race.py`, `pyproject.toml`, `.env.example`.

## Como correr

```bash
./scripts/create-db.sh ch01
cd exercises/01-diagnosis/challenge
uv run python json_race.py     # começa sempre com records.json = []
uv run python pg_race.py       # cria a tabela record se não existir e começa sempre com TRUNCATE
```

`pg_race.py` lê `DATABASE_URL` (ver `.env.example`); sem `.env`, usa a password do `.env` da raiz.

- `json_race.py`: 10 processos (`multiprocessing`), cada um junta 1 000 registos
  `{"worker": <processo>, "n": <0 a 999>}`, um de cada vez: lê o ficheiro inteiro, junta um,
  escreve o ficheiro inteiro. Sem lock. Se ler JSON inválido (ficheiro a meio de ser escrito),
  conta uma escrita falhada e continua.
- `pg_race.py`: 10 processos, cada um com a sua ligação, cada um faz 1 000 `INSERT` (um por registo)
  na tabela `record (worker integer NOT NULL, n integer NOT NULL)`.

## Resultados (3 execuções de cada)

```
== execução 1
JSON: 76 registos no ficheiro (esperado 10000), 9582 escritas falhadas, ficheiro INVÁLIDO (lixo depois do carácter 1815)
PostgreSQL: SELECT count(*) FROM record = 10000
== execução 2
JSON: 13 registos no ficheiro (esperado 10000), 9965 escritas falhadas, ficheiro INVÁLIDO (lixo depois do carácter 299)
PostgreSQL: SELECT count(*) FROM record = 10000
== execução 3
JSON: 12 registos no ficheiro (esperado 10000), 9957 escritas falhadas, ficheiro INVÁLIDO (lixo depois do carácter 276)
PostgreSQL: SELECT count(*) FROM record = 10000
```

| Execução | JSON | PostgreSQL |
|---|---|---|
| 1 | 76 | 10 000 |
| 2 | 13 | 10 000 |
| 3 | 12 | 10 000 |

Nas três execuções o ficheiro terminou **inválido**: duas escritas sobrepuseram-se e uma
escrita mais curta deixou no fim os últimos caracteres de uma mais comprida (`...}]]`). O
número de registos é o da lista válida que está no início do ficheiro.

## Porque os números são diferentes

No ficheiro JSON cada processo faz *ler – alterar – escrever* o ficheiro inteiro. Quando dois
processos leem a mesma versão, cada um junta o seu registo em memória e escreve a sua versão: a
última escrita apaga a do outro (**lost update**). Além disso, abrir o ficheiro para escrever
apaga-o antes de escrever o novo conteúdo, por isso os outros processos leem muitas vezes um
ficheiro vazio ou a meio — daí quase todas as escritas falharem — e duas escritas ao mesmo tempo
podem misturar-se e corromper o ficheiro. O resultado muda de execução para execução porque
depende de como o sistema operativo intercala os processos.

O PostgreSQL não reescreve a tabela: cada `INSERT` só acrescenta uma linha nova, numa transação
própria. O motor coordena as escritas concorrentes (cada transação vê um estado consistente, as
linhas novas não se sobrepõem e o WAL garante que um `COMMIT` não se perde nem fica a meio), por
isso as 10 000 inserções ficam todas, em todas as execuções.
