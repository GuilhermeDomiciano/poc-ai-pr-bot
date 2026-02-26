import { type FormEvent, useMemo, useState } from 'react'
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

type FormState = {
  owner: string
  repo: string
  issueNumber: string
  baseBranch: string
  dryRun: boolean
}

type FormErrors = Partial<Record<keyof Omit<FormState, 'dryRun'>, string>>

const INITIAL_FORM: FormState = {
  owner: '',
  repo: '',
  issueNumber: '',
  baseBranch: 'main',
  dryRun: false,
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message
  }
  return 'Unexpected request error'
}

function App() {
  const [form, setForm] = useState<FormState>(INITIAL_FORM)
  const [formErrors, setFormErrors] = useState<FormErrors>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isCheckingHealth, setIsCheckingHealth] = useState(false)
  const [healthMessage, setHealthMessage] = useState<string | null>(null)
  const [requestError, setRequestError] = useState<string | null>(null)
  const [workflowResult, setWorkflowResult] = useState<RunWorkflowResponse | null>(null)

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
    if (workflowResult?.status === 'success' || workflowResult?.status === 'dry_run') {
      return 'status-pill status-pill--success'
    }
    return 'status-pill'
  }, [isSubmitting, requestError, workflowResult])

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
    } catch (error) {
      setWorkflowResult(null)
      setRequestError(getErrorMessage(error))
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
      setHealthMessage(`API health failed: ${getErrorMessage(error)}`)
    } finally {
      setIsCheckingHealth(false)
    }
  }

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
            {requestError ? <p className="field-error">{requestError}</p> : null}
          </form>
        </section>

        <section className="panel">
          <h2>Timeline de Etapas</h2>
          <p className="panel-caption">O backend executa estas etapas em sequência.</p>

          <ol className="timeline">
            {FLOW_STEPS.map((step, index) => (
              <li key={step.title} className={index === 0 ? 'timeline-item current' : 'timeline-item'}>
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

          <div className="result-status">
            <span className={statusPillClass}>{statusPillText}</span>
            <p>
              {requestError ??
                workflowResult?.message ??
                'Preencha os campos e inicie o workflow para ver os dados reais da API.'}
            </p>
          </div>

          <dl className="result-grid">
            <div>
              <dt>Status</dt>
              <dd>{workflowResult?.status ?? (requestError ? 'error' : 'pending')}</dd>
            </div>
            <div>
              <dt>Mensagem</dt>
              <dd>
                {requestError ?? workflowResult?.message ?? 'Execução ainda não iniciada.'}
              </dd>
            </div>
            <div>
              <dt>Branch</dt>
              <dd>{workflowResult?.branch || '-'}</dd>
            </div>
            <div>
              <dt>Commit</dt>
              <dd>{workflowResult?.commit || '-'}</dd>
            </div>
            <div>
              <dt>PR Title</dt>
              <dd>{workflowResult?.pr_title || '-'}</dd>
            </div>
            <div>
              <dt>PR URL</dt>
              <dd>{workflowResult?.pr_url || '-'}</dd>
            </div>
          </dl>
        </section>
      </main>
    </div>
  )
}

export default App
