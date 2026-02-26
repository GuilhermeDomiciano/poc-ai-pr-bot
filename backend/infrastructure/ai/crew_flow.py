from crewai import Agent, Crew, Task


def build_crew(issue_title: str, issue_body: str, repo_tree: str) -> Crew:
    backend_dev = Agent(
        role="Backend Dev",
        goal="Implement backend changes with minimal, safe edits and stable API contracts.",
        backstory="You are strict about service boundaries and API compatibility.",
        verbose=True,
    )

    frontend_dev = Agent(
        role="Frontend Dev",
        goal="Implement UI and client integration with typed, maintainable code.",
        backstory="You are strict about user feedback states, request handling, and DX.",
        verbose=True,
    )

    integration_engineer = Agent(
        role="Integration Engineer",
        goal="Guarantee frontend/backend contract alignment and integration safety.",
        backstory="You focus on API contract, error handling, CORS, and env wiring.",
        verbose=True,
    )

    qa_reviewer = Agent(
        role="QA Reviewer",
        goal="Validate the fullstack solution and reject unsafe or incomplete outputs.",
        backstory="You apply strict E2E checks and enforce delivery guardrails.",
        verbose=True,
    )

    git_integrator = Agent(
        role="Git Integrator",
        goal="Produce a single valid JSON output for repository changes and PR metadata.",
        backstory="You enforce strict output formatting and complete file coverage.",
        verbose=True,
    )

    backend_task = Task(
        description=f"""
Issue:
Title: {issue_title}
Description: {issue_body}

Repo tree (summary):
{repo_tree}

Role responsibilities:
- Implement backend logic only.
- Keep changes minimal and coherent with existing architecture.

Scope guardrail:
- You may edit ONLY files under `backend/`.
- If frontend changes are required, describe them but do not edit frontend files.

Expected output:
1) Backend files to create/update with FULL final content
2) Short rationale (1-3 lines)
3) Integration notes for frontend consumer when relevant
""",
        expected_output="Backend-only implementation proposal with full file contents and integration notes.",
        agent=backend_dev,
    )

    frontend_task = Task(
        description="""
Implement frontend updates required by the issue and backend proposal.

Role responsibilities:
- Implement UI/client behavior in frontend.
- Ensure request/response typing and user feedback states.

Scope guardrail:
- You may edit ONLY files under `frontend/`.
- Do not edit backend files directly.

Mandatory integration defaults:
- Frontend API base URL env: `VITE_API_BASE_URL`
- Fallback base URL: `http://localhost:8000`
- Endpoint path consumed by frontend: `/workflow/run`

Error handling requirements:
- Handle loading, success, and failure states.
- Show user-friendly message on API failure.
- Keep a technical fallback message when no detail is available.

Contract expectations for request/response:
- Request: `{owner, repo, issue_number, base_branch?, dry_run?}`
- Success response: `{status, message, branch?, commit?, pr_title?, pr_url?}`
- Error response (FastAPI): `{detail: string}`
""",
        expected_output="Frontend-only implementation proposal with full file contents and explicit API handling.",
        agent=frontend_dev,
        context=[backend_task],
    )

    integration_task = Task(
        description="""
Validate and reconcile backend and frontend outputs as a single integrated solution.

Role responsibilities:
- You may edit files in BOTH `backend/` and `frontend/` when necessary.
- Resolve contract mismatches between API and frontend client.

Mandatory integration checks:
- Base URL + endpoint path consistency (`VITE_API_BASE_URL` + `/workflow/run`)
- Request payload fields and naming consistency
- Response parsing and optional fields handling
- Error handling parity (`detail` fallback)
- CORS and local-dev configuration compatibility
- Environment variable names and usage consistency
- JSON field naming and type consistency end-to-end

Output constraints:
- List required edits with FULL final contents for each file.
- Explicitly call out any contract changes or compatibility notes.
""",
        expected_output="Integrated fullstack proposal with contract-safe backend/frontend changes.",
        agent=integration_engineer,
        context=[backend_task, frontend_task],
    )

    qa_task = Task(
        description="""
Review the integrated solution end-to-end and enforce guardrails.

Reject (FAIL) if any condition happens:
- Any non-integration agent edits outside its allowed folder.
- Backend/frontend contract mismatch in fields, path, or types.
- Missing default handling for API errors on frontend.
- Missing CORS/env alignment for local integration.
- Final delivery cannot be represented as pure JSON files map.

PASS criteria:
- Contract is consistent and implementable.
- Scope guardrails respected.
- Minimal regression risk.

Output:
- PASS or FAIL
- If FAIL: required fixes
- If PASS: concise verification checklist
""",
        expected_output="PASS/FAIL with concrete corrective actions or validation checklist.",
        agent=qa_reviewer,
        context=[backend_task, frontend_task, integration_task],
    )

    git_task = Task(
        description="""
Generate the final repository output as a single JSON object.

Required JSON keys:
- files: object map {repository-relative path -> FULL final file content}
- branch: string (`feature/issue-<n>-slug`)
- commit: string (Conventional Commit message)
- pr_title: string
- pr_body: string (goal, what changed, how to test)

Hard rules:
- Return JSON only.
- No markdown, no code fences, no explanations.
- Include every file that must be created/updated.
- All file paths in `files` must start with `backend/` or `frontend/`.
""",
        expected_output='Pure JSON: {"files": {...}, "branch": "...", "commit": "...", "pr_title": "...", "pr_body": "..."}',
        agent=git_integrator,
        context=[backend_task, frontend_task, integration_task, qa_task],
    )

    return Crew(
        agents=[
            backend_dev,
            frontend_dev,
            integration_engineer,
            qa_reviewer,
            git_integrator,
        ],
        tasks=[
            backend_task,
            frontend_task,
            integration_task,
            qa_task,
            git_task,
        ],
        verbose=True,
    )
