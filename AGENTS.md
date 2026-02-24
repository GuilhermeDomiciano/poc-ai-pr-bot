# Repository Guidelines

## Project Structure & Module Organization
This repository is a Python modular-monolith POC for automating GitHub issue-to-PR flows.
- `main.py`: CLI-style entrypoint that wires dependencies and runs the workflow.
- `application/`: use-case orchestration (`run_issue_flow.py`).
- `domain/`: core models and payload parsing/validation.
- `infrastructure/`: external adapters (`ai/`, `github/`, `repo/`, `http/`).
- `Dockerfile`, `docker-compose.yml`: containerized execution.
- `.env.example`: required environment variables template.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate`: create and activate virtualenv.
- `pip install -r requirements.txt`: install dependencies.
- `cp .env.example .env`: bootstrap local config.
- `python main.py`: run the issue-to-PR workflow.
- `uvicorn infrastructure.http.api:app --reload`: run the HTTP API locally.
- `docker compose up --build`: build and run in containers.

## Coding Style & Naming Conventions
- Follow PEP 8, 4-space indentation, and type hints (current codebase uses typed signatures).
- Use `snake_case` for functions/variables/modules, `PascalCase` for classes, and explicit dependency wiring objects (for example `IssueFlowDependencies`).
- Keep `main.py` thin; place business logic in `application/` and `domain/`, integrations in `infrastructure/`.
- Prefer small, composable functions and clear boundary interfaces.

## Testing Guidelines
There is currently no committed automated test suite.
- When adding tests, prefer `pytest` with files named `test_*.py`.
- Mirror source layout under `tests/` (example: `tests/application/test_run_issue_flow.py`).
- Cover parsing edge cases, gateway failures, and dry-run behavior.

## Commit & Pull Request Guidelines
Git history follows Conventional Commits, often with scope:
- Examples: `feat(http): ...`, `refactor(issue-flow): ...`.
- Recommended format: `<type>(<scope>): <imperative summary>`.

For PRs, include:
- Clear problem/solution description and linked issue.
- Notes on env/config changes (`.env` keys, base branch behavior).
- API impact examples when changing `infrastructure/http/` endpoints.
