-- Prova da tarefa 3: cada job processado exatamente uma vez
SELECT (SELECT count(*) FROM job)                          AS jobs,
       (SELECT count(*) FROM job WHERE status = 'done')    AS done,
       (SELECT count(*) FROM job_result)                   AS results,
       (SELECT count(DISTINCT job_id) FROM job_result)     AS distinct_jobs;

-- jobs com mais de uma linha em job_result (tem de dar 0 linhas)
SELECT job_id, count(*) FROM job_result GROUP BY job_id HAVING count(*) > 1;

-- quantos jobs fez cada worker
SELECT worker, count(*) FROM job_result GROUP BY worker ORDER BY worker;
