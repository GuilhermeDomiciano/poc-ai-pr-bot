# Guia Backend: De Dentro para Fora

Este roteiro te mostra exatamente a ordem para entender o backend inteiro, do núcleo de regras até as entradas HTTP/CLI.

## 1) Núcleo do domínio (comece aqui)

1. `domain/models.py`  
   O que existe de dado canônico (`ChangeSet`).
2. `domain/payload/` (leia nessa ordem):
   - `errors.py`: erro de contrato e prefixo padrão.
   - `extractor.py`: extrai o primeiro JSON válido do texto da IA.
   - `path_policy.py`: política de caminhos permitidos (`backend/` e `frontend/`).
   - `validators.py`: valida chaves obrigatórias, strings e mapa `files`.
   - `parser.py`: orquestra tudo e retorna `ChangeSet`.
3. `domain/payload_parser.py`  
   Wrapper de compatibilidade (reexport); código novo deve usar `domain.payload`.

Objetivo: entender **qual formato é aceito** e **o que quebra o fluxo**.

## 2) Orquestração da regra de negócio

1. `application/issue_flow/contracts.py`  
   Contratos do caso de uso: `IssueFlowConfig`, `IssueFlowDependencies`, `IssueFlowResult`.
2. `application/issue_flow/steps.py`  
   Etapas isoladas do pipeline (carregar issue, preparar repo, gerar output, publicar etc.).
3. `application/issue_flow/use_case.py`  
   Orquestração final: `run_issue_flow(...)` com a sequência:
   `load_issue -> prepa    re_repo -> run_crew -> validate_payload -> publish_branch -> finalize`.
4. `application/run_issue_flow.py`  
   Wrapper de compatibilidade (reexport); código novo deve usar `application.issue_flow`.

Objetivo: entender **quem chama quem** e em que ordem.

## 3) Adaptadores de infraestrutura

### Git e filesystem
- `infrastructure/repo/operations.py`: clone, config git, push, checagem de branch remota.
- `infrastructure/repo/file_writer.py`: grava arquivos no repositório clonado.

### GitHub API
- `infrastructure/github/github_client.py`: buscar issue e criar PR.
- `infrastructure/github/issue_gateway.py` e `pr_gateway.py`: wrappers simples do client.

### IA multiagente
- `infrastructure/ai/crew_flow.py`: definição dos agentes/tarefas.
- `infrastructure/ai/crew_runner.py`: dispara `build_crew(...).kickoff()`.

Objetivo: entender **como o mundo externo é acessado**.

## 4) Observabilidade e rastreio

- `infrastructure/observability/context.py`: `request_id` por contexto.
- `infrastructure/observability/logging_utils.py`: logging estruturado + redaction.
- `infrastructure/observability/workflow_observer.py`: eventos por etapa/contrato.
- `infrastructure/observability/event_stream.py`: stream em memória para SSE.

Objetivo: entender **como diagnosticar execução**.

## 5) Entradas do sistema (camada mais externa)

### HTTP
- `infrastructure/http/schemas.py`: contrato da API.
- `infrastructure/http/mappers.py`: mapeamentos request/config/response.
- `infrastructure/http/workflow_factory.py`: injeta dependências do fluxo.
- `infrastructure/http/workflow_service.py`: executa fluxo e trata erro.
- `infrastructure/http/errors.py`: converte para erro HTTP.
- `infrastructure/http/api.py`: FastAPI, CORS, middleware, `/workflow/run`, `/workflow/stream/{request_id}`.

### CLI
- `main.py`: carrega `.env`, monta config/deps e chama `run_issue_flow`.

Objetivo: entender **como o backend é acionado**.

## 6) Checklist final (se você dominar isso, domina o backend)

- [ ] Sei explicar o contrato JSON que a IA precisa retornar.
- [ ] Sei descrever as 6 etapas do `run_issue_flow`.
- [ ] Sei onde `base_branch` é usada (criação de PR/base remota).
- [ ] Sei rastrear uma execução usando `X-Request-ID` e SSE.
- [ ] Sei apontar exatamente onde ocorre falha de contrato, git, GitHub ou IA.
