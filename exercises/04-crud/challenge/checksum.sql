-- Contagem e checksum das linhas novas (o do enunciado)
SELECT count(*) AS rows,
       md5(string_agg(concat_ws('|', rental_id, rental_date, inventory_id, customer_id, return_date, staff_id),
                      ',' ORDER BY rental_id)) AS checksum
FROM rental WHERE rental_id > 100000;
