import { type FormEvent, useMemo, useState } from 'react'
import './App.css'
import { checkHealth, getApiBaseUrl, openWorkflowStream, runWorkflow } from './services/workflowApi'
import type { RunWorkflowResponse, WorkflowRuntimeEvent } from './types/workflow'

const FLOW_STEPS = [
  {
    title: 'Carregar issue no GitHub',
    description: 'Busca título e descrição da issue informada para iniciar o contexto.',
  },
  {
    title: 'Preparar repositório e Git',
    description: 'Clona o repositório de destino e configura identidade de commit.',
  },
  {
    title: 'Executar crew multiagente',
    description: 'Backend, Frontend, Integração, QA e Git Integrator produzem a solução.',
  },
  {
    title: 'Validar payload e contrato',
    description: 'Verifica JSON final, escopo de arquivos e guardrails de segurança.',
  },
  {
    title: 'Aplicar mudanças e publicar branch',
    description: 'Escreve arquivos finais e envia commit para branch de feature.',
  },
  {
    title: 'Criar PR (ou dry-run)',
    description: 'Abre o Pull Request automaticamente ou finaliza sem push no modo dry-run.',
  },
]

const AGENT_CARDS = [
  {
    id: 'backend_dev',
    name: 'Backend Dev',
    responsibility: 'Implementa lógica de backend com alterações mínimas e contratos estáveis.',
    scopeLimit: 'Pode editar apenas arquivos em backend/.',
  },
  {
    id: 'frontend_dev',
    name: 'Frontend Dev',
    responsibility: 'Implementa UI e integração cliente/API com tipagem e estados de feedback.',
    scopeLimit: 'Pode editar apenas arquivos em frontend/.',
  },
  {
    id: 'integration_engineer',
    name: 'Integration Engineer',
    responsibility: 'Resolve incompatibilidades entre frontend e backend e garante contrato fim a fim.',
    scopeLimit: 'Pode editar backend/ e frontend/ quando necessário para integração.',
  },
  {
    id: 'qa_reviewer',
    name: 'QA Reviewer',
    responsibility: 'Valida qualidade E2E, segurança e consistência do contrato final.',
    scopeLimit: 'Não implementa feature nova; aprova ou bloqueia com critérios objetivos.',
  },
  {
    id: 'git_integrator',
    name: 'Git Integrator',
    responsibility: 'Consolida saída final em JSON com arquivos, branch, commit e dados de PR.',
    scopeLimit: 'Entrega estritamente JSON válido e caminhos sob backend/ ou frontend/.',
  },
]

const STEP_INDEX_BY_KEY: Record<string, number> = {
  load_issue: 0,
  prepare_repo: 1,
  run_crew: 2,
  validate_payload: 3,
  publish_branch: 4,
  finalize: 5,
}

const STEP_LABEL_BY_KEY: Record<string, string> = {
  load_issue: 'Carregar issue',
  prepare_repo: 'Preparar repositório e git',
  run_crew: 'Executar crew multiagente',
  validate_payload: 'Validar payload/contrato',
  publish_branch: 'Aplicar arquivos e publicar branch',
  finalize: 'Criar PR/finalização',
}

type FormState = {
  owner: string
  repo: string
  issueNumber: string
  baseBranch: string
  dryRun: boolean
}

type FormErrors = Partial<Record<keyof Omit<FormState, 'dryRun'>, string>>
type TimelinePhase = 'idle' | 'running' | 'success' | 'error'
type AgentExecutionSummary = {
  lastAction: string
  delivered: string
}

const INITIAL_FORM: FormState = {
  owner: '',
  repo: '',
  issueNumber: '',
  baseBranch: 'main',
  dryRun: false,
}

const WORKFLOW_ERROR_FALLBACK =
  'Nao foi possivel executar o workflow. Verifique a API e tente novamente.'

function getErrorDetailMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    const message = error.message.trim()
    const lowerMessage = message.toLowerCase()

    if (lowerMessage.includes('networkerror') || lowerMessage.includes('failed to fetch')) {
      return 'Falha de rede ao chamar a API. Verifique backend ativo, URL e CORS.'
    }
    return message
  }
  return WORKFLOW_ERROR_FALLBACK
}

function buildRequestId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `req-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function parseRuntimeEvent(data: string): WorkflowRuntimeEvent | null {
  let parsed: unknown
  try {
    parsed = JSON.parse(data)
  } catch {
    return null
  }

  if (typeof parsed !== 'object' || parsed === null) {
    return null
  }

  const payload = parsed as Record<string, unknown>
  if (payload.type === 'ping') {
    return null
  }

  if (
    typeof payload.timestamp !== 'string' ||
    typeof payload.level !== 'string' ||
    typeof payload.event !== 'string' ||
    typeof payload.request_id !== 'string' ||
    typeof payload.message !== 'string'
  ) {
    return null
  }

  const fields = payload.fields
  const normalizedFields: Record<string, string> = {}
  if (typeof fields === 'object' && fields !== null) {
    for (const [key, value] of Object.entries(fields)) {
      if (typeof value === 'string') {
        normalizedFields[key] = value
      }
    }
  }

  return {
    timestamp: payload.timestamp,
    level: payload.level,
    event: payload.event,
    request_id: payload.request_id,
    fields: normalizedFields,
    message: payload.message,
  }
}

function describeRuntimeEvent(runtimeEvent: WorkflowRuntimeEvent): string {
  const stepKey = runtimeEvent.fields.step
  const stepStatus = runtimeEvent.fields.status
  const stepDetail = runtimeEvent.fields.detail
  if (stepKey && stepStatus) {
    const stepLabel = STEP_LABEL_BY_KEY[stepKey] ?? stepKey
    return `${stepLabel} • ${stepStatus}${stepDetail ? ` • ${stepDetail}` : ''}`
  }
  return runtimeEvent.message
}

function parseCount(value: string | undefined): number {
  if (!value) {
    return 0
  }
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) ? parsed : 0
}

function App() {
  const [form, setForm] = useState<FormState>(INITIAL_FORM)
  const [formErrors, setFormErrors] = useState<FormErrors>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isCheckingHealth, setIsCheckingHealth] = useState(false)
  const [healthMessage, setHealthMessage] = useState<string | null>(null)
  const [requestError, setRequestError] = useState<string | null>(null)
  const [workflowResult, setWorkflowResult] = useState<RunWorkflowResponse | null>(null)
  const [requestId, setRequestId] = useState<string | null>(null)
  const [liveLogs, setLiveLogs] = useState<WorkflowRuntimeEvent[]>([])
  const [timelinePhase, setTimelinePhase] = useState<TimelinePhase>('idle')
  const [timelineStepIndex, setTimelineStepIndex] = useState(-1)

  const statusPillText = useMemo(() => {
    if (isSubmitting) {
      return 'Executando...'
    }
    if (requestError) {
      return 'Erro'
    }
    if (workflowResult?.status) {
      return workflowResult.status
    }
    return 'Aguardando execução'
  }, [isSubmitting, requestError, workflowResult])

  const statusPillClass = useMemo(() => {
    if (isSubmitting) {
      return 'status-pill status-pill--running'
    }
    if (requestError) {
      return 'status-pill status-pill--error'
    }
    if (workflowResult?.status === 'dry_run') {
      return 'status-pill status-pill--dryrun'
    }
    if (workflowResult?.status === 'success') {
      return 'status-pill status-pill--success'
    }
    return 'status-pill'
  }, [isSubmitting, requestError, workflowResult])

  const resultTone = useMemo(() => {
    if (requestError) {
      return 'error'
    }
    if (workflowResult?.status === 'dry_run') {
      return 'dryrun'
    }
    if (workflowResult?.status === 'success') {
      return 'success'
    }
    if (isSubmitting) {
      return 'running'
    }
    return 'idle'
  }, [isSubmitting, requestError, workflowResult])

  const resultFields = useMemo(() => {
    if (!workflowResult) {
      return []
    }

    return [
      { label: 'Branch', value: workflowResult.branch, isLink: false },
      { label: 'Commit', value: workflowResult.commit, isLink: false },
      { label: 'PR Title', value: workflowResult.pr_title, isLink: false },
      { label: 'PR URL', value: workflowResult.pr_url, isLink: true },
    ].filter((field) => Boolean(field.value))
  }, [workflowResult])

  const agentExecution = useMemo(() => {
    const finished = !isSubmitting && (Boolean(workflowResult) || Boolean(requestError))

    const latestChangeSetEvent = [...liveLogs]
      .reverse()
      .find((runtimeEvent) => runtimeEvent.event === 'workflow.change_set.generated')

    const backendFilesCount = parseCount(latestChangeSetEvent?.fields.backend_files_count)
    const frontendFilesCount = parseCount(latestChangeSetEvent?.fields.frontend_files_count)
    const totalFilesCount = parseCount(latestChangeSetEvent?.fields.files_count)
    const changeScope = latestChangeSetEvent?.fields.change_scope ?? 'unknown'
    const hasContractViolation = liveLogs.some(
      (runtimeEvent) => runtimeEvent.event === 'workflow.integration_contract.failed',
    )

    const fallbackSummary: AgentExecutionSummary = {
      lastAction: 'Aguardando execução.',
      delivered: '-',
    }

    if (!finished) {
      return {
        backend_dev: fallbackSummary,
        frontend_dev: fallbackSummary,
        integration_engineer: fallbackSummary,
        qa_reviewer: fallbackSummary,
        git_integrator: fallbackSummary,
      } satisfies Record<string, AgentExecutionSummary>
    }

    const backendSummary: AgentExecutionSummary = {
      lastAction: 'Implementou mudanças de backend dentro do escopo permitido.',
      delivered:
        backendFilesCount > 0
          ? `${backendFilesCount} arquivo(s) em backend/.`
          : 'Nenhum arquivo backend alterado nesta execução.',
    }

    const frontendSummary: AgentExecutionSummary = {
      lastAction: 'Implementou ajustes de frontend e integração de cliente.',
      delivered:
        frontendFilesCount > 0
          ? `${frontendFilesCount} arquivo(s) em frontend/.`
          : 'Nenhum arquivo frontend alterado nesta execução.',
    }

    const integrationSummary: AgentExecutionSummary = {
      lastAction: 'Alinhou contrato entre backend e frontend.',
      delivered: `Contrato validado para escopo ${changeScope}; payload final com ${totalFilesCount} arquivo(s).`,
    }

    const qaSummary: AgentExecutionSummary = requestError || hasContractViolation
      ? {
          lastAction: 'Executou revisão de guardrails e contrato fim a fim.',
          delivered: `FAIL: ${requestError ?? 'violação do contrato de integração.'}`,
        }
      : {
          lastAction: 'Executou revisão de guardrails e contrato fim a fim.',
          delivered: 'PASS: fluxo validado sem erro de contrato.',
        }

    const gitSummary: AgentExecutionSummary = requestError
      ? {
          lastAction: 'Tentou consolidar saída final para branch/commit/PR.',
          delivered: `Sem entrega final por erro: ${requestError}`,
        }
      : workflowResult?.status === 'dry_run'
        ? {
            lastAction: 'Consolidou resultado final para dry-run.',
            delivered: `Branch planejada ${workflowResult.branch ?? '-'} e commit "${workflowResult.commit ?? '-'}", sem push/PR real.`,
          }
        : {
            lastAction: 'Consolidou saída final para Git e PR.',
            delivered: `Branch ${workflowResult?.branch ?? '-'}${workflowResult?.pr_url ? `, PR ${workflowResult.pr_url}` : ', PR não criado.'}`,
          }

    return {
      backend_dev: backendSummary,
      frontend_dev: frontendSummary,
      integration_engineer: integrationSummary,
      qa_reviewer: qaSummary,
      git_integrator: gitSummary,
    } satisfies Record<string, AgentExecutionSummary>
  }, [isSubmitting, liveLogs, requestError, workflowResult])

  function validateForm(state: FormState): FormErrors {
    const errors: FormErrors = {}
    if (!state.owner.trim()) {
      errors.owner = 'Owner is required'
    }
    if (!state.repo.trim()) {
      errors.repo = 'Repository is required'
    }
    if (!state.baseBranch.trim()) {
      errors.baseBranch = 'Base branch is required'
    }

    const parsedIssueNumber = Number(state.issueNumber)
    const hasValidIssueNumber = Number.isInteger(parsedIssueNumber) && parsedIssueNumber > 0
    if (!hasValidIssueNumber) {
      errors.issueNumber = 'Issue number must be an integer greater than 0'
    }
    return errors
  }

  async function handleWorkflowSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setHealthMessage(null)
    setRequestError(null)

    const errors = validateForm(form)
    setFormErrors(errors)
    if (Object.keys(errors).length > 0) {
      return
    }

    const generatedRequestId = buildRequestId()
    setRequestId(generatedRequestId)
    setLiveLogs([])
    setWorkflowResult(null)
    setTimelinePhase('running')
    setTimelineStepIndex(0)
    setIsSubmitting(true)

    const stream = openWorkflowStream(generatedRequestId)
    stream.onmessage = (streamEvent) => {
      const runtimeEvent = parseRuntimeEvent(streamEvent.data)
      if (!runtimeEvent) {
        return
      }

      setLiveLogs((previous) => [...previous.slice(-79), runtimeEvent])

      if (runtimeEvent.event !== 'workflow.step') {
        return
      }

      const stepKey = runtimeEvent.fields.step
      const stepStatus = runtimeEvent.fields.status
      if (!stepKey || !stepStatus) {
        return
      }

      const stepIndex = STEP_INDEX_BY_KEY[stepKey]
      if (stepIndex !== undefined) {
        setTimelineStepIndex((previous) => Math.max(previous, stepIndex))
      }

      if (stepStatus === 'error') {
        setTimelinePhase('error')
        setTimelineStepIndex(FLOW_STEPS.length - 1)
      }
    }

    try {
      const execution = await runWorkflow(
        {
          owner: form.owner.trim(),
          repo: form.repo.trim(),
          issue_number: Number(form.issueNumber),
          base_branch: form.baseBranch.trim(),
          dry_run: form.dryRun,
        },
        generatedRequestId,
      )
      setRequestId(execution.requestId)
      setWorkflowResult(execution.response)
      setTimelinePhase('success')
      setTimelineStepIndex(FLOW_STEPS.length - 1)
    } catch (error) {
      setWorkflowResult(null)
      setRequestError(getErrorDetailMessage(error))
      setTimelinePhase('error')
      setTimelineStepIndex(FLOW_STEPS.length - 1)
    } finally {
      setIsSubmitting(false)
      window.setTimeout(() => {
        stream.close()
      }, 750)
    }
  }

  async function handleHealthCheck() {
    setIsCheckingHealth(true)
    setHealthMessage(null)
    setRequestError(null)

    try {
      const health = await checkHealth()
      setHealthMessage(`API health: ${health.status}`)
    } catch (error) {
      setHealthMessage(`API health failed: ${getErrorDetailMessage(error)}`)
    } finally {
      setIsCheckingHealth(false)
    }
  }

  function getTimelineItemClass(index: number): string {
    const lastStepIndex = FLOW_STEPS.length - 1

    if (timelinePhase === 'idle') {
      return 'timeline-item timeline-item--pending'
    }

    if (timelinePhase === 'running') {
      if (index < timelineStepIndex) {
        return 'timeline-item timeline-item--done'
      }
      if (index === timelineStepIndex) {
        return 'timeline-item timeline-item--active'
      }
      return 'timeline-item timeline-item--pending'
    }

    if (timelinePhase === 'success') {
      if (index === lastStepIndex) {
        return 'timeline-item timeline-item--success'
      }
      return 'timeline-item timeline-item--done'
    }

    if (index === lastStepIndex) {
      return 'timeline-item timeline-item--error'
    }
    return 'timeline-item timeline-item--done'
  }

  const timelineHint = useMemo(() => {
    if (timelinePhase === 'running') {
      return 'Progresso em tempo real baseado nos eventos do backend.'
    }
    if (timelinePhase === 'success') {
      return 'Fluxo finalizado com sucesso.'
    }
    if (timelinePhase === 'error') {
      return 'Fluxo finalizado com erro.'
    }
    return 'O backend executa estas etapas em sequência.'
  }, [timelinePhase])

  return (
    <div className="app-shell">
      <header className="hero">
        <p className="eyebrow">POC AI PR Bot</p>
        <h1>Workflow Visual</h1>
        <p className="subtitle">
          Uma visão clara do pipeline <strong>Issue → Branch → Commit → PR</strong> com foco em
          demonstração.
        </p>
      </header>

      <main className="dashboard-grid">
        <section className="panel">
          <h2>Formulário de Execução</h2>
          <p className="panel-caption">
            Defina o contexto da issue para iniciar o fluxo. API base: <code>{getApiBaseUrl()}</code>
          </p>

          <form className="workflow-form" onSubmit={handleWorkflowSubmit} noValidate>
            <label>
              Owner
              <input
                type="text"
                name="owner"
                placeholder="your-org-or-user"
                value={form.owner}
                onChange={(event) => {
                  setForm((previous) => ({ ...previous, owner: event.target.value }))
                }}
                aria-invalid={Boolean(formErrors.owner)}
                className={formErrors.owner ? 'input-error' : ''}
              />
              {formErrors.owner ? <span className="field-error">{formErrors.owner}</span> : null}
            </label>
            <label>
              Repositório
              <input
                type="text"
                name="repo"
                placeholder="repo-name"
                value={form.repo}
                onChange={(event) => {
                  setForm((previous) => ({ ...previous, repo: event.target.value }))
                }}
                aria-invalid={Boolean(formErrors.repo)}
                className={formErrors.repo ? 'input-error' : ''}
              />
              {formErrors.repo ? <span className="field-error">{formErrors.repo}</span> : null}
            </label>
            <label>
              Issue Number
              <input
                type="number"
                name="issue_number"
                min={1}
                placeholder="1"
                value={form.issueNumber}
                onChange={(event) => {
                  setForm((previous) => ({ ...previous, issueNumber: event.target.value }))
                }}
                aria-invalid={Boolean(formErrors.issueNumber)}
                className={formErrors.issueNumber ? 'input-error' : ''}
              />
              {formErrors.issueNumber ? (
                <span className="field-error">{formErrors.issueNumber}</span>
              ) : null}
            </label>
            <label>
              Base Branch
              <input
                type="text"
                name="base_branch"
                value={form.baseBranch}
                onChange={(event) => {
                  setForm((previous) => ({ ...previous, baseBranch: event.target.value }))
                }}
                aria-invalid={Boolean(formErrors.baseBranch)}
                className={formErrors.baseBranch ? 'input-error' : ''}
              />
              {formErrors.baseBranch ? (
                <span className="field-error">{formErrors.baseBranch}</span>
              ) : null}
            </label>
            <label className="checkbox-row">
              <input
                type="checkbox"
                name="dry_run"
                checked={form.dryRun}
                onChange={(event) => {
                  setForm((previous) => ({ ...previous, dryRun: event.target.checked }))
                }}
              />
              <span>Dry run (não publicar alterações)</span>
            </label>

            <div className="button-row">
              <button type="submit" className="button button-primary" disabled={isSubmitting}>
                {isSubmitting ? 'Executando...' : 'Executar Workflow'}
              </button>
              <button
                type="button"
                className="button button-secondary"
                onClick={handleHealthCheck}
                disabled={isCheckingHealth}
              >
                {isCheckingHealth ? 'Testando...' : 'Testar Health'}
              </button>
            </div>

            {healthMessage ? <p className="form-helper">{healthMessage}</p> : null}
          </form>
        </section>

        <section className="panel">
          <h2>Timeline de Etapas</h2>
          <p className="panel-caption">{timelineHint}</p>

          <ol className="timeline">
            {FLOW_STEPS.map((step, index) => (
              <li key={step.title} className={getTimelineItemClass(index)}>
                <div className="timeline-badge">{index + 1}</div>
                <div>
                  <h3>{step.title}</h3>
                  <p>{step.description}</p>
                </div>
              </li>
            ))}
          </ol>

          <div className="live-observability">
            <p className="live-observability-title">Observabilidade ao vivo</p>
            <p className="request-id-line">
              X-Request-ID: <code>{requestId ?? '-'}</code>
            </p>

            <ul className="live-log-list">
              {liveLogs.length === 0 ? (
                <li className="live-log-empty">Sem logs recebidos ainda.</li>
              ) : (
                [...liveLogs]
                  .reverse()
                  .map((runtimeEvent, index) => (
                    <li key={`${runtimeEvent.timestamp}-${index}`} className="live-log-item">
                      <span className="live-log-time">
                        {new Date(runtimeEvent.timestamp).toLocaleTimeString()}
                      </span>
                      <span className="live-log-text">{describeRuntimeEvent(runtimeEvent)}</span>
                    </li>
                  ))
              )}
            </ul>
          </div>
        </section>

        <section className="panel">
          <h2>Resultado Final</h2>
          <p className="panel-caption">Resumo consolidado da execução para apresentação.</p>

          <div className={`result-status result-status--${resultTone}`}>
            <span className={statusPillClass}>{statusPillText}</span>
            <p>
              {requestError ??
                workflowResult?.message ??
                'Preencha os campos e inicie o workflow para ver os dados reais da API.'}
            </p>
          </div>

          {workflowResult?.status === 'dry_run' ? (
            <p className="result-note result-note--dryrun">
              Dry-run confirmado: nenhum push de branch e nenhum PR real foram criados.
            </p>
          ) : null}

          {requestError ? (
            <p className="result-note result-note--error">
              <strong>Error detail:</strong> {requestError || WORKFLOW_ERROR_FALLBACK}
            </p>
          ) : null}

          {resultFields.length > 0 ? (
            <dl className="result-grid">
              <div>
                <dt>Status</dt>
                <dd>{workflowResult?.status ?? 'pending'}</dd>
              </div>
              <div>
                <dt>Mensagem</dt>
                <dd>{workflowResult?.message ?? '-'}</dd>
              </div>
              {resultFields.map((field) => (
                <div key={field.label}>
                  <dt>{field.label}</dt>
                  <dd>
                    {field.isLink ? (
                      <a href={field.value ?? '#'} target="_blank" rel="noreferrer">
                        {field.value}
                      </a>
                    ) : (
                      field.value
                    )}
                  </dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="result-empty">Sem artefatos ainda. Execute o workflow para gerar branch, commit e PR.</p>
          )}
        </section>

        <section className="panel panel--wide">
          <h2>Como Funciona por Dentro</h2>
          <p className="panel-caption">
            Cada agente tem papel claro, com responsabilidade definida e limite de atuação.
          </p>

          <div className="agent-grid">
            {AGENT_CARDS.map((agent) => (
              <article key={agent.name} className="agent-card">
                <h3>{agent.name}</h3>
                <p>
                  <strong>Responsabilidade:</strong> {agent.responsibility}
                </p>
                <p>
                  <strong>Limite:</strong> {agent.scopeLimit}
                </p>
                <p className="agent-runtime">
                  <strong>Ultima execução:</strong>{' '}
                  {agentExecution[agent.id as keyof typeof agentExecution].lastAction}
                </p>
                <p className="agent-runtime">
                  <strong>Entregou:</strong>{' '}
                  {agentExecution[agent.id as keyof typeof agentExecution].delivered}
                </p>
              </article>
            ))}
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
