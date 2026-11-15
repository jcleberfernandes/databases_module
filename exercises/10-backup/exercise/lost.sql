-- RPO: os 5 pagamentos de activity.sql (feitos depois do backup) estão em falta depois do restore?
-- (os 5 alugueres mais recentes, sem o pagamento de 1.99 de 2026-07-30 12:00)
SELECT r.rental_id, r.customer_id, 1.99 AS amount, timestamptz '2026-07-30 12:00+00' AS payment_date
FROM (SELECT rental_id, customer_id FROM rental ORDER BY rental_id DESC LIMIT 5) r
WHERE NOT EXISTS (
    SELECT 1 FROM payment p
    WHERE p.rental_id = r.rental_id AND p.amount = 1.99 AND p.payment_date = '2026-07-30 12:00+00'
)
ORDER BY r.rental_id;
