# Challenge 10 — Backups automáticos com retenção e verificação

Ficheiros: `backup.sh`, `verify.sh`. Os backups ficam em `backups/pagila/` (a pasta `backups/` está no `.gitignore`).

```bash
bash exercises/10-backup/challenge/backup.sh                     # hoje
bash exercises/10-backup/challenge/backup.sh --now 2026-10-01    # finge que hoje é 2026-10-01
bash exercises/10-backup/challenge/verify.sh; echo "exit=$?"
```

## `backup.sh`

1. Conta as linhas de **todas** as tabelas do `pagila` (70, `count(*)` exato de cada uma) para
   `pagila_YYYY-MM-DD_HHMM.counts`.
2. `pg_dump -Fc pagila` para `pagila_YYYY-MM-DD_HHMM.dump`. Os dois ficheiros são escritos primeiro
   com `.tmp` e só ganham o nome final se tudo correu bem.
3. Retenção: fica o último backup de cada um dos últimos 7 dias e o último de cada uma das últimas
   4 semanas (semanas ISO); o resto é apagado (`.dump` e `.counts`). `--now YYYY-MM-DD` substitui
   a data de hoje, no nome e na retenção.

```
2026-11-05 11:54:46 backup backups/pagila/pagila_2026-11-05_1154.dump (4.4M, 70 tabelas)
```

`.counts` (primeiras linhas):

```
actor 200
address 1003
category 16
```

## Tarefa 3 — retenção com 40 dias simulados

```bash
for i in $(seq 39 -1 0); do
  bash exercises/10-backup/challenge/backup.sh --now $(date -d "2026-11-05 -$i day" +%F)
done
```

40 backups (de 2026-09-27 a 2026-11-05), 31 apagados. Ficaram:

```
pagila_2026-10-18_1155.counts
pagila_2026-10-18_1155.dump
pagila_2026-10-25_1155.counts
pagila_2026-10-25_1155.dump
pagila_2026-10-30_1155.counts
pagila_2026-10-30_1155.dump
pagila_2026-10-31_1155.counts
pagila_2026-10-31_1155.dump
pagila_2026-11-01_1155.counts
pagila_2026-11-01_1155.dump
pagila_2026-11-02_1155.counts
pagila_2026-11-02_1155.dump
pagila_2026-11-03_1156.counts
pagila_2026-11-03_1156.dump
pagila_2026-11-04_1156.counts
pagila_2026-11-04_1156.dump
pagila_2026-11-05_1156.counts
pagila_2026-11-05_1156.dump
```

| Ficheiro | Dia | Semana ISO | Porque ficou |
|---|---|---|---|
| `pagila_2026-11-05_*` | qui | W45 | último dos dias 1–7 (e da semana W45) |
| `pagila_2026-11-04_*` | qua | W45 | dia 2 |
| `pagila_2026-11-03_*` | ter | W45 | dia 3 |
| `pagila_2026-11-02_*` | seg | W45 | dia 4 |
| `pagila_2026-11-01_*` | dom | W44 | dia 5 (e o último da semana W44) |
| `pagila_2026-10-31_*` | sáb | W44 | dia 6 |
| `pagila_2026-10-30_*` | sex | W44 | dia 7 |
| `pagila_2026-10-25_*` | dom | W43 | último da semana W43 |
| `pagila_2026-10-18_*` | dom | W42 | último da semana W42 |

7 diários + 2 semanais a mais (as semanas W45 e W44 já estão cobertas pelos diários) = 9 backups.
São os esperados: no máximo 7 diários e 4 semanais.

## `verify.sh`

1. Escolhe o dump mais recente (os nomes ordenam por data).
2. `docker run --rm -d postgres:18`: um contentor limpo, apagado no fim (`trap ... EXIT`).
3. `pg_restore`, conta as linhas de todas as tabelas e faz `diff` com o `.counts` desse dump.
4. Mostra as diferenças e sai com 1 se houver alguma; senão sai com 0.

Dump bom:

```
2026-11-05 11:56:17 verificar backups/pagila/pagila_2026-11-05_1156.dump
2026-11-05 11:56:25 OK: as 70 tabelas têm as contagens do .counts
exit=0
```

Dump alterado de propósito: substituí o dump mais recente por um de uma cópia do `pagila` com 10
linhas a menos em `film_actor`, mantendo o `.counts` original:

```
2026-11-05 11:56:29 verificar backups/pagila/pagila_2026-11-05_1156.dump
2026-11-05 11:56:37 ERRO: contagens diferentes (< .counts, > restaurado):
8c8
< film_actor 5462
---
> film_actor 5452
exit=1
```

## Tarefa 4 — agendamento (cron)

O cron não vem no devcontainer. Instalar e arrancar:

```bash
sudo apt-get install -y cron
sudo service cron start
```

Configuração (`crontab -e`): o backup todos os dias às 02:00 e a verificação às 02:30. O cron não
carrega o PATH do utilizador, por isso é preciso indicar onde está o `docker`:

```
PATH=/usr/local/bin:/usr/bin:/bin
0 2 * * *  bash /workspaces/databases_module/exercises/10-backup/challenge/backup.sh >> /workspaces/databases_module/backups/pagila/cron.log 2>&1
30 2 * * * bash /workspaces/databases_module/exercises/10-backup/challenge/verify.sh >> /workspaces/databases_module/backups/pagila/cron.log 2>&1
```

Os dois scripts funcionam com o ambiente mínimo do cron (testado com `env -i PATH=/usr/local/bin:/usr/bin:/bin`, a partir de outra pasta):

```
2026-11-05 11:56:47 backup backups/pagila/pagila_2026-11-05_1156.dump (4.4M, 70 tabelas)
2026-11-05 11:56:48 verificar backups/pagila/pagila_2026-11-05_1156.dump
2026-11-05 11:56:55 OK: as 70 tabelas têm as contagens do .counts
exit=0
```

Para ver duas execuções agendadas sem esperar dois dias, a mesma configuração de 2 em 2 minutos
(backup nos minutos pares, verificação nos ímpares):

```
PATH=/usr/local/bin:/usr/bin:/bin
*/2 * * * *    bash /workspaces/databases_module/exercises/10-backup/challenge/backup.sh >> /workspaces/databases_module/backups/pagila/cron.log 2>&1
1-59/2 * * * * bash /workspaces/databases_module/exercises/10-backup/challenge/verify.sh >> /workspaces/databases_module/backups/pagila/cron.log 2>&1
```

Log de duas execuções agendadas (`cat backups/pagila/cron.log`):

```
2026-11-15 18:10:02 backup backups/pagila/pagila_2026-11-15_1810.dump (4.4M, 70 tabelas)
2026-11-15 18:11:01 verificar backups/pagila/pagila_2026-11-15_1810.dump
2026-11-15 18:11:07 OK: as 70 tabelas têm as contagens do .counts
2026-11-15 18:12:02 backup backups/pagila/pagila_2026-11-15_1812.dump (4.4M, 70 tabelas)
2026-11-15 18:12:02 apagado backups/pagila/pagila_2026-11-15_1810.dump
2026-11-15 18:13:01 verificar backups/pagila/pagila_2026-11-15_1812.dump
2026-11-15 18:13:07 OK: as 70 tabelas têm as contagens do .counts
```

Duas execuções agendadas de cada script, as duas com `OK`. O backup das 18:12 apagou o das 18:10
porque a retenção só guarda o último backup de cada dia. Depois da demonstração, a agenda de 2 em 2
minutos foi removida (`crontab -r`).
