-- Exercício 07: os índices que ficaram (cada um justificado por uma melhoria medida, ver README)

-- Q1: só os ~3% de alugueres por devolver, por cliente (índice parcial).
--     count(*) responde só com o índice (Index Only Scan).
CREATE INDEX big_rental_open_customer ON big_rental (customer_id) WHERE returned_at IS NULL;

-- Q2 (e a Q3 reescrita como intervalo): filtro e ordenação por rented_at.
CREATE INDEX big_rental_rented_at ON big_rental (rented_at);

-- Q5: igualdade em customer_id primeiro, intervalo e ordenação em rented_at depois.
CREATE INDEX big_rental_customer_rented ON big_rental (customer_id, rented_at);

-- Q4: nenhum. Lê 97% da tabela; o índice só ajudava um pouco se fosse forçado, e o planner
--     (com razão) não o escolhe.
-- Q3 tal como está escrita: nenhum. rented_at::date não usa o índice de rented_at, e um índice
--     em (rented_at::date) não se pode criar (a conversão de timestamptz em date não é IMMUTABLE).

VACUUM ANALYZE big_rental;
