from application.issue_flow.contracts import (
    IssueFlowConfig,
    IssueFlowDependencies,
    IssueFlowResult,
)
from application.issue_flow.steps import (
    build_dry_run_result,
    build_pr_or_branch_result,
    generate_ai_output,
    load_issue_context,
    parse_change_set,
    prepare_repository,
    publish_repository_changes,
)


def run_issue_flow(
    config: IssueFlowConfig,
    dependencies: IssueFlowDependencies,
    *,
    raise_on_error: bool = True,
) -> IssueFlowResult:
    try:
        dependencies.observe_step("load_issue", "start")
        issue_title, issue_body = load_issue_context(config, dependencies)
        dependencies.observe_step("load_issue", "success")

        dependencies.observe_step("prepare_repo", "start")
        prepare_repository(config, dependencies)
        dependencies.observe_step("prepare_repo", "success")

        dependencies.observe_step("generate_changes", "start")
        ai_output_text = generate_ai_output(issue_title, issue_body, config, dependencies)
        dependencies.observe_step("generate_changes", "success")

        dependencies.observe_step("validate_payload", "start")
        change_set = parse_change_set(ai_output_text, dependencies)
        dependencies.observe_step(
            "validate_payload",
            "success",
            detail=f"files_count={len(change_set.files)}",
        )

        if config.dry_run:
            dependencies.observe_step(
                "publish_branch",
                "success",
                detail="skipped (dry_run=true)",
            )
            dependencies.observe_step("finalize", "success", detail="dry_run completed")
            return build_dry_run_result(change_set)

        dependencies.observe_step("publish_branch", "start")
        publish_repository_changes(config, dependencies, change_set)
        dependencies.observe_step("publish_branch", "success", detail=change_set.branch)

        dependencies.observe_step("finalize", "start")
        result = build_pr_or_branch_result(config, dependencies, change_set)
        dependencies.observe_step("finalize", "success", detail=result.message)
        return result
    except Exception as error:
        dependencies.observe_step("finalize", "error", detail=str(error))
        if raise_on_error:
            raise
        return IssueFlowResult(
            status="error",
            message="Issue flow execution failed",
            error=str(error),
        )
