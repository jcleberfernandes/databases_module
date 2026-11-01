# Challenge 10 — backup.sh, verify.sh e cron

Ficheiros:
- `backup.sh` — dump `-Fc` com data/hora no nome + retenção 7 diários / 4 semanais.
- `verify.sh` — restaura o último dump num contentor descartável e compara as contagens de todas as tabelas com a produção; código de saída 1 se houver diferenças.
- `crontab.txt` — agenda diária (02:00 backup, 02:30 verify).
- `crontab-demo.txt` — a mesma agenda de 2 em 2 minutos, para ver duas execuções.

```bash
bash exercises/10-backup/challenge/backup.sh ex10
bash exercises/10-backup/challenge/verify.sh ex10; echo "exit=$?"
```

Os dumps ficam em `backups/ex10/daily/` e `backups/ex10/weekly/` (`backups/` está no `.gitignore`).

## backup.sh

- Nome: `backups/ex10/daily/ex10_2026-11-01_184327.dump`.
- Escreve primeiro para `.tmp` e só renomeia se o `pg_dump` terminou bem.
- Semanal: o primeiro backup de cada semana ISO é copiado para `weekly/ex10_2026-W44.dump`.
- Retenção: `ls -1t | tail -n +8 | xargs rm` (fica com 7 diários) e `tail -n +5` (fica com 4 semanais).

Teste da retenção diária (10 backups seguidos → ficam 7):

```
2026-11-01 18:44:18 backup backups/ex10/daily/ex10_2026-11-01_184417.dump (4.4M)
removed 'backups/ex10/daily/ex10_2026-11-01_184402.dump'
```

Teste da retenção semanal (com semanas W39–W43 simuladas → ficam W41–W44):

```
removed 'backups/ex10/weekly/ex10_2026-W40.dump'
removed 'backups/ex10/weekly/ex10_2026-W39.dump'
```

## verify.sh

- `docker run --rm -d postgres:18` → contentor limpo, apagado no fim (`trap ... EXIT`).
- `pg_restore` do dump mais recente.
- Conta as linhas de **todas** as tabelas de `public` (70) nos dois lados e faz `diff`.

Backup certo:

```
2026-11-01 18:43:28 verificar backups/ex10/daily/ex10_2026-11-01_184327.dump
2026-11-01 18:43:36 OK: 70 tabelas com as mesmas contagens
exit=0
```

Com um ator inserido em produção depois do backup:

```
2026-11-01 18:43:57 ERRO: contagens diferentes (< backup, > produção):
1c1
< actor 200
---
> actor 201
exit=1
```

## cron

O cron não vinha no devcontainer; instalar e arrancar:

```bash
sudo apt-get install -y cron
sudo service cron start
```

Agenda (`crontab.txt`):

```
PATH=/usr/local/bin:/usr/bin:/bin
0 2 * * *  bash .../challenge/backup.sh ex10 >> .../backups/ex10/cron.log 2>&1
30 2 * * * bash .../challenge/verify.sh ex10 >> .../backups/ex10/cron.log 2>&1
```

Para ver duas execuções sem esperar dois dias:

```bash
crontab exercises/10-backup/challenge/crontab-demo.txt   # de 2 em 2 minutos
# esperar ~5 minutos
cat backups/ex10/cron.log
crontab exercises/10-backup/challenge/crontab.txt        # voltar à agenda diária
```

Log de duas execuções:

```
(colar aqui o conteúdo de backups/ex10/cron.log)
```
