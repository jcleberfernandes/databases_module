# Runbook — Recuperar dados apagados do Pagila (exercício 10)

## Quando usar

Alguém apagou linhas de uma ou mais tabelas (ex: `DELETE` sem o `WHERE` certo)
e a base continua a funcionar. Não usar se a base inteira se perdeu (aí basta o passo 1 com `-d ex10`).

## Pré-requisitos

- `docker compose ps` mostra o `postgres` como `healthy`.
- Existe um dump em `backups/` (formato custom, `-Fc`).
- Saber que tabelas foram afetadas (aqui: `payment`, `film_actor`, `film_category`).

## Ficheiros

| Ficheiro | Para quê |
|---|---|
| `counts.sql` | contar linhas das tabelas (antes/depois) |
| `after_backup.sql` | simula a atividade da loja depois do backup |
| `disaster.sql` | simula o script do formador (apaga dados de 3 tabelas) |
| `recover.sh` | a recuperação (passos 1 a 4 abaixo) |

## 0. Backup (no início)

```bash
./scripts/create-db.sh ex10 --pagila
mkdir -p backups
docker compose exec -T postgres psql -U postgres -d ex10 < exercises/10-backup/exercise/counts.sql
docker compose exec -T postgres pg_dump -U postgres -Fc ex10 > backups/ex10_$(date +%F_%H%M%S).dump
```

```
 payment | film_actor | film_category | rental
---------+------------+---------------+--------
   51061 |       5462 |          2367 |  51805
```

Backup: `backups/ex10_2026-11-01_184145.dump`, 4,6 MB, 2,7 s.

## Depois do backup e o desastre

```bash
docker compose exec -T postgres psql -U postgres -d ex10 < exercises/10-backup/exercise/after_backup.sql
docker compose exec -T postgres psql -U postgres -d ex10 < exercises/10-backup/exercise/disaster.sql
```

Atividade depois do backup: +5 linhas em `film_actor` (ator 1) e +2 pagamentos (um de 2022-12-31 e um de 2026-07-28).

Desastre:

```
DELETE FROM payment WHERE payment_date < '2023-01-01';      -- DELETE 19071
DELETE FROM film_actor WHERE actor_id <= 50;                -- DELETE 1332
DELETE FROM film_category WHERE category_id IN (1, 2, 3);   -- DELETE 447
```

```
 payment | film_actor | film_category | rental
---------+------------+---------------+--------
   31992 |       4135 |          1920 |  51805
```

## Recuperação

```bash
time bash exercises/10-backup/exercise/recover.sh backups/ex10_2026-11-01_184145.dump
```

O que o script faz:

1. **Restaura o dump numa base separada** (`ex10_restored`). Não se mexe na base em produção às cegas.
   ```bash
   docker compose exec -T postgres psql -U postgres -d postgres -c "CREATE DATABASE ex10_restored"
   docker compose exec -T postgres pg_restore -U postgres -d ex10_restored --no-owner < backups/ex10_....dump
   ```
2. **Copia as 3 tabelas** do backup para um schema `recovery` em `ex10`:
   ```bash
   docker compose exec -T postgres psql -U postgres -d ex10 -c "CREATE TABLE recovery.film_actor (LIKE public.film_actor)"
   docker compose exec -T postgres psql -U postgres -d ex10_restored -c "COPY (SELECT * FROM public.film_actor) TO STDOUT" \
     | docker compose exec -T postgres psql -U postgres -d ex10 -c "COPY recovery.film_actor FROM STDIN"
   ```
   (igual para `payment` e `film_category`; `payment` é particionada, por isso usa-se `COPY (SELECT ...)`).
3. **Insere só as linhas que faltam**, numa transação:
   ```sql
   INSERT INTO public.payment       SELECT * FROM recovery.payment       ON CONFLICT DO NOTHING;
   INSERT INTO public.film_actor    SELECT * FROM recovery.film_actor    ON CONFLICT DO NOTHING;
   INSERT INTO public.film_category SELECT * FROM recovery.film_category ON CONFLICT DO NOTHING;
   ```
   Assim os dados criados depois do backup que **não** foram apagados ficam intactos
   (um `TRUNCATE` + restore da tabela apagava-os).
4. Apaga o schema `recovery` e a base `ex10_restored`.

**Tempo medido do restore: 10,5 s** (`real 0m10.473s`).

## Verificação

```bash
docker compose exec -T postgres psql -U postgres -d ex10 < exercises/10-backup/exercise/counts.sql
```

```
 payment | film_actor | film_category | rental
---------+------------+---------------+--------
   51062 |       5462 |          2367 |  51805
```

- `film_category` e `film_actor`: iguais ao backup.
- `payment`: 51 061 do backup + 1 pagamento de 2026 criado depois do backup (não foi apagado, ficou).

## O que se perdeu (RPO real)

Tudo o que foi criado **depois do backup** e **apagado pelo desastre**:

| Tabela | Perdido |
|---|---|
| `film_actor` | 5 linhas (ator 1, filmes 990–994) |
| `payment` | 1 pagamento de 9.99 de 2022-12-31 |
| `film_category` | nada |

O RPO real é o tempo entre o backup e o desastre: tudo o que foi escrito nesse
intervalo, nas tabelas afetadas, perdeu-se.

## O que mudaria na estratégia

- **Backups mais frequentes** (ex: de hora a hora) com retenção, para baixar o RPO (ver challenge).
- **Arquivo de WAL + backup físico** para point-in-time recovery: voltar ao segundo antes do `DELETE`, RPO quase zero.
- **Testar o restore automaticamente** (`verify.sh` do challenge), porque um backup nunca restaurado não é um backup.
- **Copiar os dumps para fora da máquina** (outro disco/cloud): um volume Docker não é um backup.
- **Menos permissões**: a aplicação não devia poder fazer `DELETE` em massa (roles do exercício 09).

## Quem avisar

O responsável pela base de dados e a equipa da aplicação, com a lista do que se perdeu (tabela acima).
