-- Challenge 05: graus de separação entre atores (até 3)
-- Ator de partida: 1 (PENELOPE GUINESS). Muda o número em "start" para outro ator.

WITH RECURSIVE
start AS (SELECT 1 AS actor_id),
-- Dois atores estão a distância 1 se entraram no mesmo filme
costar AS (
    SELECT DISTINCT fa1.actor_id AS a, fa2.actor_id AS b
    FROM film_actor fa1
    JOIN film_actor fa2 ON fa2.film_id = fa1.film_id AND fa2.actor_id <> fa1.actor_id
),
walk (actor_id, distance, visited) AS (
    SELECT actor_id, 0, ARRAY[actor_id] FROM start
    UNION ALL
    SELECT c.b, w.distance + 1, w.visited || c.b
    FROM walk w
    JOIN costar c ON c.a = w.actor_id
    WHERE w.distance < 3                -- termina: nunca passa de 3 graus
      AND c.b <> ALL (w.visited)        -- não volta a um ator já visitado neste caminho
)
SELECT w.actor_id, a.first_name, a.last_name, min(w.distance) AS shortest_distance
FROM walk w
JOIN actor a ON a.actor_id = w.actor_id
WHERE w.distance > 0
GROUP BY w.actor_id, a.first_name, a.last_name
ORDER BY shortest_distance, w.actor_id;
