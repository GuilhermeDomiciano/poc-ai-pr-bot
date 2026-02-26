import { type FormEvent, useEffect, useMemo, useState } from 'react'
import './App.css'
import { checkHealth, getApiBaseUrl, runWorkflow } from './services/workflowApi'
import type { RunWorkflowResponse } from './types/workflow'

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
    name: 'Backend Dev',
    responsibility: 'Implementa lógica de backend com alterações mínimas e contratos estáveis.',
    scopeLimit: 'Pode editar apenas arquivos em backend/.',
  },
  {
    name: 'Frontend Dev',
    responsibility: 'Implementa UI e integração cliente/API com tipagem e estados de feedback.',
    scopeLimit: 'Pode editar apenas arquivos em frontend/.',
  },
  {
    name: 'Integration Engineer',
    responsibility: 'Resolve incompatibilidades entre frontend e backend e garante contrato fim a fim.',
    scopeLimit: 'Pode editar backend/ e frontend/ quando necessário para integração.',
  },
  {
    name: 'QA Reviewer',
    responsibility: 'Valida qualidade E2E, segurança e consistência do contrato final.',
    scopeLimit: 'Não implementa feature nova; aprova ou bloqueia com critérios objetivos.',
  },
  {
    name: 'Git Integrator',
    responsibility: 'Consolida saída final em JSON com arquivos, branch, commit e dados de PR.',
    scopeLimit: 'Entrega estritamente JSON válido e caminhos sob backend/ ou frontend/.',
  },
]

type FormState = {
  owner: string
  repo: string
  issueNumber: string
  baseBranch: string
  dryRun: boolean
}

type FormErrors = Partial<Record<keyof Omit<FormState, 'dryRun'>, string>>
type TimelinePhase = 'idle' | 'running' | 'success' | 'error'

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

function App() {
  const [form, setForm] = useState<FormState>(INITIAL_FORM)
  const [formErrors, setFormErrors] = useState<FormErrors>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isCheckingHealth, setIsCheckingHealth] = useState(false)
  const [healthMessage, setHealthMessage] = useState<string | null>(null)
  const [requestError, setRequestError] = useState<string | null>(null)
  const [workflowResult, setWorkflowResult] = useState<RunWorkflowResponse | null>(null)
  const [timelinePhase, setTimelinePhase] = useState<TimelinePhase>('idle')
  const [timelineStepIndex, setTimelineStepIndex] = useState(-1)

  useEffect(() => {
    if (!isSubmitting) {
      return
    }

    const stepTimer = window.setInterval(() => {
      setTimelineStepIndex((previous) => {
        if (previous < FLOW_STEPS.length - 1) {
          return previous + 1
        }
        return previous
      })
    }, 1200)

    return () => {
      window.clearInterval(stepTimer)
    }
  }, [isSubmitting])

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

    setTimelinePhase('running')
    setTimelineStepIndex(0)
    setIsSubmitting(true)
    try {
      const response = await runWorkflow({
        owner: form.owner.trim(),
        repo: form.repo.trim(),
        issue_number: Number(form.issueNumber),
        base_branch: form.baseBranch.trim(),
        dry_run: form.dryRun,
      })
      setWorkflowResult(response)
      setTimelinePhase('success')
      setTimelineStepIndex(FLOW_STEPS.length - 1)
    } catch (error) {
      setWorkflowResult(null)
      setRequestError(getErrorDetailMessage(error))
      setTimelinePhase('error')
      setTimelineStepIndex(FLOW_STEPS.length - 1)
    } finally {
      setIsSubmitting(false)
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
      return 'Demonstração em andamento: etapas avançando automaticamente.'
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
              </article>
            ))}
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
