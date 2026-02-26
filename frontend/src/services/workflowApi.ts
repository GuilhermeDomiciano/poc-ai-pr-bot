import type {
  HealthCheckResponse,
  RunWorkflowExecution,
  RunWorkflowErrorResponse,
  RunWorkflowRequest,
  RunWorkflowResponse,
} from '../types/workflow'

const DEFAULT_API_BASE_URL = 'http://localhost:8000'
const WORKFLOW_RUN_PATH = '/workflow/run'
const WORKFLOW_STREAM_PATH = '/workflow/stream'
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

export function openWorkflowStream(requestId: string): EventSource {
  return new EventSource(`${API_BASE_URL}${WORKFLOW_STREAM_PATH}/${encodeURIComponent(requestId)}`)
}

export async function runWorkflow(
  payload: RunWorkflowRequest,
  requestId?: string,
): Promise<RunWorkflowExecution> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (requestId) {
    headers['X-Request-ID'] = requestId
  }

  const response = await fetch(`${API_BASE_URL}${WORKFLOW_RUN_PATH}`, {
    method: 'POST',
    headers,
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

  return {
    response: (await response.json()) as RunWorkflowResponse,
    requestId: response.headers.get('X-Request-ID') ?? requestId ?? null,
  }
}
