-- Impressão digital dos dados do seed (sem a coluna uuid, que é aleatória)
SELECT count(*) AS rows,
       md5(string_agg(concat_ws('|', rental_id, rental_date, inventory_id, customer_id,
                                return_date, staff_id, last_update), ',' ORDER BY rental_id)) AS md5
FROM rental
WHERE rental_id >= 1000001;
