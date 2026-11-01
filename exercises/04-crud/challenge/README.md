# Challenge 04 — 1 milhão de alugueres com COPY

Ficheiros: `seed.py` (o seed), `checksum.sql` (md5 dos dados), `pyproject.toml`.
O script lê `POSTGRES_USER` e `POSTGRES_PASSWORD` do `.env` da raiz.

```bash
./scripts/create-db.sh ex04_seed_a --pagila
./scripts/create-db.sh ex04_seed_b --pagila
cd exercises/04-crud/challenge
uv run python seed.py ex04_seed_a
uv run python seed.py ex04_seed_b
uv run python seed.py ex04_seed_b     # 2.ª vez: não duplica
cd ../../..
docker compose exec -T postgres psql -U postgres -d ex04_seed_a < exercises/04-crud/challenge/checksum.sql
docker compose exec -T postgres psql -U postgres -d ex04_seed_b < exercises/04-crud/challenge/checksum.sql
```

## Como funciona

- Lê os ids que existem em `inventory`, `customer` e `staff` e escolhe ao acaso com
  `random.Random(42)` (semente fixa = mesmos dados sempre).
- `return_date` = `rental_date` + 1 a 240 horas, logo sempre depois.
- `COPY` para uma tabela temporária, depois um `INSERT ... SELECT` para `rental`.
  Antes do INSERT tira as FKs e índices secundários e volta a criá-los no fim
  (é mais rápido do que atualizar os índices linha a linha). As FKs são
  validadas quando são recriadas, logo uma linha inválida dava erro.
- Idempotente: os ids do seed começam em 1 000 001. Se já há 1 000 000 linhas
  nesse intervalo não faz nada; se ficou a meio, apaga e recomeça.

## Resultado

```
COPY: 7.4 s
INSERT: 11.6 s
1,000,000 alugueres inseridos em 14.2 s
Os dados já existem, nada a fazer.
```

`checksum.sql` nas duas bases (o `uuid` fica de fora porque é gerado ao acaso pelo PostgreSQL):

```
ex04_seed_a:  1000000 | 70d99979b3da9e6b6d749ed803da46b8
ex04_seed_b:  1000000 | 70d99979b3da9e6b6d749ed803da46b8
```

Datas inválidas (`return_date <= rental_date`): 0.
