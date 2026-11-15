# Challenge 14 — Relatório diário incremental com `$merge`

Ficheiros:
- `daily_revenue.py` — o relatório (`run_report`) e o watermark em `report_state`.
- `tests/test_daily_revenue.py` — o teste.
- `config.py`, `pyproject.toml`, `.env.example` (`MONGO_URL`; sem `.env` usa a password do `.env` da raiz).

```bash
cd exercises/14-pipelines/challenge
uv run python daily_revenue.py      # corre o relatório em pagila_docs
uv run pytest -v -s                 # o teste
```

O teste usa `pagila_docs.rentals`. No fim apaga os 5 alugueres de teste e o relatório,
para `rentals` ficar como estava.

## Como funciona

- `daily_revenue`: `{_id: "2026-07-28", rentals: 20, revenue: Decimal128("52.81")}`.
- `report_state`: `{_id: "daily_revenue", watermark: <maior rentals._id processado>}`.

Cada execução:
1. lê o watermark;
2. encontra os **dias** dos alugueres com `_id > watermark`;
3. recalcula esses dias inteiros a partir de **todos** os alugueres desses dias e faz
   `$merge` em `daily_revenue` com `whenMatched: "replace"`;
4. só depois avança o watermark.

Em `pagila_docs`:

```
dias recalculados: 1476 (2022-02-14 ... 2026-07-28)
daily_revenue: 1476 dias
dias recalculados: 0
daily_revenue: 1476 dias
```

## Saída do teste

```
tests/test_daily_revenue.py::test_incremental_report
1.ª execução: 1476 dias recalculados, daily_revenue com 1476 dias
2.ª execução: recalculou ['2026-07-28', '2026-07-29']; dias diferentes em daily_revenue: ['2026-07-28', '2026-07-29']
   2026-07-28 antes={'_id': '2026-07-28', 'rentals': 20, 'revenue': Decimal128('52.81')} depois={'_id': '2026-07-28', 'rentals': 23, 'revenue': Decimal128('61.78')}
   2026-07-29 depois={'_id': '2026-07-29', 'rentals': 2, 'revenue': Decimal128('5.98')}
4. recálculo completo: 1477 dias, igual a daily_revenue: True
3.ª execução: recalculou []; daily_revenue igual: True
PASSED

============================== 1 passed in 1.74s ===============================
```

1. 1.ª execução: os 1476 dias.
2. 5 alugueres novos: 3 em `2026-07-28` (já existia) e 2 em `2026-07-29` (novo).
3. 2.ª execução: só esses 2 dias mudam (`2026-07-28` de 20 para 23 alugueres; `2026-07-29` aparece).
4. `daily_revenue` é igual a um recálculo completo do zero.
5. 3.ª execução: não muda nada.

## Porque recalcular o dia inteiro e não somar os valores novos

- **Pode repetir-se sem estragar nada (idempotente).** Se o processo morrer depois do
  `$merge` e antes de gravar o watermark, a próxima execução processa outra vez os mesmos
  alugueres. Recalculando o dia, o resultado é o mesmo; somando (`$inc`), esses valores
  contavam duas vezes.
- **Apanha correções.** Se um aluguer antigo desse dia for corrigido ou apagado, recalcular
  o dia dá o valor certo; somar só os novos nunca o corrigia.
- **O resultado depende só dos dados, não do histórico de execuções**: é sempre igual ao
  recálculo completo (passo 4 do teste). O custo é pequeno, porque só se recalculam os dias
  que tiveram alugueres novos.
