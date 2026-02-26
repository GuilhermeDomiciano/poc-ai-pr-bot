# POC AI PR Bot

A proof-of-concept bot that reads a GitHub Issue, runs a multi-agent CrewAI workflow, applies generated code changes, and opens a Pull Request.

## What It Does

1. Reads issue data from GitHub (`ISSUE_NUMBER` in CLI mode, payload in HTTP mode).
2. Clones the target repository into `/work/repo`.
3. Runs a 5-agent flow:
   - `Backend Dev`
   - `Frontend Dev`
   - `Integration Engineer`
   - `QA Reviewer`
   - `Git Integrator`
4. Expects final pure JSON payload:
   - `files` (path -> full file content)
   - `branch`
   - `commit`
   - `pr_title`
   - `pr_body`
5. Writes files, creates branch, commits, pushes, and tries to create a PR.

## Multi-Agent Strategy

### Agent responsibilities

- `Backend Dev`: edits only `backend/` and focuses on API/service changes.
- `Frontend Dev`: edits only `frontend/` and focuses on UI/client behavior.
- `Integration Engineer`: can edit both `backend/` and `frontend/` to resolve contract mismatches.
- `QA Reviewer`: validates E2E contract, scope guardrails, and output quality.
- `Git Integrator`: consolidates everything into one strict JSON output.

### Integration contract defaults

- Frontend base URL env: `VITE_API_BASE_URL`
- Fallback base URL: `http://localhost:8000`
- Endpoint path: `/workflow/run`
- Request shape consumed by frontend:
  - `{owner, repo, issue_number, base_branch?, dry_run?}`
- Success response:
  - `{status, message, branch?, commit?, pr_title?, pr_url?}`
- Error response:
  - `{detail}`

### Guardrails

- Non-integration agents cannot edit outside their folder scope.
- Final `files` map only accepts paths under `backend/` or `frontend/`.
- Parser rejects absolute paths and traversal patterns (`..`).

## Architecture (Current)

- `main.py`: CLI entrypoint only (load env, wire dependencies, call use case).
- `application/run_issue_flow.py`: use-case orchestration.
- `domain/models.py`: domain model (`ChangeSet`).
- `domain/payload_parser.py`: JSON extraction + integration contract validation.
- `infrastructure/ai/`: Crew flow and runner.
- `infrastructure/http/`: API adapter (`/health`, `/workflow/run`).
- `infrastructure/github/`: GitHub API client and gateways.
- `infrastructure/repo/`: git/repo operations and file writer.
- `infrastructure/observability/`: structured logging + change-scope observer.

## Requirements

- Python 3.10-3.13 (CrewAI pinned version is not compatible with Python 3.14).
- Git installed.
- GitHub token with repository write + PR permissions.
- OpenAI API key.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

```env
# Required for CLI and HTTP
OPENAI_API_KEY=...
GITHUB_TOKEN=...

# Required for CLI (`python main.py`)
GH_OWNER=your-org-or-user
GH_REPO=your-repo
ISSUE_NUMBER=1

# Optional
OPENAI_MODEL=gpt-4o-mini
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
GH_BASE_BRANCH=main
GIT_AUTHOR_NAME=AI Bot
GIT_AUTHOR_EMAIL=ai-bot@example.com
```

`OPENAI_MODEL` define o modelo usado pelos 5 agentes CrewAI. O padrão é `gpt-4o-mini` para reduzir custo de tokens.
`CORS_ALLOW_ORIGINS` define as origens permitidas no HTTP mode (lista separada por vírgula).

For HTTP mode (`POST /workflow/run`), `owner`, `repo`, and `issue_number` come from request payload; `OPENAI_API_KEY` and `GITHUB_TOKEN` remain required in env.

## Run

```bash
python main.py
```

or:

```bash
uvicorn infrastructure.http.api:app --reload
```

## Testing

Run test suite:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Current tests cover:

- multi-agent flow structure (5 agents + task ordering/context)
- parser guardrails for integration payload
- light integration scenarios (`backend_only`, `frontend_only`, `fullstack`) in `run_issue_flow`

## Example Issue Types

- Backend-only:
  - "Adicionar endpoint de health detalhado com metadata"
- Frontend-only:
  - "Criar tela de status de execucao com loading e erro amigavel"
- Fullstack:
  - "Adicionar filtro por repositorio no backend e UI com consumo tipado"

## Troubleshooting

- Error: `Integration contract violation: no valid JSON object found...`
  - Cause: crew returned markdown/text instead of pure JSON.
  - Fix: enforce "JSON only" in prompts and Git Integrator output.

- Error: `Integration contract violation: file path '...' must start with 'backend/' or 'frontend/'`
  - Cause: output paths outside allowed monorepo roots.
  - Fix: adjust agent outputs to scoped paths only.

- Error: `Integration contract violation: file path '...' contains invalid path traversal segments`
  - Cause: unsafe path (`..`).
  - Fix: ensure repository-relative safe paths.

- Frontend cannot call API in local dev:
  - Check `VITE_API_BASE_URL`.
  - Confirm backend endpoint path `/workflow/run`.
  - Confirm CORS policy includes frontend origin.

## Notes

- Bot writes full file contents from AI output, not diffs.
- Use a test repository before production repositories.
- Current `docker-compose.yml` mounts `./work:/work`; host `work/` must be writable.
