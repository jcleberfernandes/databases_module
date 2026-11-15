# Challenge 16 — Transactional outbox

Ficheiros:
- `rent.py` — insere N alugueres; cada aluguer e a sua linha de `outbox` na mesma transação.
- `worker.py` — processa a outbox em lotes de 50 com `FOR UPDATE SKIP LOCKED`.
- `setup.sql` — a tabela `outbox`.
- `pyproject.toml`, `.env.example` (usa `config.py` e `verify.py` do exercício).

## Passos que corri (na raiz do repositório)

```bash
rc() { docker compose exec -T redis sh -c 'redis-cli -a "$REDIS_PASSWORD" --no-auth-warning "$@"' -- "$@"; }

# ponto de partida: ex16 com os sets do rebuild.py e verify.py a dar 0
docker compose exec -T postgres psql -U postgres -d ex16 -v ON_ERROR_STOP=1 < exercises/16-consistency/challenge/setup.sql
(cd exercises/16-consistency/exercise && uv run python rebuild.py && uv run python verify.py)

# AOF, seguindo o aviso de sessions/16-redis-consistency/fastapi/README.md:
rc CONFIG SET appendonly yes          # 1.º o servidor escreve as chaves atuais num AOF (esperar aof_rewrite_in_progress:0)
docker compose -f docker-compose.yml -f docker-compose.redis-aof.yml up -d --wait redis
rc CONFIG SET appendfsync always

cd exercises/16-consistency/challenge
uv run python worker.py &             # worker 1
uv run python rent.py 5000 &
kill -9 <pid do worker 1>             # a meio de um lote
uv run python worker.py &             # worker 2
docker compose -f docker-compose.yml -f docker-compose.redis-aof.yml kill redis      # a meio de um lote
docker compose -f docker-compose.yml -f docker-compose.redis-aof.yml up -d --wait redis
rc CONFIG SET appendfsync always      # sempre depois de cada reinício
# esperar que a outbox fique toda processada, parar o worker
(cd ../exercise && uv run python verify.py; echo "exit=$?")
```

Antes das falhas, os dois `rc DBSIZE` (base 0 e base 1) deram o mesmo depois de ligar o AOF
(`db0=1 db1=997`): nenhuma chave se perdeu ao recriar o contentor.

O worker só escreve no Redis quando `CONFIG GET appendfsync` devolve `always`. Assim nunca
escreve antes de o `CONFIG SET` ser feito outra vez depois de um reinício (ver o log).
Entre escrever no Redis e fazer `COMMIT` espera 0,3 s, para ser possível matá-lo "a meio de um lote".

## Log do worker à volta das duas falhas

**1. `kill -9` do worker a meio de um lote:**

```
21:04:46 [worker 134884] lote 251..300: COMMIT
21:04:47 [worker 134884] lote 301..350 (50 linhas): Redis escrito, a fazer COMMIT
21:04:47 >>> kill -9 worker 134884 (a meio de um lote, depois do Redis e antes do COMMIT)
21:04:48 >>> worker 2 arrancou (pid 134996)
21:04:48 [worker 134996] arrancou
21:04:48 [worker 134996] lote 301..350 (50 linhas): Redis escrito, a fazer COMMIT
21:04:48 [worker 134996] lote 301..350: COMMIT
```

O worker 1 já tinha escrito o lote 301..350 no Redis mas não fez `COMMIT`. O PostgreSQL desfez a
transação, as 50 linhas voltaram a ficar livres, e o worker 2 processou o mesmo lote outra vez.

**2. `docker compose kill redis` a meio de um lote:**

