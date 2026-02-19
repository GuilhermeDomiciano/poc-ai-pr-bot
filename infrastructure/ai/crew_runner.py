from infrastructure.ai.crew_flow import build_crew


def run_crew(issue_title: str, issue_body: str, repository_tree_summary: str) -> str:
    issue_crew = build_crew(issue_title, issue_body, repository_tree_summary)
    crew_result = issue_crew.kickoff()
    return str(crew_result)
