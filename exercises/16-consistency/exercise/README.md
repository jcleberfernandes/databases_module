# Exercício 16 — Redis como dado derivado: rebuild, verify e persistência

Ficheiros:
- `rebuild.py` — reconstrói `customer:{customer_id}:categories` (1 query + 1 pipeline).
- `verify.py` — compara o Redis com o PostgreSQL; sai com 0 ou 1.
- `config.py`, `pyproject.toml`, `.env.example` — `DATABASE_URL` e `REDIS_URL` a terminar em
  **`/1`** (base lógica 1, para o `FLUSHDB` não apagar as chaves dos outros exercícios).

## Como correr

```bash
./scripts/create-db.sh ex16 --pagila --reset
cd exercises/16-consistency/exercise
# redis-cli na base 1 (a password é a do próprio contentor):
rc() { docker compose exec -T redis sh -c 'redis-cli -a "$REDIS_PASSWORD" --no-auth-warning -n 1 "$@"' -- "$@"; }
rc FLUSHDB
uv run python rebuild.py
uv run python verify.py; echo "exit=$?"
```

## 1. `rebuild.py`

- **Uma query:** `array_agg(DISTINCT c.name)` por cliente, juntando `rental → inventory →
  film_category → category` (um filme pode ter várias categorias; o `DISTINCT` tira as repetidas).
- **Um pipeline:** para cada cliente `DEL tmp:…`, `SADD tmp:… <categorias>`, `RENAME tmp:… customer:{id}:categories`.
  O `RENAME` substitui o set antigo de uma vez, por isso quem lê vê o set antigo ou o novo, nunca um a meio.
- No mesmo pipeline apaga as chaves `customer:*:categories` de clientes que não deviam ter uma
  (encontradas antes com `SCAN`). É isso que remove o `customer:647:categories` falso no passo 3.

## 2. `FLUSHDB`, rebuild e contagem com `SCAN`

```
> FLUSHDB (base 1)
OK
> rebuild.py
rebuild: 997 sets escritos, 0 chaves a mais apagadas, 1 query + 1 pipeline, 0.19 s
SCAN customer:*:categories: 997 chaves
```

**997 sets** (os clientes 647 e 978 não têm alugueres). A contagem usa `SCAN` (`scan_iter`),
que percorre as chaves aos poucos; `KEYS` bloqueava o Redis enquanto as lia todas.

## 3. `verify.py`

```
> verify.py
verify: 997 sets comparados, 0 diferenças
exit=0
> SREM customer:1:categories Action
customer:1:categories: PostgreSQL 16, Redis 15 | em falta no Redis: ['Action'] | a mais no Redis: []
verify: 997 sets comparados, 1 diferenças
exit=1
> SADD customer:647:categories Fake
customer:1:categories: PostgreSQL 16, Redis 15 | em falta no Redis: ['Action'] | a mais no Redis: []
customer:647:categories: não devia existir (o cliente não tem alugueres) | membros: ['Fake']
verify: 997 sets comparados, 2 diferenças
exit=1
> rebuild.py
rebuild: 997 sets escritos, 1 chaves a mais apagadas, 1 query + 1 pipeline, 0.20 s
SCAN customer:*:categories: 997 chaves
> verify.py
verify: 997 sets comparados, 0 diferenças
exit=0
```

## 4. Classes das chaves (exercícios 15 e 16)