```
21:04:52 [worker 134996] lote 851..900 (50 linhas): Redis escrito, a fazer COMMIT
21:04:52 >>> docker compose kill redis (a meio de um lote)
21:04:52 [worker 134996] lote 851..900: COMMIT
21:04:52 [worker 134996] erro no Redis (ConnectionError): ROLLBACK, tento outra vez daqui a 1 s
21:04:53 [worker 134996] erro no Redis (ConnectionError): ROLLBACK, tento outra vez daqui a 1 s
21:04:54 [worker 134996] erro no Redis (ConnectionError): ROLLBACK, tento outra vez daqui a 1 s
21:04:55 [worker 134996] erro no Redis (ConnectionError): ROLLBACK, tento outra vez daqui a 1 s
21:04:56 [worker 134996] Redis sem appendfsync always: à espera
...
21:05:01 [worker 134996] Redis sem appendfsync always: à espera
21:05:01 >>> redis arrancou outra vez com AOF (appendonly=yes)
21:05:01 >>> CONFIG SET appendfsync always
21:05:02 [worker 134996] lote 901..950 (50 linhas): Redis escrito, a fazer COMMIT
21:05:02 [worker 134996] lote 901..950: COMMIT
```

O Redis morreu depois de receber o lote 851..900 (com `appendfsync always` essas escritas já
estavam no disco) e antes do `COMMIT` no PostgreSQL, que correu bem. No lote seguinte o Redis
não respondia: `ConnectionError`, `ROLLBACK`, e o worker tentou outra vez de segundo a segundo.
Quando o Redis voltou (ainda com `everysec` do ficheiro de compose), o worker esperou pelo
`CONFIG SET appendfsync always` e continuou a partir do lote 901.

```
rent: 5000 alugueres + 5000 linhas de outbox em 14.9 s
 total | processed
-------+-----------
  5000 |      5000
```

## `verify.py` no fim (sem `rebuild.py`)

```
verify: 999 sets comparados, 0 diferenças
exit=0
```

999 e não 997: o `rent.py` deu alugueres também aos clientes 647 e 978, e o worker criou os sets deles.

Depois voltei o Redis à configuração normal do repositório (RDB): `rc SAVE` (para o `dump.rdb`
ficar atual) e `docker compose up -d --wait redis`. As chaves ficaram (`db0=1 db1=999`).

## 5. Explicações

**Porque processar a mesma linha duas vezes não faz mal.** O worker faz `SADD` de categorias
a um set. Um set não tem repetidos: juntar "Action" a um set que já tem "Action" não muda
nada. Fazer a operação uma ou duas vezes dá o mesmo resultado (é **idempotente**). Foi o que
aconteceu ao lote 301..350.

**Se não fosse idempotente** (por exemplo `INCR customer:{id}:rentals`), o lote repetido
contava duas vezes. Era preciso guardar no Redis, **na mesma operação atómica**, que aquela linha já
foi aplicada: por exemplo um script Lua que faz `SADD outbox:applied <outbox_id>` e só faz o
`INCR` se o `SADD` devolver 1 (o id ainda não estava lá). Ou um `MULTI` com as duas coisas.
Assim uma linha repetida é ignorada.

**Porque o resultado depende da persistência do Redis.** A outbox só garante que cada linha é
processada **pelo menos uma vez até ao `COMMIT`**. Depois do `COMMIT` a linha fica marcada como
`processed_at` e nunca mais é lida. Se o Redis perder uma escrita depois disso, ninguém volta a
fazê-la:

- **Só RDB:** o Redis grava um snapshot de tempos a tempos (`save 3600 1 300 100 ...`). Uma
  falha perde tudo desde o último snapshot — muitos lotes já com `COMMIT` no PostgreSQL.
- **AOF com `appendfsync everysec`:** o Redis responde OK antes de a escrita estar no disco e
  faz fsync uma vez por segundo. Uma falha pode perder até ~1 s de escritas que o worker já
  considerou feitas (e a que já fez `COMMIT`).
- **`appendfsync always`:** cada escrita está no disco antes do OK. Quando o worker faz `COMMIT`,
  o Redis já tem os dados guardados. Foi isso que salvou o lote 851..900.

A outbox sozinha não traz de volta o que se perdeu, porque essas linhas já estão processadas.
Só um `rebuild.py` completo (ou voltar a pôr `processed_at = NULL` em linhas recentes) o recuperaria.
