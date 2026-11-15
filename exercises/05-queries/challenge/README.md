# Challenge 05 — Graus de separação entre atores

Ficheiro: `degrees.sql` (as queries das tarefas 2 e 3).

```bash
./scripts/create-db.sh ch05 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ch05 < exercises/05-queries/challenge/degrees.sql
```

Dois atores estão **ligados** se entraram juntos em pelo menos 3 filmes. A CTE
`edge(actor_id, other_actor_id)` tem cada par ligado nos dois sentidos
(`film_actor` com ela própria, `GROUP BY` do par, `HAVING count(*) >= 3`).

## Tarefa 2 — atores a 3 graus ou menos do ator 1

`walk` começa no ator 1 com `distance = 0` e `path = ARRAY[1]`; cada passo segue uma ligação e
acrescenta o ator novo ao `path`. No fim, `min(distance)` por ator dá a distância mais curta.
O ator 1 fica de fora do resultado. 141 atores:

| Distância | Atores |
|---|---|
| 1 | 3 |
| 2 | 23 |
| 3 | 115 |

Primeiras linhas:

```
 actor_id | first_name  |  last_name   | distance 
----------+-------------+--------------+----------
        4 | JENNIFER    | DAVIS        |        1
       20 | LUCILLE     | TRACY        |        1
       64 | RAY         | JOHANSSON    |        1
        7 | GRACE       | MOSTEL       |        2
       13 | UMA         | WOOD         |        2
       16 | FRED        | COSTNER      |        2
 ...
(141 rows)
```

**Verificação.** Os atores a distância 1 têm de ser exatamente os que entraram em 3 ou mais filmes
com o ator 1. Contei-os à parte, sem a CTE recursiva: são 3, os mesmos da tabela (4, 20 e 64).
Por exemplo, o ator 20 (LUCILLE TRACY) entrou com o ator 1 em `ACADEMY DINOSAUR`,
`CHEAPER CLYDE` e `KING EVOLUTION`.

## Tarefa 3 — caminho mais curto do ator 1 ao ator 200 (até 5 graus)

Mesma `walk`, até 5 graus, e um caminho deixa de continuar quando chega ao 200. Do conjunto dos
caminhos que acabam no 200 fica o mais curto, e o `path` é convertido em nomes (`unnest ... WITH ORDINALITY`).
Se não houvesse caminho até 5 graus, a query devolvia 0 linhas.

```
 distance |                                          path                                           
----------+-----------------------------------------------------------------------------------------
        4 | PENELOPE GUINESS -> LUCILLE TRACY -> GINA DEGENERES -> ANGELINA ASTAIRE -> THORA TEMPLE
(1 row)

```

O ator 200 (THORA TEMPLE) está a 4 graus do ator 1.

## Porque a query não corre para sempre

Uma CTE recursiva repete o passo recursivo enquanto ele produzir linhas novas. Duas condições
garantem que acaba:

1. **Limite de profundidade:** `WHERE w.distance < 3` (ou `< 5` na tarefa 3). Um caminho com 3
   ligações já não gera mais nenhum, por isso no máximo há 3 (ou 5) passos.
2. **Sem voltar atrás:** `e.other_actor_id <> ALL (w.path)`. O `path` guarda os atores do caminho;
   um ator que já lá está não volta a entrar. Sem isto, A → B → A → B ... criava ciclos (e
   caminhos repetidos que só faziam a consulta mais lenta).

O mesmo ator pode aparecer por caminhos diferentes (por isso o `min(distance)` no fim), mas nunca
duas vezes no mesmo caminho.
