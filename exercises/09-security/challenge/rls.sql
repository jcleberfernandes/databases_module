-- Challenge 09: row-level security em rental e payment
-- Correr como superuser na base ex09, depois de ../exercise/roles.sql

ALTER TABLE rental  ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment ENABLE ROW LEVEL SECURITY;

-- Só as linhas do cliente definido em app.customer_id.
-- current_setting(..., true) devolve NULL se não estiver definido -> não vê nada.
-- USING filtra as leituras; WITH CHECK impede escrever linhas de outro cliente.
DROP POLICY IF EXISTS rental_by_customer ON rental;
CREATE POLICY rental_by_customer ON rental TO app
    USING (customer_id = current_setting('app.customer_id', true)::int)
    WITH CHECK (customer_id = current_setting('app.customer_id', true)::int);

DROP POLICY IF EXISTS payment_by_customer ON payment;
CREATE POLICY payment_by_customer ON payment TO app
    USING (customer_id = current_setting('app.customer_id', true)::int)
    WITH CHECK (customer_id = current_setting('app.customer_id', true)::int);

-- payment está particionada: as políticas da tabela-mãe NÃO se aplicam se alguém
-- consultar uma partição diretamente (ex: payment_p2022_01). Por isso o app perde
-- o acesso direto às partições e só pode passar pela tabela payment.
DO $$
DECLARE p regclass;
BEGIN
    FOR p IN SELECT inhrelid::regclass FROM pg_inherits WHERE inhparent = 'payment'::regclass LOOP
        EXECUTE format('REVOKE ALL ON %s FROM app', p);
    END LOOP;
END $$;