| Chave | Classe | O que se perde se o Redis a perder | Como volta |
|---|---|---|---|
| `customer:{id}:viewed` (filmes vistos) | **fonte de verdade** (só existe no Redis) | a lista de filmes vistos recentemente; os clientes deixam de os ver no "vistos recentemente" | não volta: não está em mais lado nenhum. Só se recupera de um backup/AOF do Redis (ou deixa-se encher outra vez com as novas visitas) |
| `cache:film:{id}` (cache) | **derivada** | nada de definitivo: só a cópia; os próximos pedidos vão ao PostgreSQL (mais lentos por um momento) | sozinha: no próximo `get_film` (cache-aside) |
| `lock:refresh:monthly_revenue` | **efémera** | o lock: outro processo pode começar um `REFRESH` ao mesmo tempo (o `CONCURRENTLY` aguenta; no pior caso faz-se trabalho a dobrar) | não precisa de voltar: o próximo processo cria um novo; expira em 60 s de qualquer forma |
| `ratelimit:customer:{id}:{minuto}` | **efémera** | os contadores do minuto atual: um cliente pode fazer até mais 10 pedidos nesse minuto | não precisa: o minuto seguinte começa do zero |
| `customer:{id}:categories` | **derivada** | os sets (até ao rebuild, quem lê vê sets vazios) | `rebuild.py` (~0,2 s) a partir do PostgreSQL; `verify.py` confirma |

## 5. Configuração escolhida

Configuração atual do contentor (valores por omissão da imagem):

```
appendonly no | appendfsync everysec | maxmemory 0 | maxmemory-policy noeviction | save 3600 1 300 100 60 10000
```

Escolho:

```
appendonly yes
appendfsync everysec
maxmemory 256mb
maxmemory-policy noeviction
```

Justificação, a partir da tabela:

- **`appendonly yes` + `everysec`.** A única chave que é *fonte de verdade* é
  `customer:{id}:viewed`. Com só RDB, uma falha perde tudo desde o último snapshot (até 1 hora
  com `save 3600 1`). Com AOF `everysec` perde-se no máximo ~1 segundo de escritas, com um custo
  de desempenho pequeno. `always` (fsync em cada escrita) não compensa para uma lista de
  "vistos recentemente". O AOF também evita servir sets de categorias vazios entre um
  reinício e o rebuild.
- **`maxmemory 256mb`.** Sem limite, o Redis pode crescer até a máquina ficar sem memória e
  o sistema matar o processo — aí perde-se tudo, incluindo a fonte de verdade.
- **`maxmemory-policy noeviction`.** Quando chega ao limite, o Redis recusa escritas novas
  com erro em vez de apagar chaves em silêncio. Uma política como `allkeys-lru` podia apagar
  `customer:{id}:viewed` (que não volta) ou um set de categorias (que ficava errado até ao
  próximo rebuild, sem ninguém saber). Prefiro um erro visível a perder dados sem aviso.

**O compromisso.** `maxmemory-policy` é **uma para a instância inteira**, não por chave. Para a
cache (`cache:film:*`) a política ideal seria `allkeys-lru` ou `volatile-lru` — apagar cópias
antigas é exatamente o que uma cache deve fazer quando a memória acaba. Mas a mesma política
também apagaria a fonte de verdade. Com `noeviction` protejo os dados que importam e pago com
erros de escrita na cache quando a memória acaba (por isso o limite tem de ter folga e ser vigiado).

**Quando usar duas instâncias.** Quando a cache é grande e precisa de expulsar chaves, e ao
mesmo tempo há dados que não se podem perder: uma instância **cache** (`allkeys-lru`, sem AOF,
pode perder tudo num reinício) e outra para **dados** (`noeviction`, AOF `everysec`, com
backups). Cada uma tem a configuração certa para o que guarda, e encher a cache nunca
põe em risco os dados.

Para ligar o AOF neste repositório (seguindo o aviso de `sessions/16-redis-consistency/fastapi/README.md`):

```bash
# 1.º: o servidor em execução escreve as chaves atuais num AOF novo
docker compose exec redis sh -c 'redis-cli -a "$REDIS_PASSWORD" --no-auth-warning CONFIG SET appendonly yes'
# 2.º: recriar o contentor com --appendonly yes (fica assim depois de reinícios)
docker compose -f docker-compose.yml -f docker-compose.redis-aof.yml up -d --wait redis
```

Não saltar o 1.º passo: um Redis que arranca com `appendonly yes` e não encontra AOF começa
vazio e ignora o `dump.rdb`.
