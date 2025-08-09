# Análise de Performance de Consultas no Django ORM

Este projeto contém uma suíte de testes prática para demonstrar e analisar o impacto de diferentes estratégias de otimização de consultas no Django ORM, especialmente em um cenário com grande volume de dados.

O objetivo é fornecer um ambiente controlado para reproduzir os cenários apresentados na videoaula sobre Otimização de Consultas.

## Setup do Ambiente

Para executar os testes, siga os passos abaixo:

**1. Clone o Repositório e Navegue para a Branch:**
```bash
git clone <url-do-seu-repositorio>
cd <nome-do-projeto>
git checkout feat/orm-optimization-video
````

**2. Crie e Ative um Ambiente Virtual:**

```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

**3. Instale as Dependências:**

```bash
pip install -r requirements/local.txt
```

**4. Configure as Variáveis de Ambiente:**
Copie o arquivo de exemplo e, se necessário, ajuste as configurações do banco de dados.

```bash
cp .env.example .env
```

**5. Aplique as Migrações do Banco de Dados:**

```bash
python manage.py migrate
```

**6. Popule o Banco de Dados (Passo Crucial):**
Para simular um ambiente de produção e tornar os efeitos da otimização visíveis, use o nosso *management command* para criar um grande número de transações.

Execute o comando abaixo para criar 100.000 transações (sinta-se à vontade para aumentar o número para ver um impacto ainda maior, como `1000000`).

```bash
python manage.py populate_transactions --count 100000
```

**Aguarde o término do processo.**

**7. Inicie o Servidor de Desenvolvimento:**

```bash
python manage.py runserver
```

O servidor estará rodando em `http://127.0.0.1:8000/`.

-----

## Testando os Endpoints de Performance

Para realizar os testes, você precisará de duas ferramentas:

  - Um cliente de API como **Postman** ou **Insomnia**.
  - Um navegador web para visualizar a **Django Debug Toolbar**.

### Cenários de Teste

Temos três endpoints para comparar, cada um representando uma estratégia diferente.

#### Cenário 1: Não Otimizado (N+1 Paginado)

  - **URL:** `http://127.0.0.1:8000/api/v1/transactions/performance-test/unoptimized/`
  - **O que observar:**
      - **No Postman:** Anote o valor do campo `processing_time_ms`. Este é o nosso tempo base.
      - **Na Debug Toolbar:** Observe o **número de queries** e o **tempo total**.

#### Cenário 2: Otimizado com `select_related` (JOIN Gigante)

  - **URL:** `http://127.0.0.1:8000/api/v1/transactions/performance-test/optimized-join/`
  - **O que observar:**
      - **No Postman:** Compare o `processing_time_ms` com o cenário anterior.
      - **Na Debug Toolbar:** Haverá **apenas 1 query**, mas o seu tempo de execução individual poderá ser alto. Use o botão **"EXPLAIN"** na query para ver o plano de execução custoso do banco de dados.

#### Cenário 3: Otimizado com `prefetch_related` (Estratégia Correta)

  - **URL:** `http://127.0.0.1:8000/api/v1/transactions/performance-test/optimized-prefetch/`
  - **O que observar:**
      - **No Postman:** O `processing_time_ms` deve ser **ligeiramente menor** que os dois cenários anteriores.
      - **Na Debug Toolbar:** O número de queries será pequeno (ex: 4 ou 5 queries). Todas serão extremamente rápidas individualmente, resultando no menor tempo total.

### Resultados Esperados

| Cenário | Estratégia | Queries (p/ Página) | Análise |
| :--- | :--- | :--- | :--- | :--- |
| 1. Unoptimized | N+1 Paginado | \~25 | Muitas viagens ao banco. |
| 2. Optimized JOIN | `select_related` | 1 | Custo do `JOIN` em larga escala. |
| 3. Optimized Prefetch| `prefetch_related`| \~5 | Estratégia de query mais eficiente. |