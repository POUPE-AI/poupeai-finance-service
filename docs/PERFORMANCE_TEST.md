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

## Relatório de Performance (Resultados Esperados)

A tabela abaixo resume os resultados esperados ao testar os diferentes endpoints. Os valores de tempo são ilustrativos e podem variar dependendo da sua máquina, mas a ordem de grandeza e a diferença no número de queries serão consistentes.

### Cenário 1: Paginação com 10 Itens (`?page_size=10`)

| Estratégia | Nº de Queries (Debug Toolbar) | Tempo Total das Queries (ms) | Tempo de Processamento da API (ms) | Análise Rápida |
| :--- | :---: | :---: | :---: | :--- |
| **Não Otimizado** | \~22 | \~87 ms | \~130 ms | O problema N+1 ainda não é devastador. |
| **`select_related`** | \~2 | \~91 ms | \~110 ms | Não tão eficiente. |
| **`prefetch_related`** | **\~5** | **\~75 ms** | **\~87 ms** | **A melhor performance geral.** |

### Cenário 2: Paginação com 100 Itens (`?page_size=100`)

| Estratégia | Nº de Queries (Debug Toolbar) | Tempo Total das Queries (ms) | Tempo de Processamento da API (ms) | Análise Rápida |
| :--- | :---: | :---: | :---: | :--- |
| **Não Otimizado** | **\~202** | **\~250 ms** | **\~510 ms** | **Inviável.** O problema N+1 explode, tornando a API lenta. |
| **`select_related`** | \~2 | \~87 ms | \~135 ms | O JOIN único se torna pesado e lento. |
| **`prefetch_related`** | **\~5** | **\~65 ms** | **\~101 ms** | **Performance escala bem.** Continua rápido e eficiente. |

### 💡 Análise dos Resultados

  * **Não Otimizado (N+1):** Esta abordagem executa 1 query para a lista de transações e depois **N queries adicionais** para buscar os dados relacionados de cada uma das N transações. Como a tabela mostra, o número de queries e o tempo de resposta crescem linearmente com o tamanho da página, tornando a aplicação lenta rapidamente.

  * **Otimizado com `select_related`:** Esta estratégia resolve o problema N+1 ao unir as tabelas em uma **única e grande query SQL (JOIN)**.

  * **Otimizado com `prefetch_related` (A Estratégia Vencedora):** Esta é a solução ideal para o nosso caso. Ela funciona de forma mais inteligente:

    1.  Executa a query principal para as transações.
    2.  Executa **uma ou mais queries separadas** para buscar todos os dados relacionados necessários de uma só vez (usando a cláusula `WHERE id IN (...)`).
    3.  Faz o "join" dos dados em Python.

    Isso resulta em um número pequeno e **constante** de queries muito eficientes, independentemente do tamanho da página, garantindo performance e escalabilidade.