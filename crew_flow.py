from crewai import Agent, Task, Crew

def build_crew(issue_title: str, issue_body: str, repo_tree: str):
    dev = Agent(
        role="Backend Dev",
        goal="Implement the issue with minimal, clear changes.",
        backstory="You change as little as possible and keep the code consistent.",
        verbose=True,
    )

    qa = Agent(
        role="QA Reviewer",
        goal="Validate whether the change solves the issue and did not break obvious behavior.",
        backstory="You are strict about edge cases and ask for a simple test when it makes sense.",
        verbose=True,
    )

    git_agent = Agent(
        role="Git Integrator",
        goal="Generate clear, objective commit and PR messages based on the final changes.",
        backstory="You write PRs with professional engineering standards.",
        verbose=True,
    )

    dev_task = Task(
        description=f"""
Issue:
Title: {issue_title}
Description: {issue_body}

Repo tree (summary):
{repo_tree}

MANDATORY output:
1) A list of files to change/create
2) For each file, the FULL final content (not a diff)
3) A short explanation (1-3 lines) of what changed
""",
        expected_output="Files + full final content + short explanation.",
        agent=dev,
    )

    qa_task = Task(
        description="""
Review the proposed solution.
Checklist:
- Does it match the issue request exactly?
- Do endpoint/contract expectations match?
- Suggest 1 simple test (or a test file) when applicable.
Output:
- PASS or FAIL
- If FAIL: what must change
- If PASS: suggested test (if applicable) with full file content
""",
        expected_output="PASS/FAIL + recommendations + possible full test file content.",
        agent=qa,
        context=[dev_task],
    )

    git_task = Task(
        description="""
Based on the final changes, generate:
- a single JSON object with EXACTLY these keys:
  - files: object map where keys are repository-relative file paths and values are FULL final file contents
  - branch: string (feature/issue-<n>-slug)
  - commit: string (conventional commit message)
  - pr_title: string
  - pr_body: string (include goal, what changed, and how to test)

Rules:
- Return JSON only (no markdown, no code fences, no explanations).
- Ensure "files" includes every file that must be created/updated for this issue.
""",
        expected_output='Pure JSON: {"files": {...}, "branch": "...", "commit": "...", "pr_title": "...", "pr_body": "..."}',
        agent=git_agent,
        context=[dev_task, qa_task],
    )

    return Crew(agents=[dev, qa, git_agent], tasks=[dev_task, qa_task, git_task], verbose=True)
