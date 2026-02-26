import type {
  HealthCheckResponse,
  RunWorkflowErrorResponse,
  RunWorkflowRequest,
  RunWorkflowResponse,
} from '../types/workflow'

const DEFAULT_API_BASE_URL = 'http://localhost:8000'
const WORKFLOW_RUN_PATH = '/workflow/run'
const HEALTH_PATH = '/health'

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL).replace(/\/+$/, '')

function isRunWorkflowErrorResponse(payload: unknown): payload is RunWorkflowErrorResponse {
  if (typeof payload !== 'object' || payload === null) {
    return false
  }
  const maybeDetail = (payload as { detail?: unknown }).detail
  return typeof maybeDetail === 'string'
}

export function getApiBaseUrl(): string {
  return API_BASE_URL
}

export async function checkHealth(): Promise<HealthCheckResponse> {
  const response = await fetch(`${API_BASE_URL}${HEALTH_PATH}`)
  if (!response.ok) {
    throw new Error('Health check failed')
  }
  return (await response.json()) as HealthCheckResponse
}

export async function runWorkflow(payload: RunWorkflowRequest): Promise<RunWorkflowResponse> {
  const response = await fetch(`${API_BASE_URL}${WORKFLOW_RUN_PATH}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    let errorDetail = 'Falha ao executar workflow. A API nao retornou detalhes.'
    try {
      const errorPayload = (await response.json()) as unknown
      if (isRunWorkflowErrorResponse(errorPayload)) {
        errorDetail = errorPayload.detail
      }
    } catch (error) {
      void error
    }
    throw new Error(errorDetail)
  }

  return (await response.json()) as RunWorkflowResponse
}
