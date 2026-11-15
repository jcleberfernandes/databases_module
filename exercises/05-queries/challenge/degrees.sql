-- Challenge 05: graus de separação entre atores
-- ./scripts/create-db.sh ch05 --pagila --reset
-- docker compose exec -T postgres psql -U postgres -d ch05 < exercises/05-queries/challenge/degrees.sql
-- Dois atores estão ligados se entraram juntos em pelo menos 3 filmes.

-- Tarefa 2: atores a 3 graus ou menos do ator 1, com a distância mais curta
WITH RECURSIVE
edge (actor_id, other_actor_id) AS (
    -- cada par ligado, nos dois sentidos
    SELECT fa1.actor_id, fa2.actor_id
    FROM film_actor fa1
    JOIN film_actor fa2 ON fa2.film_id = fa1.film_id AND fa2.actor_id <> fa1.actor_id
    GROUP BY fa1.actor_id, fa2.actor_id
    HAVING count(*) >= 3
),
walk (actor_id, distance, path) AS (
    SELECT 1, 0, ARRAY[1]
    UNION ALL
    SELECT e.other_actor_id, w.distance + 1, w.path || e.other_actor_id
    FROM walk w
    JOIN edge e ON e.actor_id = w.actor_id
    WHERE w.distance < 3                        -- para sozinho: nunca passa de 3 graus
      AND e.other_actor_id <> ALL (w.path)      -- nunca volta a um ator do mesmo caminho
)
SELECT w.actor_id, a.first_name, a.last_name, min(w.distance) AS distance
FROM walk w
JOIN actor a ON a.actor_id = w.actor_id
WHERE w.actor_id <> 1
GROUP BY w.actor_id, a.first_name, a.last_name
ORDER BY distance, w.actor_id;

-- Tarefa 3: o caminho mais curto do ator 1 ao ator 200 (até 5 graus), como lista de nomes
WITH RECURSIVE
edge (actor_id, other_actor_id) AS (
    SELECT fa1.actor_id, fa2.actor_id
    FROM film_actor fa1
    JOIN film_actor fa2 ON fa2.film_id = fa1.film_id AND fa2.actor_id <> fa1.actor_id
    GROUP BY fa1.actor_id, fa2.actor_id
    HAVING count(*) >= 3
),
walk (actor_id, distance, path) AS (
    SELECT 1, 0, ARRAY[1]
    UNION ALL
    SELECT e.other_actor_id, w.distance + 1, w.path || e.other_actor_id
    FROM walk w
    JOIN edge e ON e.actor_id = w.actor_id
    WHERE w.distance < 5
      AND e.other_actor_id <> ALL (w.path)
      AND w.actor_id <> 200                     -- quando chega ao 200, esse caminho já não continua
),
shortest AS (
    SELECT path FROM walk WHERE actor_id = 200 ORDER BY distance, path LIMIT 1
)
SELECT array_length(s.path, 1) - 1 AS distance,
       string_agg(a.first_name || ' ' || a.last_name, ' -> ' ORDER BY p.pos) AS path
FROM shortest s
CROSS JOIN LATERAL unnest(s.path) WITH ORDINALITY AS p(actor_id, pos)
JOIN actor a ON a.actor_id = p.actor_id
GROUP BY s.path;
