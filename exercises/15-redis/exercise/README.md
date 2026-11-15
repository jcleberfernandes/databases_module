# Exercício 15 — Padrões Redis

Ficheiros:
- `patterns.py` — as funções dos 4 padrões.
- `demo.py` — demonstração dos padrões 1, 2 e 4.
- `refresh.py` — o padrão 3 (lock) com `REFRESH MATERIALIZED VIEW CONCURRENTLY`.
- `setup.sql` — a view `monthly_revenue`.
- `config.py`, `pyproject.toml`, `.env.example` — `DATABASE_URL` e `REDIS_URL` (sem `.env`, usa as passwords do `.env` da raiz).

## Como correr

```bash
./scripts/create-db.sh ex15 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ex15 -v ON_ERROR_STOP=1 < exercises/15-redis/exercise/setup.sql
cd exercises/15-redis/exercise
uv run python demo.py                                   # ~1,5 min: o rate limit espera pela mudança de minuto
uv run python refresh.py & uv run python refresh.py & wait
```

## Saída de `demo.py`

```
=== 1. Filmes vistos recentemente
cliente 1 viu os filmes 1 a 25 por ordem
recent_views(1) = [25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6]
viu o filme 10 outra vez
recent_views(1) = [10, 25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 9, 8, 7, 6] (20 filmes, sem duplicados)
TTL customer:1:viewed = 2592000 s

=== 2. Cache-aside (filme 1)
get_film(1) -> MISS {'title': 'ACADEMY DINOSAUR', 'rating': 'PG', 'length': 86, 'rental_rate': '0.99'}
get_film(1) -> HIT {'title': 'ACADEMY DINOSAUR', 'rating': 'PG', 'length': 86, 'rental_rate': '0.99'}  (TTL 300 s)
update_film_rate(1, 1.99) -> PostgreSQL atualizado, cache:film:1 apagada: True
get_film(1) -> MISS {'title': 'ACADEMY DINOSAUR', 'rating': 'PG', 'length': 86, 'rental_rate': '1.99'}

=== 4. Rate limit (10 pedidos por minuto)
21:00:00 12 pedidos seguidos -> [True, True, True, True, True, True, True, True, True, True, False, False]
True: 10  False: 2
21:01:00 minuto seguinte -> allow_request(1) = True
```

(No fim, `demo.py` volta a pôr o `rental_rate` do filme 1 em 0.99.)

- **1.** `ZADD` com a hora atual como score (ver outra vez o mesmo filme só atualiza o score, não duplica),
  `ZREMRANGEBYRANK key 0 -21` (fica com os 20 mais recentes) e `EXPIRE` 30 dias, num `MULTI/EXEC`.
- **2.** Lê `cache:film:{id}`; num miss lê o PostgreSQL e guarda o JSON com `EX 300`.
  `update_film_rate` grava primeiro no PostgreSQL e depois **apaga** a chave (não a atualiza):
  a próxima leitura vai buscar o valor certo à fonte.
- **4.** Um contador por cliente e por minuto (`INCR` + `EXPIRE 60`); acima de 10 recusa.

## Saída dos dois `refresh.py`

```
[129044] lock ocupado: outro processo está a atualizar, saltei
[129045] lock obtido (token dee68527...)
[129045] REFRESH feito em 0.07 s; a manter o lock 5 s
[129045] lock libertado: True
```

O lock é `SET lock:refresh:monthly_revenue <token aleatório> NX EX 60`. Só um processo
consegue o `NX`; o outro vê que a chave existe e salta. A libertação é um script Lua que só
apaga a chave se o valor ainda for o **seu** token, de forma atómica:

```lua
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
```

Prova de que um processo sem o token não liberta o lock:

```
A tem o lock: True
B tenta libertar com outro token: False | chave ainda existe: True
A liberta com o seu token: True | chave existe: False
```

Sem o token, um processo cujo lock já tivesse expirado (`EX 60`) podia apagar o lock que
entretanto outro processo obteve. Com `GET` e `DEL` separados também podia acontecer, entre os
dois comandos; o Lua faz os dois juntos.

## Chaves usadas

| Padrão de chave | Tipo Redis | TTL | Para quê |
|---|---|---|---|
| `customer:{customer_id}:viewed` | sorted set (membro = film_id, score = hora) | 30 dias depois da última visita | filmes vistos recentemente (máx. 20) |
| `cache:film:{film_id}` | string (JSON) | 300 s | cópia em cache do filme (`title`, `rating`, `length`, `rental_rate`) |
| `lock:refresh:monthly_revenue` | string (token) | 60 s | só um processo de cada vez faz o `REFRESH` |
| `ratelimit:customer:{customer_id}:{minuto}` | string (contador) | 60 s | rate limit de 10 pedidos por minuto (janela fixa) |
