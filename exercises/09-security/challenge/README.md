# Challenge 09 — Row-level security

Ficheiros: `rls.sql` (ativa RLS e cria as políticas) e `rls_test.sql` (provas, corre como `app`).

```bash
# como superuser, depois de ../exercise/roles.sql
docker compose exec -T postgres psql -U postgres -d ex09 -v ON_ERROR_STOP=1 < exercises/09-security/challenge/rls.sql
# login COMO app (o contentor aceita ligações locais sem password)
docker compose exec -T postgres psql -U app -d ex09 < exercises/09-security/challenge/rls_test.sql
```

Política (igual para `rental` e `payment`):

```sql
CREATE POLICY rental_by_customer ON rental TO app
    USING (customer_id = current_setting('app.customer_id', true)::int)
    WITH CHECK (customer_id = current_setting('app.customer_id', true)::int);
```

A aplicação faz `SET app.customer_id = '42'` no início de cada pedido.

`payment` é particionada e as políticas da tabela-mãe não se aplicam a quem lê
uma partição diretamente; por isso `rls.sql` tira ao `app` o acesso às partições.

## Prova

Totais reais (como superuser): 51 805 alugueres (69 do cliente 42) e 51 061 pagamentos (68 do cliente 42).

Como `app` (ordem real das mensagens):

```
--- ligado como:
 current_user | session_user
--------------+--------------
 app          | app

--- app sem app.customer_id: não vê nada
 rentals
---------
       0

--- app com app.customer_id = 42: query SEM WHERE
 rentals | customers | min | max
---------+-----------+-----+-----
      69 |         1 |  42 |  42

 payments | customers | min | max
----------+-----------+-----+-----
       68 |         1 |  42 |  42
```

Só aparecem as linhas do cliente 42, sem nenhum `WHERE`.

## O app não consegue contornar a política

```
--- tentativa 1: pedir outro cliente no WHERE
 count
-------
     0
--- tentativa 2: desligar o RLS na sessão (SET row_security = off)
ERROR:  query would be affected by row-level security policy for table "rental"
--- tentativa 3: desligar o RLS na tabela
ERROR:  must be owner of table rental
--- tentativa 4: ler uma partição de payment diretamente
ERROR:  permission denied for table payment_p2022_01
--- tentativa 5: inserir um aluguer de outro cliente
ERROR:  new row violates row-level security policy for table "rental"
--- tentativa 6: passar a superuser
ERROR:  permission denied to set role "postgres"
--- o app não tem BYPASSRLS nem é dono das tabelas
 rolname | rolsuper | rolbypassrls
---------+----------+--------------
 app     | f        | f
 tableowner
------------
 postgres
```

O RLS só é ignorado por superusers, roles com `BYPASSRLS` e o dono da tabela.
O `app` não é nenhum destes, por isso fica sempre sujeito à política.

Nota: o `app.customer_id` é definido pela aplicação. Se um atacante conseguisse
correr SQL como `app` (ex: SQL injection), podia fazer `SET app.customer_id`
para outro cliente. Por isso o RLS complementa as queries parametrizadas, não as substitui.
