# Runbook — Recuperar linhas apagadas de `payment`, `film_actor` e `film_category`

## Quando usar

Alguém apagou linhas de uma ou mais tabelas (um `DELETE` errado, um script mal corrido) e a base
continua a funcionar. Este runbook recupera as linhas a partir do último backup **sem apagar nem
recriar a base**, enquanto o resto da aplicação continua a usá-la.

Não usar se a base inteira se perdeu: aí faz-se `createdb` + `pg_restore` do dump completo.

## Pré-requisitos

- `docker compose ps` mostra o `postgres` como `healthy`.
- Um dump em formato custom (`-Fc`) em `backups/`, de antes do incidente.
- Saber que tabelas e que linhas foram afetadas. Aqui: `payment` com `payment_date >= '2026-01-01'`
  (as partições `payment_p2026_01` a `payment_p2026_07`), `film_actor` com `actor_id <= 50` e
  `film_category` com `category_id = 1`.
- Avisar quem usa a base: durante o restore (menos de 1 s) estas tabelas estão vazias ou bloqueadas.

## Ficheiros

| Ficheiro | Para quê |
|---|---|
| `activity.sql` | a atividade normal depois do backup (do enunciado) |
| `disaster.sql` | o incidente (do enunciado) |
| `counts.sql` | contar as linhas das 3 tabelas |
| `lost.sql` | mostrar o que se perdeu (RPO) |

## Comandos, por ordem

Na raiz do repositório. `P` é só um atalho para o `psql` da base `ex10`:

```bash
P() { docker compose exec -T postgres psql -U postgres -d ex10 "$@"; }
```

### 0. Preparar (só neste exercício)

```bash
./scripts/create-db.sh ex10 --pagila --reset
```

### 1. Contar as linhas

```bash
P < exercises/10-backup/exercise/counts.sql
```
```
 payment | film_actor | film_category
---------+------------+---------------
   51061 |       5462 |          2367
```

### 2. Backup

```bash
mkdir -p backups
date '+%F %T'                                  # 2026-11-05 11:53:18
docker compose exec -T postgres pg_dump -U postgres -Fc ex10 > backups/ex10_$(date +%F_%H%M).dump
```

`backups/ex10_2026-11-05_1153.dump` (4,6 MB, 0,9 s).

### 3. A atividade e o incidente

```bash
P < exercises/10-backup/exercise/activity.sql     # INSERT 0 5
P < exercises/10-backup/exercise/disaster.sql     # DELETE 5286, DELETE 1327, DELETE 149
P < exercises/10-backup/exercise/counts.sql
```
```
 payment | film_actor | film_category
---------+------------+---------------
   45780 |       4135 |          2218
```

### 4. Restore (sem apagar a base)

Primeiro confirmar que as partições de 2026 estão vazias (não pode haver linhas novas que se
repetissem com as do backup). Não pode aparecer nenhuma partição:

```bash
P -c "SELECT tableoid::regclass, count(*) FROM payment WHERE payment_date >= '2026-01-01' GROUP BY 1"
```

`film_actor` e `film_category` ainda têm parte das linhas. O plano é **esvaziá-las e carregá-las
inteiras** do backup (nenhuma das duas mudou depois do backup, por isso não se perde nada).
O `payment` está particionado: as linhas estão nas partições, e cada uma tem de ser nomeada;
as de 2026 estão vazias, por isso basta carregá-las.

```bash
time ( P -v ON_ERROR_STOP=1 -c "TRUNCATE film_actor, film_category" && \
  docker compose exec -T postgres pg_restore -U postgres -d ex10 --data-only --single-transaction \
    -t film_actor -t film_category \
    -t payment_p2026_01 -t payment_p2026_02 -t payment_p2026_03 -t payment_p2026_04 \
    -t payment_p2026_05 -t payment_p2026_06 -t payment_p2026_07 \
    < backups/ex10_2026-11-05_1153.dump )
```

- `--data-only`: só os dados; as tabelas já existem.
- `--single-transaction`: ou carrega tudo, ou nada.
- Não usar `--clean -t film_actor`: tenta apagar e recriar a tabela e falha, porque as views `actor_info` e `film_list` dependem dela.

**Tempo medido do restore (RTO real): 0,54 s** (`real 0m0.541s`).

### 5. Verificar o restore

```bash
P < exercises/10-backup/exercise/counts.sql
```
```
 payment | film_actor | film_category
---------+------------+---------------
   51061 |       5462 |          2367
```

| | payment | film_actor | film_category |
|---|---|---|---|
| tarefa 1 (antes do incidente) | 51 061 | 5 462 | 2 367 |
| tarefa 3 (depois do incidente) | 45 780 | 4 135 | 2 218 |
| tarefa 5 (depois do restore) | **51 061** | **5 462** | **2 367** |

As três tabelas voltaram às contagens da tarefa 1. Outras verificações úteis: a aplicação abre
um filme com os seus atores; `SELECT count(*) FROM payment WHERE payment_date >= '2026-01-01'`
dá 5 281: o `DELETE` apagou 5 286, dos quais 5 eram os pagamentos de `activity.sql`, que não estão no backup.

## O que se perdeu (RPO real)

Tudo o que foi escrito **depois do backup** nas tabelas apagadas. Aqui: os **5 pagamentos de
`activity.sql`** (1.99 cada, de 2026-07-30 12:00). Foram criados depois do backup e apagados pelo
incidente (`payment_date >= '2026-01-01'`), por isso não estão em lado nenhum.

```bash
P < exercises/10-backup/exercise/lost.sql
```
```
 rental_id | customer_id | amount |      payment_date
-----------+-------------+--------+------------------------
     87555 |         250 |   1.99 | 2026-07-30 12:00:00+00
     87556 |         715 |   1.99 | 2026-07-30 12:00:00+00
     87557 |         484 |   1.99 | 2026-07-30 12:00:00+00
     87558 |         676 |   1.99 | 2026-07-30 12:00:00+00
     87559 |           3 |   1.99 | 2026-07-30 12:00:00+00
```

(Os 5 alugueres mais recentes não têm o pagamento de 1.99 que o `activity.sql` lhes deu.)
É por isso que as contagens voltam a ser as da tarefa 1 e não "tarefa 1 + 5". Estes 5 pagamentos
têm de ser registados outra vez a partir de outra fonte (recibos, o sistema de pagamentos).

O RPO real é o tempo entre o backup (11:53:18) e o incidente: tudo o que foi escrito nesse
intervalo, nas tabelas afetadas, perdeu-se.

## O que mudar na estratégia de backup

- **Backups mais frequentes**, automáticos e com retenção (ver o challenge): o RPO é, no máximo, o intervalo entre backups.
- **Arquivo do WAL + backup físico** (point-in-time recovery): permite voltar ao segundo antes do
  `DELETE`, e os 5 pagamentos não se perdiam (RPO de segundos).
- **Testar o restore com regularidade**: um backup que nunca foi restaurado não se sabe se funciona.
- **Copiar os backups para fora da máquina** (outro disco ou a cloud): um volume Docker não é um backup.
- **Menos privilégios**: a aplicação não devia conseguir apagar milhares de linhas de uma vez (roles do exercício 09).
