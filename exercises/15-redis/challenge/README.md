# Challenge 15 — Rate limit com janela deslizante

Ficheiros:
- `rate_limit.py` — `allow_request_fixed(customer_id, now)` e `allow_request_sliding(customer_id, now)`.
- `tests/test_rate_limit.py` — os dois testes.
- `pyproject.toml`, `.env.example` (`REDIS_URL`; sem `.env` usa a password do `.env` da raiz).

```bash
cd exercises/15-redis/challenge
uv run pytest -v        # -s para ver também os prints
```

## As duas funções

- **Janela fixa** (como no exercício, mas com `now` como argumento): um contador
  `ratelimit:fixed:{customer_id}:{int(now // 60)}` com `INCR` + `EXPIRE 60`.
- **Janela deslizante**: um sorted set `ratelimit:sliding:{customer_id}` com score = hora do
  pedido. Um script Lua, num só passo atómico:
  1. `ZREMRANGEBYSCORE key -inf now-60` — tira os pedidos com mais de 60 s;
  2. `ZCARD key` — conta os que ficam;
  3. se forem menos de 10, `ZADD key now <membro>` e devolve 1; senão devolve 0.

  O membro é `"{now}:{uuid4}"`, por isso é único mesmo quando dois pedidos têm a mesma hora
  (com membro = hora, o segundo `ZADD` só atualizava o primeiro e contava como um só).

## `uv run pytest -v`

```
tests/test_rate_limit.py::test_fixed_window_accepts_20_but_sliding_only_10 PASSED [ 50%]
tests/test_rate_limit.py::test_sliding_window_under_concurrency PASSED   [100%]

============================== 2 passed in 0.14s ===============================
```

Com `-s`:

```
janela fixa:      20 aceites de 20  [True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True, True]
janela deslizante: 10 aceites de 20  [True, True, True, True, True, True, True, True, True, True, False, False, False, False, False, False, False, False, False, False]

30 pedidos de 10 threads: 10 aceites, 20 recusados
```

- **Teste 1:** 10 pedidos aos segundos 59.0–59.9 de um minuto e 10 aos 0.0–0.9 do seguinte.
  A janela fixa aceita os 20 (10 em cada minuto do relógio), embora sejam 20 pedidos em menos
  de 2 segundos. A deslizante aceita só os primeiros 10: para os outros, os últimos 60 s já têm 10.
- **Teste 2:** 30 pedidos de 10 threads, todos com a mesma hora, na janela deslizante:
  exatamente 10 aceites, e o sorted set tem 10 membros.

## Porque a verificação e a inserção têm de ser atómicas

Se fossem comandos separados (`ZCARD`, e depois `ZADD` na aplicação), várias threads podiam
fazer o `ZCARD` ao mesmo tempo, todas veriam por exemplo 9 pedidos, e todas fariam o `ZADD`:
ficavam 15 ou 20 aceites em vez de 10. É o mesmo problema "ler, decidir, escrever" do write
skew do exercício 08. O Redis corre cada script Lua inteiro sem nenhum outro comando pelo meio,
por isso a contagem que cada pedido vê já inclui os pedidos aceites antes dele — e o teste 2
dá sempre exatamente 10.
