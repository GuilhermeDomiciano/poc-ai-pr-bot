export type RunWorkflowRequest = {
  owner: string
  repo: string
  issue_number: number
  base_branch?: string
  dry_run?: boolean
}

export type RunWorkflowResponse = {
  status: string
  message: string
  branch?: string | null
  commit?: string | null
  pr_title?: string | null
  pr_url?: string | null
}

export type RunWorkflowErrorResponse = {
  detail: string
}

export type HealthCheckResponse = {
  status: string
}
