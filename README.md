# IFSP - PTB - PTBDAMS: APIs REST

## Visão Geral do Projeto

Este projeto demonstra a comunicação entre **microsserviços** utilizando **APIs REST** com o framework **FastAPI** (Python). A arquitetura é composta por dois serviços independentes que se comunicam via HTTP, orquestrados pelo **Docker Compose**.

---

##  Microsserviços

### Serviço 1: Autores

Responsável por armazenar e fornecer informações sobre autores literários. É o serviço **dependência** do projeto, ou seja, o `books_service` depende dele para compor a resposta completa.

| Campo    | Descrição                      |
|----------|--------------------------------|
| **Porta**    | `8000`                         |
| **Framework**| FastAPI + Uvicorn              |

#### Endpoint

| Método | Rota                  | Descrição                                         |
|--------|-----------------------|---------------------------------------------------|
| GET    | `/author/{id}`        | Retorna os dados de um autor pelo seu ID.         |

**Query Parameters:**

| Parâmetro | Tipo | Padrão | Descrição                                                        |
|-----------|------|--------|------------------------------------------------------------------|
| `delay`   | int  | `0`    | Simula uma demora artificial (em segundos) antes de responder.   |

**Exemplo de resposta — `GET /author/1`:**
```json
{
  "nome": "Machado de Assis",
  "pais": "Brasil",
  "estilo": "Realismo"
}
```


---

### Serviço 2: Livros

Responsável por fornecer informações sobre livros. Ao receber uma requisição, ele **consulta internamente** o `authors_service` para obter os dados do autor correspondente e devolver uma ficha técnica completa.

| Campo    | Descrição                      |
|----------|--------------------------------|
| **Porta**    | `8001` (externa) / `8000` (interna) |
| **Framework**| FastAPI + Uvicorn + HTTPX      |

#### Endpoint

| Método | Rota            | Descrição                                                         |
|--------|-----------------|-------------------------------------------------------------------|
| GET    | `/book/{id}`    | Retorna os dados do livro + dados do autor (via chamada interna). |

**Query Parameters:**

| Parâmetro | Tipo | Padrão | Descrição                                                                        |
|-----------|------|--------|----------------------------------------------------------------------------------|
| `delay`   | int  | `0`    | Repassado ao `authors_service` para simular lentidão na resposta do outro serviço.|

**Exemplo de resposta — `GET /book/101`:**
```json
{
  "livro": "Dom Casmurro",
  "detalhes_do_autor": {
    "nome": "Machado de Assis",
    "pais": "Brasil",
    "estilo": "Realismo"
  },
  "status": "Ficha técnica completa com sucesso!"
}
```

## Cenários de Simulação

### Cenário 1 — Falha na comunicação (serviço de autores indisponível)

**Situação:** O `authors_service` está fora do ar (container parado ou com erro).

**O que acontece:**

1. O cliente faz uma requisição para `GET /book/101`.
2. O `books_service` encontra o livro na sua base local.
3. Ao tentar chamar `http://authors_service:8000/author/1`, a conexão **falha** — o serviço não está acessível.
4. O `httpx` lança uma exceção do tipo `httpx.RequestError`.
5. O `books_service` captura essa exceção e retorna ao cliente:

```json
{
  "detail": "Não foi possível conectar ao serviço de autores (Falha de Comunicação)."
}
```
**Código HTTP:** `503 Service Unavailable`

**Conclusão:** O serviço de livros não consegue compor a resposta completa e informa ao cliente que a dependência está indisponível, sem travar ou ficar esperando indefinidamente.

---

### Cenário 2 — Timeout demorado no serviço de autores

**Situação:** O `authors_service` está no ar, porém respondendo com muita lentidão (simulado via parâmetro `delay`).

**Exemplo de chamada:** `GET /book/101?delay=5` (simula 5 segundos de atraso)

**O que acontece:**

1. O cliente faz uma requisição para `GET /book/101?delay=5`.
2. O `books_service` encontra o livro e faz a chamada interna para `http://authors_service:8000/author/1?delay=5`.
3. O `authors_service` recebe a requisição e executa `await asyncio.sleep(5)` — dormindo por 5 segundos antes de responder.
4. Porém, o `books_service` configurou um **timeout de 2 segundos** (`timeout=2.0`) no cliente HTTP.
5. Após 2 segundos sem resposta, o `httpx` lança uma exceção do tipo `httpx.ReadTimeout`.
6. O `books_service` captura essa exceção e retorna ao cliente:

```json
{
  "detail": "O serviço de autores demorou demais para responder (Timeout)."
}
```
**Código HTTP:** `504 Gateway Timeout`

**Conclusão:** Mesmo que o serviço de autores eventualmente respondesse (após 5 segundos), o serviço de livros **não ficou preso esperando** — ele se protegeu com um timeout de 2 segundos e informou o problema ao cliente de forma adequada.

---

## Problemas que podem ocorrer nesse tipo de implementação

1. **Ponto único de falha (Single Point of Failure):** Se o `authors_service` cair, o `books_service` perde toda a capacidade de retornar fichas completas — não existe redundância ou réplica do serviço.

2. **Ausência de Circuit Breaker:** Não há mecanismo para "abrir o circuito" quando o serviço de autores está repetidamente falhando. Cada nova requisição ao `books_service` tentará chamar o `authors_service` novamente, gerando carga desnecessária e aumentando a latência para o cliente.

3. **Sem mecanismo de Retry com backoff:** Falhas de rede podem ser transitórias. Uma única tentativa que falha já retorna erro ao usuário, quando uma segunda tentativa poderia ter sucesso.

4. **Efeito cascata (Cascading Failure):** Se o `authors_service` ficar lento (mas não totalmente fora do ar), as requisições do `books_service` podem se acumular, consumindo threads/conexões e eventualmente derrubando o próprio `books_service` também.

5. **Sem Health Checks:** O `docker-compose` usa `depends_on`, mas isso só garante que o container **iniciou** — não que a aplicação dentro dele está **pronta** para receber requisições. O `books_service` pode tentar chamar o `authors_service` antes dele estar de fato respondendo.

6. **Sem cache:** Dados de autores raramente mudam, mas toda requisição ao `books_service` gera uma chamada de rede ao `authors_service`. Um cache local evitaria chamadas repetidas e reduziria o impacto de falhas.

7. **Acoplamento temporal:** Os dois serviços precisam estar no ar **ao mesmo tempo** para funcionar. Em arquiteturas mais resilientes, mensageria assíncrona (ex: RabbitMQ, Kafka) poderia desacoplar essa dependência.

8. **Sem observabilidade:** Não há logs estruturados, métricas ou tracing distribuído. Em produção, seria difícil diagnosticar a causa raiz de falhas intermitentes entre os serviços.

---

## * Relato sobre a execução do projeto:

Não foi possível realizar a execução e os testes práticos deste (com prints de tela). A máquina utilizada não possui espaço de armazenamento suficiente para a instalação do **Docker Desktop**, que é necessário para subir os containers dos microsserviços via `docker-compose up`.
Sem o Docker, não é possível criar a rede interna entre os serviços (`authors_service` e `books_service`), o que impede a demonstração prática dos cenários de comunicação, falha e timeout descritos acima. Portanto, esta atividade apresenta apenas a **implementação do código-fonte e a análise teórica** dos cenários, sem os prints da execução real.
