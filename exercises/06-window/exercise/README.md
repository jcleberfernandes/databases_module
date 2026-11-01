# Exercício 06 — Window functions e views

Ficheiro: `queries.sql`.

```bash
./scripts/create-db.sh ex06 --pagila
docker compose exec -T postgres psql -U postgres -d ex06 -v ON_ERROR_STOP=1 < exercises/06-window/exercise/queries.sql
```

| # | Pergunta | Window function | Linhas |
|---|---|---|---|
| 1 | Top 3 filmes por categoria | `DENSE_RANK` | 56 (16×3 + empates) |
| 2 | Receita acumulada por dia (primeiros 15 dias) | `SUM() OVER (ORDER BY day)` | 15 |
| 3 | Variação face ao mês anterior | `LAG` | 55 |
| 4 | Posição do cliente no ranking da loja (top 20) | `RANK` | 20 |
| 5 | View materializada da receita mensal + refresh | — | — |

## Empates (1)

Com `DENSE_RANK` os filmes empatados ficam com a mesma posição e entram todos.
Exemplo: em Animation há dois filmes com 102 alugueres, os dois ficam em 1.º:

```
 Animation   |   1 | GILMORE BOILED       |     102
 Animation   |   1 | GRIT CLOCKWORK       |     102
 Animation   |   2 | EXPENDABLE STALLION  |      98
 Animation   |   3 | WITCHES PANIC        |      97
```

## Excertos

```
    day     | revenue | cumulative_revenue
 2022-01-23 |  161.60 |             161.60
 2022-01-24 |  366.18 |             527.78

   month    | revenue  | previous_month |  change  | change_pct
 2022-01-01 |  3094.78 |                |          |
 2022-02-01 | 10164.97 |        3094.78 |  7070.19 |      228.5
 2022-03-01 | 11413.86 |       10164.97 |  1248.89 |       12.3
```

## View materializada (5)

Um pagamento novo de 100.00 em março só aparece depois do `REFRESH`:

```
antes do INSERT:   2022-03-01 | 11413.86 | 2713
depois do INSERT:  2022-03-01 | 11413.86 | 2713   (a view não mudou)
depois do REFRESH: 2022-03-01 | 11513.86 | 2714
```

O índice único em `month` permite `REFRESH ... CONCURRENTLY`, que não bloqueia quem está a ler a view.
