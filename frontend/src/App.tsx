import './App.css'

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

function App() {
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
          <p className="panel-caption">Defina o contexto da issue para iniciar o fluxo.</p>

          <form
            className="workflow-form"
            onSubmit={(event) => {
              event.preventDefault()
            }}
          >
            <label>
              Owner
              <input type="text" name="owner" placeholder="your-org-or-user" />
            </label>
            <label>
              Repositório
              <input type="text" name="repo" placeholder="repo-name" />
            </label>
            <label>
              Issue Number
              <input type="number" name="issue_number" min={1} placeholder="1" />
            </label>
            <label>
              Base Branch
              <input type="text" name="base_branch" defaultValue="main" />
            </label>
            <label className="checkbox-row">
              <input type="checkbox" name="dry_run" />
              <span>Dry run (não publicar alterações)</span>
            </label>

            <div className="button-row">
              <button type="submit" className="button button-primary">
                Executar Workflow
              </button>
              <button type="button" className="button button-secondary">
                Testar Health
              </button>
            </div>
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
            <span className="status-pill">Aguardando execução</span>
            <p>Preencha os campos e inicie o workflow para ver os dados reais da API.</p>
          </div>

          <dl className="result-grid">
            <div>
              <dt>Status</dt>
              <dd>pending</dd>
            </div>
            <div>
              <dt>Mensagem</dt>
              <dd>Execução ainda não iniciada.</dd>
            </div>
            <div>
              <dt>Branch</dt>
              <dd>-</dd>
            </div>
            <div>
              <dt>Commit</dt>
              <dd>-</dd>
            </div>
            <div>
              <dt>PR Title</dt>
              <dd>-</dd>
            </div>
            <div>
              <dt>PR URL</dt>
              <dd>-</dd>
            </div>
          </dl>
        </section>
      </main>
    </div>
  )
}

export default App
