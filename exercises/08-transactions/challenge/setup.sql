-- Challenge 08: as tabelas do enunciado (base ch08)
CREATE TABLE job (
    job_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payload jsonb NOT NULL,
    status  text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'done'))
);

CREATE TABLE job_result (
    job_id       bigint NOT NULL REFERENCES job,
    worker       integer NOT NULL,
    processed_at timestamptz NOT NULL DEFAULT now()
);
