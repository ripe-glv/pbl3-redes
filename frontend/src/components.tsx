import { FormEvent, ReactNode, useEffect, useState } from "react";
import { api, formatDate, post, shortHash } from "./api";
import type {
  AuthCompany,
  Block,
  Company,
  Drone,
  Mission,
  MissionDetails,
  NodeStatus,
  Transaction,
  Wallet,
} from "./types";

export function LoginScreen({
  nodeUrl,
  nodeUrls,
  onNodeChange,
  onLogin,
}: {
  nodeUrl: string;
  nodeUrls: string[];
  onNodeChange: (nodeUrl: string) => void;
  onLogin: (token: string, company: AuthCompany) => void;
}) {
  const [companyId, setCompanyId] = useState("gulf");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const result = await post<{
        access_token: string;
        company: AuthCompany;
      }>(nodeUrl, "/auth/login", {
        company_id: companyId,
        password,
      });
      onLogin(result.access_token, result.company);
    } catch (loginError) {
      setError(String(loginError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-brand">
          <span className="brand-mark">S</span>
          <div>
            <strong>Sentinel Ledger</strong>
            <small>Portal das companhias</small>
          </div>
        </div>
        <Badge tone="info">AUTENTICAÇÃO DE CARTEIRA</Badge>
        <h1>Acesse a companhia</h1>
        <p>
          A sessão define qual carteira pode assinar operações e abrir laudos
          confidenciais.
        </p>
        <form onSubmit={submit}>
          <label>
            Nó de autenticação
            <select
              value={nodeUrl}
              onChange={(event) => onNodeChange(event.target.value)}
            >
              {nodeUrls.map((url, index) => (
                <option value={url} key={url}>
                  node-{String.fromCharCode(97 + index)} · {url}
                </option>
              ))}
            </select>
          </label>
          <label>
            Companhia
            <select
              value={companyId}
              onChange={(event) => setCompanyId(event.target.value)}
            >
              <option value="gulf">Gulf Shipping Co.</option>
              <option value="atlas">Atlas Maritime</option>
              <option value="orion">Orion Logistics</option>
            </select>
          </label>
          <label>
            Senha
            <input
              type="password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Digite a senha da companhia"
            />
          </label>
          {error && <div className="login-error">{error}</div>}
          <button className="button primary" disabled={submitting} type="submit">
            {submitting ? "Autenticando..." : "Entrar com a carteira"}
          </button>
        </form>
        <div className="demo-credentials">
          <strong>Credenciais de laboratório</strong>
          <code>gulf / Gulf@2026</code>
          <code>atlas / Atlas@2026</code>
          <code>orion / Orion@2026</code>
        </div>
      </section>
      <aside className="login-context">
        <span className="eyebrow">ACESSO CRIPTOGRÁFICO</span>
        <h2>Uma companhia.<br />Uma carteira.<br /><span>Uma chave de acesso.</span></h2>
        <p>
          Todos auditam a prova pública. Somente a companhia proprietária
          consegue visualizar os detalhes protegidos da missão.
        </p>
      </aside>
    </main>
  );
}

export function Panel({
  title,
  eyebrow,
  actions,
  children,
  className = "",
}: {
  title: string;
  eyebrow?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      <header className="panel-header">
        <div>
          {eyebrow && <span className="eyebrow">{eyebrow}</span>}
          <h2>{title}</h2>
        </div>
        {actions}
      </header>
      {children}
    </section>
  );
}

export function Badge({
  children,
  tone = "info",
}: {
  children: ReactNode;
  tone?: "success" | "danger" | "warning" | "info" | "neutral";
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function NodeStatusCard({ node }: { node: NodeStatus }) {
  return (
    <article className={`node-card ${node.online ? "" : "offline"}`}>
      <div className="node-orbit">
        <span className={`status-dot ${node.online ? "online" : ""}`} />
      </div>
      <div>
        <strong>{node.node_id || node.url}</strong>
        <p>{node.online ? "Operacional" : "Inacessível"}</p>
      </div>
      <dl>
        <div>
          <dt>Altura</dt>
          <dd>{node.height ?? "—"}</dd>
        </div>
        <div>
          <dt>Peers</dt>
          <dd>{node.peers ?? "—"}</dd>
        </div>
      </dl>
    </article>
  );
}

export function LedgerBlockCard({
  block,
  selected,
  onClick,
}: {
  block: Block;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={`block-card ${selected ? "selected" : ""}`}
      onClick={onClick}
    >
      <span className="block-index">#{block.index}</span>
      <span>
        <strong>{shortHash(block.hash)}</strong>
        <small>{block.transactions.length} transações</small>
      </span>
      <Badge tone={block.index === 0 ? "info" : "success"}>
        {block.index === 0 ? "GÊNESE" : "POW"}
      </Badge>
    </button>
  );
}

export function TransactionList({
  transactions,
}: {
  transactions: Transaction[];
}) {
  if (!transactions.length) return <div className="empty">Nenhuma transação.</div>;
  return (
    <div className="transaction-list">
      {transactions.map((tx) => (
        <article className="transaction-row" key={tx.id}>
          <div className={`tx-icon ${tx.type.toLowerCase()}`}>↗</div>
          <div className="tx-main">
            <div>
              <Badge tone={tx.type.includes("PROOF") ? "info" : "neutral"}>
                {tx.type}
              </Badge>
              <strong>{tx.amount ? `${tx.amount} OC` : "Registro"}</strong>
            </div>
            <code>{shortHash(tx.id, 12)}</code>
            <small>{formatDate(tx.timestamp)}</small>
          </div>
          <details>
            <summary>payload</summary>
            <pre>{JSON.stringify(tx.payload, null, 2)}</pre>
          </details>
        </article>
      ))}
    </div>
  );
}

export function BalanceTable({ companies }: { companies: Company[] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Companhia</th>
            <th>Carteira</th>
            <th className="number">Saldo confirmado</th>
          </tr>
        </thead>
        <tbody>
          {companies.map((company) => (
            <tr key={company.company_id}>
              <td>
                <strong>{company.name}</strong>
                <small>{company.company_id}</small>
              </td>
              <td>
                <code>{shortHash(company.wallet_address, 14)}</code>
              </td>
              <td className="number credit">{company.balance} OC</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function WalletCard({
  wallet,
  active,
}: {
  wallet: Wallet;
  active: boolean;
}) {
  return (
    <article className={`wallet-card ${active ? "active" : ""}`}>
      <div className="wallet-mark">{wallet.name.slice(0, 2).toUpperCase()}</div>
      <div className="wallet-balance">{wallet.balance} <span>OC</span></div>
      <h3>{wallet.name}</h3>
      <code>{shortHash(wallet.wallet_address, 16)}</code>
      <div className="wallet-actions">
        <Badge tone={active ? "success" : "neutral"}>
          {active ? "CARTEIRA DA SESSÃO" : "SOMENTE LEITURA"}
        </Badge>
        <button
          className="icon-button"
          title="Copiar chave pública"
          onClick={() => navigator.clipboard.writeText(wallet.public_key)}
        >
          ⧉
        </button>
      </div>
    </article>
  );
}

type ActionProps = {
  nodeUrl: string;
  companies: Company[];
  accessToken: string;
  authenticatedCompanyId: string;
  onResult: (label: string, value: unknown, error?: boolean) => void;
  onRefresh: () => void;
};

export function CreditTransferForm({
  nodeUrl,
  companies,
  accessToken,
  authenticatedCompanyId,
  onResult,
  onRefresh,
}: ActionProps) {
  const [recipient, setRecipient] = useState("atlas");
  const [amount, setAmount] = useState(10);
  const recipientOptions = companies.filter(
    (company) => company.company_id !== authenticatedCompanyId,
  );

  useEffect(() => {
    if (recipient === authenticatedCompanyId) {
      setRecipient(recipientOptions[0]?.company_id ?? "");
    }
  }, [authenticatedCompanyId, recipient, recipientOptions]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      const result = await post(nodeUrl, "/credits/transfer", {
        sender_company_id: authenticatedCompanyId,
        recipient_company_id: recipient,
        amount,
      }, accessToken);
      onResult("Transferência confirmada", result);
      onRefresh();
    } catch (error) {
      onResult("Transferência rejeitada", String(error), true);
    }
  }

  return (
    <form className="form-grid" onSubmit={submit}>
      <label>
        Carteira remetente
        <input
          readOnly
          value={
            companies.find((item) => item.company_id === authenticatedCompanyId)
              ?.name ?? authenticatedCompanyId
          }
        />
      </label>
      <label>
        Destinatário
        <select value={recipient} onChange={(e) => setRecipient(e.target.value)}>
          {recipientOptions.map((company) => (
            <option value={company.company_id} key={company.company_id}>
              {company.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Valor em OC
        <input
          type="number"
          min={1}
          value={amount}
          onChange={(e) => setAmount(Number(e.target.value))}
        />
      </label>
      <button className="button primary" type="submit">Assinar e transferir</button>
    </form>
  );
}

export function EscortRequestForm({
  nodeUrl,
  companies,
  drones,
  accessToken,
  authenticatedCompanyId,
  onResult,
  onRefresh,
}: ActionProps & { drones: Drone[] }) {
  const [drone, setDrone] = useState("DRONE-01");
  const [route, setRoute] = useState("ROTA-ALFA");
  const [cost, setCost] = useState(25);

  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      const result = await post(nodeUrl, "/escort/request", {
        company_id: authenticatedCompanyId,
        drone_id: drone,
        route_id: route,
        cost,
      }, accessToken);
      onResult("Escolta paga e drone despachado", result);
      onRefresh();
    } catch (error) {
      onResult("Solicitação rejeitada", String(error), true);
    }
  }

  return (
    <form className="form-grid" onSubmit={submit}>
      <label>
        Companhia solicitante
        <input
          readOnly
          value={
            companies.find((item) => item.company_id === authenticatedCompanyId)
              ?.name ?? authenticatedCompanyId
          }
        />
      </label>
      <label>
        Drone
        <select value={drone} onChange={(e) => setDrone(e.target.value)}>
          {drones.map((item) => (
            <option value={item.drone_id} key={item.drone_id}>
              {item.drone_id} · {item.available ? "disponível" : "ocupado"}
            </option>
          ))}
        </select>
      </label>
      <label>
        Rota
        <select value={route} onChange={(e) => setRoute(e.target.value)}>
          <option>ROTA-ALFA</option>
          <option>ROTA-BRAVO</option>
          <option>ROTA-CHARLIE</option>
        </select>
      </label>
      <label>
        Custo
        <input type="number" min={1} value={cost} onChange={(e) => setCost(+e.target.value)} />
      </label>
      <button className="button primary" type="submit">Pagar e solicitar escolta</button>
    </form>
  );
}

export function MissionReportForm({
  nodeUrl,
  mission,
  onResult,
  onRefresh,
  accessToken,
}: {
  nodeUrl: string;
  mission: Mission;
  onResult: ActionProps["onResult"];
  onRefresh: () => void;
  accessToken: string;
}) {
  const [description, setDescription] = useState("");
  const [result, setResult] = useState("ROTA_SEGURA");
  const [risk, setRisk] = useState("BAIXO");
  const [notes, setNotes] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      const value = await post(nodeUrl, `/missions/${mission.mission_id}/complete`, {
        company_id: mission.company_id,
        result,
        description,
        evidence: ["telemetria", "registro visual"],
        strategic_notes: notes,
        risk_classification: risk,
      }, accessToken);
      onResult("Laudo criptografado e prova registrada", value);
      onRefresh();
    } catch (error) {
      onResult("Falha ao concluir missão", String(error), true);
    }
  }

  return (
    <form className="mission-form" onSubmit={submit}>
      <label>Resultado
        <select value={result} onChange={(e) => setResult(e.target.value)}>
          <option>ROTA_SEGURA</option>
          <option>OBSTACULO_DETECTADO</option>
          <option>INCIDENTE</option>
        </select>
      </label>
      <label>Risco
        <select value={risk} onChange={(e) => setRisk(e.target.value)}>
          <option>BAIXO</option><option>MÉDIO</option><option>ALTO</option>
        </select>
      </label>
      <label className="wide">Descrição confidencial
        <textarea required value={description} onChange={(e) => setDescription(e.target.value)} />
      </label>
      <label className="wide">Observações estratégicas
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} />
      </label>
      <button className="button primary" type="submit">Criptografar e registrar prova</button>
    </form>
  );
}

export function PublicMissionCard({
  mission,
  authenticatedCompanyId,
  accessToken,
  nodeUrl,
  onResult,
  onRefresh,
}: {
  mission: Mission;
  authenticatedCompanyId: string;
  accessToken: string;
  nodeUrl: string;
  onResult: ActionProps["onResult"];
  onRefresh: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [details, setDetails] = useState<MissionDetails | null>(null);
  const [detailsError, setDetailsError] = useState("");
  const [loadingDetails, setLoadingDetails] = useState(false);
  const isOwner = mission.company_id === authenticatedCompanyId;

  async function viewDetails() {
    setDetails(null);
    setDetailsError("");
    setLoadingDetails(true);
    try {
      const value = await post<MissionDetails>(
        nodeUrl,
        `/missions/${mission.mission_id}/decrypt`,
        {},
        accessToken,
      );
      setDetails(value);
    } catch (error) {
      setDetailsError(String(error));
    } finally {
      setLoadingDetails(false);
    }
  }
  return (
    <article className="mission-card">
      <header>
        <div>
          <Badge tone={mission.status === "COMPLETED" ? "success" : "warning"}>
            {mission.status}
          </Badge>
          <h3>{mission.mission_id}</h3>
        </div>
        <span className="drone-chip">{mission.drone_id}</span>
      </header>
      <div className="mission-meta">
        <span>Rota<strong>{mission.route_id}</strong></span>
        <span>Custo<strong>{mission.cost} OC</strong></span>
        <span>Data<strong>{formatDate(mission.created_at)}</strong></span>
      </div>
      {mission.report_hash && (
        <div className="proof-box">
          <Badge tone="info">CONTEÚDO OFF-CHAIN CRIPTOGRAFADO</Badge>
          <code>laudo {shortHash(mission.report_hash, 15)}</code>
          <code>arquivo {shortHash(mission.encrypted_file_hash, 15)}</code>
        </div>
      )}
      <div className="card-actions">
        {mission.status === "ACTIVE" && isOwner && (
          <button className="button secondary" onClick={() => setExpanded(!expanded)}>
            Concluir missão
          </button>
        )}
        {mission.report_hash && (
          <>
            <button
              className="button secondary"
              onClick={async () => {
                try {
                  const value = await fetch(
                    `${nodeUrl}/missions/${mission.mission_id}/verify-file-integrity`,
                  ).then(async (r) => {
                    const body = await r.json();
                    if (!r.ok) throw new Error(body.detail);
                    return body;
                  });
                  onResult("Integridade do arquivo", value);
                } catch (error) {
                  onResult("Falha de auditoria", String(error), true);
                }
              }}
            >
              Verificar arquivo
            </button>
            <button className="button primary" onClick={viewDetails}>
              {loadingDetails ? "Abrindo..." : "Visualizar detalhes da missão"}
            </button>
          </>
        )}
      </div>
      {expanded && (
        <MissionReportForm
          nodeUrl={nodeUrl}
          mission={mission}
          onResult={onResult}
          onRefresh={onRefresh}
          accessToken={accessToken}
        />
      )}
      {detailsError && (
        <div className="mission-access-denied">
          <Badge tone="danger">ACESSO BLOQUEADO</Badge>
          <strong>Esta missão pertence a outra companhia.</strong>
          <p>
            Você pode auditar hashes e metadados públicos, mas a sessão atual
            não possui a chave privada necessária para abrir o laudo.
          </p>
        </div>
      )}
      {details && (
        <section className="mission-details">
          <header>
            <div>
              <Badge tone={details.valid ? "success" : "danger"}>
                {details.valid ? "LAUDO ÍNTEGRO" : "LAUDO ADULTERADO"}
              </Badge>
              <h4>Detalhes confidenciais</h4>
            </div>
            <button
              className="icon-button"
              title="Fechar detalhes"
              onClick={() => setDetails(null)}
            >
              ×
            </button>
          </header>
          <dl>
            <div><dt>Resultado</dt><dd>{details.report.result}</dd></div>
            <div><dt>Risco</dt><dd>{details.report.risk_classification}</dd></div>
            <div><dt>Rota detalhada</dt><dd>{details.report.detailed_route}</dd></div>
            <div><dt>Data</dt><dd>{formatDate(details.report.timestamp)}</dd></div>
          </dl>
          <article>
            <span>Descrição completa</span>
            <p>{details.report.description}</p>
          </article>
          <article>
            <span>Evidências coletadas</span>
            <ul>
              {details.report.evidence.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </article>
          <article>
            <span>Observações estratégicas</span>
            <p>{details.report.strategic_notes || "Sem observações."}</p>
          </article>
          <div className="detail-hashes">
            <code>calculado {shortHash(details.calculated_hash, 18)}</code>
            <code>registrado {shortHash(details.registered_hash, 18)}</code>
          </div>
        </section>
      )}
    </article>
  );
}

export function DecryptMissionPanel({ result }: { result: unknown }) {
  if (!result) return null;
  return <pre className="result-code">{JSON.stringify(result, null, 2)}</pre>;
}

export function AuditPanel({
  nodeUrl,
  missions,
  onResult,
  onRefresh,
}: {
  nodeUrl: string;
  missions: Mission[];
  onResult: ActionProps["onResult"];
  onRefresh: () => void;
}) {
  const completed = missions.find((mission) => mission.report_hash);
  const actions = [
    { label: "Verificar cadeia", method: "GET", path: "/audit/verify-chain", tone: "success" },
    { label: "Adulterar blockchain", method: "POST", path: "/audit/tamper-chain", tone: "danger" },
    {
      label: "Adulterar arquivo off-chain",
      method: "POST",
      path: "/audit/tamper-storage",
      body: { target: "storage", mission_id: completed?.mission_id },
      tone: "danger",
    },
    { label: "Sincronizar com peers", method: "POST", path: "/audit/repair", tone: "info" },
  ];

  return (
    <div className="audit-grid">
      {actions.map((action) => (
        <button
          key={action.label}
          className={`audit-action ${action.tone}`}
          onClick={async () => {
            try {
              const value =
                action.method === "GET"
                  ? await fetch(`${nodeUrl}${action.path}`).then(async (r) => {
                      const body = await r.json();
                      if (!r.ok) throw new Error(body.detail);
                      return body;
                    })
                  : await post(nodeUrl, action.path, action.body ?? {});
              onResult(action.label, value);
              onRefresh();
            } catch (error) {
              onResult(action.label, String(error), true);
            }
          }}
        >
          <span>{action.label}</span>
          <small>Executar no nó selecionado</small>
        </button>
      ))}
    </div>
  );
}

export function DemoPanel({
  nodeUrl,
  accessToken,
  onResult,
  onRefresh,
}: {
  nodeUrl: string;
  accessToken: string;
  onResult: ActionProps["onResult"];
  onRefresh: () => void;
}) {
  const demos = [
    ["Duplo gasto", "/demo/double-spend"],
    ["Mesmo drone, duas companhias", "/demo/drone-race"],
    ["Comparar nós", "/demo/compare-nodes", "GET"],
    ["Carteira correta", "/demo/decrypt-correct-wallet"],
    ["Carteira errada", "/demo/decrypt-wrong-wallet"],
  ];
  return (
    <div className="demo-grid">
      {demos.map(([label, path, method]) => (
        <button
          className="demo-card"
          key={path}
          onClick={async () => {
            try {
              const value =
                method === "GET"
                  ? await fetch(`${nodeUrl}${path}`).then((r) => r.json())
                  : await post(nodeUrl, path, {}, accessToken);
              onResult(`Teste: ${label}`, value);
              onRefresh();
            } catch (error) {
              onResult(`Teste: ${label}`, String(error), true);
            }
          }}
        >
          <span className="demo-play">▶</span>
          <strong>{label}</strong>
          <small>Executar cenário do barema</small>
        </button>
      ))}
    </div>
  );
}

export type LogEntry = {
  time: string;
  label: string;
  value: unknown;
  error?: boolean;
};

export function LogsPanel({ entries }: { entries: LogEntry[] }) {
  return (
    <div className="logs">
      {!entries.length && <div className="empty">As operações aparecerão aqui.</div>}
      {entries.map((entry, index) => (
        <details className={entry.error ? "log error" : "log"} key={`${entry.time}-${index}`} open={index === 0}>
          <summary>
            <span>{entry.error ? "REJEITADO" : "OK"}</span>
            <strong>{entry.label}</strong>
            <time>{entry.time}</time>
          </summary>
          <pre>{typeof entry.value === "string" ? entry.value : JSON.stringify(entry.value, null, 2)}</pre>
        </details>
      ))}
    </div>
  );
}
