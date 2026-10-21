# Challenge — Escritas concorrentes

Este desafio inicia 10 processos. Cada processo tenta adicionar 1.000
registros:

1. Primeiro, os processos fazem leitura, adição e gravação no mesmo arquivo
   `messages.json`.
2. Depois, os processos usam conexões diferentes para inserir registros na
   tabela `challenge_messages` do PostgreSQL.
3. No fim, o programa conta os registros encontrados em cada lugar.

## Como executar

Na raiz do projeto, deixe os containers em execução:

```bash
docker compose up -d --wait
```

O script precisa do pacote `psycopg`, que já está nas dependências do FastAPI:

```bash
cd exercises/ex01database-engines/individual/fastapi
uv run python ../../challange/concurrent_writes.py
```

Também é possível informar outro arquivo JSON:

```bash
uv run python ../../challange/concurrent_writes.py --json-file /tmp/messages.json
```

## Resultado esperado

O total esperado é de 10.000 registros. O arquivo JSON normalmente terá menos
registros, porque dois processos podem ler o mesmo conteúdo e um pode apagar a
alteração feita pelo outro quando grava novamente. Em alguns casos, o arquivo
também pode ficar inválido por causa de duas gravações ao mesmo tempo.

O PostgreSQL deve terminar com 10.000 registros. Cada processo usa uma conexão
separada e cada inserção é tratada pelo banco, por isso as gravações não
substituem umas às outras.

O script limpa a tabela `challenge_messages` antes de começar. Ela é uma tabela
criada apenas para este desafio.
