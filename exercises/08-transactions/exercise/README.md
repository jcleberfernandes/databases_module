# Exercício 08 — Transações e concorrência

Ficheiros:
- `setup.sql` — o SQL do enunciado (coluna `balance` e 14 funcionários novos na loja 1, que fica com 20 ativos).
- `lost_update.md` — tarefas 1 e 2 (as duas sessões, em tabela, com os resultados).
- `deadlock.md` — tarefa 3 (as duas sessões, a mensagem completa explicada linha a linha, e como evitar).
- `write_skew.py`, `pyproject.toml`, `.env.example` — tarefa 4.

```bash
./scripts/create-db.sh ex08 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ex08 -v ON_ERROR_STOP=1 < exercises/08-transactions/exercise/setup.sql
# tarefas 1 a 3: duas sessões psql, como em lost_update.md e deadlock.md
docker compose exec postgres psql -U postgres -d ex08
# tarefa 4
cd exercises/08-transactions/exercise
uv run python write_skew.py read_committed
docker compose exec -T postgres psql -U postgres -d ex08 -c "UPDATE staff SET active = true WHERE store_id = 1;"
uv run python write_skew.py serializable
```

Resumo das tarefas 1 a 3: o lost update dá **90** em vez de 80; com o `UPDATE` atómico e com o
`SELECT ... FOR UPDATE` o saldo final é **80**; o deadlock dá `ERROR: deadlock detected` e cancela
uma das transações.

## Tarefa 4 — write skew

`write_skew.py` cria 20 threads, uma por funcionário ativo da loja 1, cada uma com a sua ligação.
Cada uma corre uma transação: conta os ativos da loja 1; espera num `threading.Barrier(20)` (assim
todas leem antes de alguma escrever); se a contagem for maior do que 1, desativa o seu funcionário;
`COMMIT`. Em `SERIALIZABLE`, uma transação que falha com `SerializationFailure` (SQLSTATE `40001`)
é repetida desde o início, sem a barreira.

```
READ COMMITTED: 20 funcionários ativos na loja 1 no início
READ COMMITTED: 0 funcionários ativos na loja 1 no fim (0 transações repetidas)
UPDATE 20
SERIALIZABLE: 20 funcionários ativos na loja 1 no início
SERIALIZABLE: 1 funcionários ativos na loja 1 no fim (146 transações repetidas)
```

Repeti mais duas vezes: sempre 0 com `READ COMMITTED` e sempre 1 com `SERIALIZABLE` (139 e 150 repetições).

**Porque `READ COMMITTED` quebra a regra.** Cada thread lê "20 ativos" e decide que pode
desativar o seu funcionário. Cada uma escreve numa **linha diferente**, por isso nenhum lock as
trava: não há conflito de escrita para o PostgreSQL detetar. A regra depende do conjunto das
linhas (quantas estão ativas), mas cada transação só vê o que leu no início. As 20 desativam e a
loja fica com 0 — é o *write skew*.

**Porque `SERIALIZABLE` não quebra.** Neste nível o PostgreSQL vigia também o que cada transação
**leu**. Ele vê que a transação X leu linhas que a Y mudou, e a Y leu linhas que a X mudou: não há
nenhuma ordem em série que dê este resultado. Por isso cancela uma delas com o erro `40001`. A
transação repetida lê outra vez e já vê a contagem atualizada. As que leem 1 já não desativam
ninguém, e fica exatamente **1** ativo.
