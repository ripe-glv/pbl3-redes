import { useCallback, useEffect, useMemo, useState } from "react";
import { api, authenticatedApi, NODE_URLS, shortHash } from "./api";
import {
  AuditPanel,
  BalanceTable,
  Badge,
  CreditTransferForm,
  DecryptMissionPanel,
  DemoPanel,
  EscortRequestForm,
  LedgerBlockCard,
  LoginScreen,
  LogsPanel,
  NodeStatusCard,
  Panel,
  PublicMissionCard,
  TransactionList,
  WalletCard,
  type LogEntry,
} from "./components";
import type {
  AuthCompany,
  Block,
  Company,
  Drone,
  Mission,
  NodeStatus,
  Transaction,
  Wallet,
} from "./types";
import "./styles.css";

const sections = [
  ["dashboard", "Visão geral"],
  ["ledger", "Explorer do ledger"],
  ["wallets", "Carteiras"],
  ["credits", "Créditos operacionais"],
  ["escort", "Solicitar escolta"],
  ["missions", "Missões e laudos"],
  ["audit", "Auditoria"],
  ["demo", "Demonstrações"],
] as const;

type Section = (typeof sections)[number][0];

export default function App() {
  const [section, setSection] = useState<Section>("dashboard");
  const [nodeUrl, setNodeUrl] = useState(NODE_URLS[0]);
  const [statuses, setStatuses] = useState<NodeStatus[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [wallets, setWallets] = useState<Wallet[]>([]);
  const [drones, setDrones] = useState<Drone[]>([]);
  const [missions, setMissions] = useState<Mission[]>([]);
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [selectedBlock, setSelectedBlock] = useState<Block | null>(null);
  const [accessToken, setAccessToken] = useState(
    () => window.localStorage.getItem("sentinel_access_token") ?? "",
  );
  const [authCompany, setAuthCompany] = useState<AuthCompany | null>(null);
  const [authLoading, setAuthLoading] = useState(Boolean(accessToken));
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const addLog = useCallback((label: string, value: unknown, error = false) => {
    setLogs((current) =>
      [
        { label, value, error, time: new Date().toLocaleTimeString("pt-BR") },
        ...current,
      ].slice(0, 30),
    );
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    const nodeResults = await Promise.all(
      NODE_URLS.map(async (url): Promise<NodeStatus> => {
        try {
          return { ...(await api<NodeStatus>(url, "/node/status")), url };
        } catch {
          return {
            node_id: url.split(":").at(-1) ?? url,
            online: false,
            height: 0,
            transactions: 0,
            mempool: 0,
            peers: 0,
            chain_valid: false,
            url,
          };
        }
      }),
    );
    setStatuses(nodeResults);
    try {
      const [companyData, walletData, droneData, missionData, blockData, txData] =
        await Promise.all([
          api<Company[]>(nodeUrl, "/companies"),
          api<Wallet[]>(nodeUrl, "/wallets"),
          api<Drone[]>(nodeUrl, "/drones"),
          api<Mission[]>(nodeUrl, "/missions"),
          api<Block[]>(nodeUrl, "/blocks"),
          api<Transaction[]>(nodeUrl, "/transactions"),
        ]);
      setCompanies(companyData);
      setWallets(walletData);
      setDrones(droneData);
      setMissions(missionData);
      setBlocks(blockData);
      setTransactions(txData);
      setSelectedBlock((current) =>
        current ? blockData.find((item) => item.index === current.index) ?? blockData[0] : blockData[0],
      );
    } catch (error) {
      addLog("Falha ao atualizar nó selecionado", String(error), true);
    } finally {
      setLoading(false);
    }
  }, [addLog, nodeUrl]);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 8000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  useEffect(() => {
    if (!accessToken) {
      setAuthLoading(false);
      setAuthCompany(null);
      return;
    }
    setAuthLoading(true);
    authenticatedApi<AuthCompany>(nodeUrl, "/auth/me", accessToken)
      .then(setAuthCompany)
      .catch(() => {
        window.localStorage.removeItem("sentinel_access_token");
        setAccessToken("");
        setAuthCompany(null);
      })
      .finally(() => setAuthLoading(false));
  }, [accessToken, nodeUrl]);

  const localStatus = statuses.find((item) => item.url === nodeUrl);
  const validNodes = statuses.filter((node) => node.online).length;
  const totalMissions = missions.length;
  const activeWallet = wallets.find(
    (wallet) => wallet.company_id === authCompany?.company_id,
  );

  const pageTitle = useMemo(
    () => sections.find(([key]) => key === section)?.[1] ?? "",
    [section],
  );

  if (authLoading) {
    return <div className="auth-loading">Validando sessão da companhia...</div>;
  }

  if (!accessToken || !authCompany) {
    return (
      <LoginScreen
        nodeUrl={nodeUrl}
        nodeUrls={NODE_URLS}
        onNodeChange={setNodeUrl}
        onLogin={(token, company) => {
          window.localStorage.setItem("sentinel_access_token", token);
          setAccessToken(token);
          setAuthCompany(company);
        }}
      />
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">S</span>
          <div><strong>Sentinel</strong><small>Distributed Ledger</small></div>
        </div>
        <nav>
          {sections.map(([key, label], index) => (
            <button className={section === key ? "active" : ""} onClick={() => setSection(key)} key={key}>
              <span>{String(index + 1).padStart(2, "0")}</span>{label}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <span className="status-dot online" />
          <div><strong>{validNodes}/{NODE_URLS.length} nós online</strong><small>Rede sem autoridade central</small></div>
        </div>
      </aside>

      <main>
        <header className="topbar">
          <div><span className="eyebrow">TEC502 · ECONOMIA E AUDITORIA DE GUERRA</span><h1>{pageTitle}</h1></div>
          <div className="top-actions">
            <div className="session-chip">
              <span>{authCompany.name.slice(0, 2).toUpperCase()}</span>
              <div>
                <strong>{authCompany.name}</strong>
                <small>Carteira autenticada</small>
              </div>
            </div>
            <label className="node-selector">Nó consultado
              <select value={nodeUrl} onChange={(e) => setNodeUrl(e.target.value)}>
                {NODE_URLS.map((url, index) => <option value={url} key={url}>node-{String.fromCharCode(97 + index)} · {url}</option>)}
              </select>
            </label>
            <button className="icon-button" onClick={() => void refresh()} title="Atualizar">↻</button>
            <button
              className="button secondary"
              onClick={() => {
                window.localStorage.removeItem("sentinel_access_token");
                setAccessToken("");
                setAuthCompany(null);
              }}
            >
              Sair
            </button>
          </div>
        </header>

        {loading && <div className="loading-bar" />}

        <div className="content">
          {section === "dashboard" && (
            <>
              <div className="hero">
                <div>
                  <Badge tone={localStatus?.chain_valid ? "success" : "danger"}>
                    {localStatus?.chain_valid ? "LEDGER ÍNTEGRO" : "VERIFICAÇÃO NECESSÁRIA"}
                  </Badge>
                  <h2>A blockchain não guarda o segredo.<br /><span>Ela guarda a prova.</span></h2>
                  <p>Créditos, pagamentos e provas públicas distribuídos. Laudos confidenciais permanecem criptografados fora da cadeia.</p>
                </div>
                <div className="chain-visual"><i /><i /><i /><span>HASH</span></div>
              </div>
              <div className="metric-grid">
                <article><small>Nós ativos</small><strong>{validNodes}<span>/{NODE_URLS.length}</span></strong><Badge tone="success">P2P</Badge></article>
                <article><small>Altura da cadeia</small><strong>{localStatus?.height ?? 0}</strong><code>{shortHash(blocks[0]?.hash)}</code></article>
                <article><small>Transações</small><strong>{transactions.length}</strong><span>confirmadas</span></article>
                <article><small>Missões</small><strong>{totalMissions}</strong><span>{missions.filter((m) => m.status === "ACTIVE").length} ativas</span></article>
              </div>
              <Panel title="Topologia da rede" eyebrow="NÓS INDEPENDENTES">
                <div className="nodes-grid">{statuses.map((node) => <NodeStatusCard node={node} key={node.url} />)}</div>
              </Panel>
              <div className="two-columns">
                <Panel title="Saldos derivados do ledger" eyebrow="OPERATIONAL CREDIT"><BalanceTable companies={companies} /></Panel>
                <Panel title="Atividade recente" eyebrow="ÚLTIMAS TRANSAÇÕES"><TransactionList transactions={transactions.slice(0, 4)} /></Panel>
              </div>
            </>
          )}

          {section === "ledger" && (
            <div className="explorer-layout">
              <Panel title="Blocos confirmados" eyebrow={`${blocks.length} BLOCOS`}>
                <div className="block-list">{blocks.map((block) => <LedgerBlockCard block={block} selected={selectedBlock?.index === block.index} onClick={() => setSelectedBlock(block)} key={block.hash} />)}</div>
              </Panel>
              <Panel title={selectedBlock ? `Bloco #${selectedBlock.index}` : "Selecione um bloco"} eyebrow="DETALHES CRIPTOGRÁFICOS">
                {selectedBlock && <div className="block-detail">
                  <dl>
                    <div><dt>Hash</dt><dd><code>{selectedBlock.hash}</code></dd></div>
                    <div><dt>Hash anterior</dt><dd><code>{selectedBlock.previous_hash}</code></dd></div>
                    <div><dt>Criador</dt><dd>{selectedBlock.node_id}</dd></div>
                    <div><dt>Nonce</dt><dd>{selectedBlock.nonce}</dd></div>
                  </dl>
                  <TransactionList transactions={selectedBlock.transactions} />
                </div>}
              </Panel>
            </div>
          )}

          {section === "wallets" && (
            <>
              <div className="wallet-grid">{wallets.map((wallet) => <WalletCard wallet={wallet} active={wallet.company_id === authCompany.company_id} key={wallet.company_id} />)}</div>
              <Panel title={`Histórico · ${activeWallet?.name ?? ""}`} eyebrow="ASSINATURAS E MOVIMENTAÇÕES">
                <TransactionList transactions={transactions.filter((tx) => tx.sender === activeWallet?.wallet_address || tx.recipient === activeWallet?.wallet_address)} />
              </Panel>
            </>
          )}

          {section === "credits" && (
            <div className="two-columns">
              <Panel title="Transferir créditos" eyebrow="TRANSAÇÃO ASSINADA"><CreditTransferForm nodeUrl={nodeUrl} companies={companies} accessToken={accessToken} authenticatedCompanyId={authCompany.company_id} onResult={addLog} onRefresh={() => void refresh()} /></Panel>
              <Panel title="Posse atual" eyebrow="CALCULADA DO HISTÓRICO"><BalanceTable companies={companies} /></Panel>
              <Panel title="Histórico de ativos" className="span-two"><TransactionList transactions={transactions.filter((tx) => ["GENESIS_CREDIT", "TRANSFER_CREDIT", "ESCORT_PAYMENT"].includes(tx.type))} /></Panel>
            </div>
          )}

          {section === "escort" && (
            <div className="two-columns">
              <Panel title="Nova requisição" eyebrow="PAGAMENTO ANTES DO DESPACHO"><EscortRequestForm nodeUrl={nodeUrl} companies={companies} drones={drones} accessToken={accessToken} authenticatedCompanyId={authCompany.company_id} onResult={addLog} onRefresh={() => void refresh()} /></Panel>
              <Panel title="Estado da frota" eyebrow="DERIVADO DO LEDGER">
                <div className="fleet">{drones.map((drone) => <article key={drone.drone_id}><span className={`status-dot ${drone.available ? "online" : "busy"}`} /><strong>{drone.drone_id}</strong><Badge tone={drone.available ? "success" : "warning"}>{drone.available ? "DISPONÍVEL" : "EM MISSÃO"}</Badge><small>{drone.active_mission ?? "Aguardando despacho"}</small></article>)}</div>
              </Panel>
            </div>
          )}

          {section === "missions" && (
            <>
              <div className="section-intro"><div><h2>Missões e provas públicas</h2><p>Metadados auditáveis on-chain; detalhes liberados somente à carteira autenticada proprietária.</p></div><div className="connected-wallet"><span>Carteira conectada</span><strong>{authCompany.name}</strong><code>{shortHash(authCompany.wallet_address, 14)}</code></div></div>
              <div className="mission-grid">{missions.map((mission) => <PublicMissionCard mission={mission} authenticatedCompanyId={authCompany.company_id} accessToken={accessToken} nodeUrl={nodeUrl} onResult={addLog} onRefresh={() => void refresh()} key={mission.mission_id} />)}</div>
              {!missions.length && <div className="empty large">Nenhuma missão registrada. Solicite uma escolta primeiro.</div>}
            </>
          )}

          {section === "audit" && (
            <>
              <Panel title="Controles de integridade" eyebrow="ADULTERAÇÃO E RECUPERAÇÃO"><AuditPanel nodeUrl={nodeUrl} missions={missions} onResult={addLog} onRefresh={() => void refresh()} /></Panel>
              <Panel title="Resultado da última operação" eyebrow="EVIDÊNCIA TÉCNICA"><DecryptMissionPanel result={logs[0]?.value} /></Panel>
            </>
          )}

          {section === "demo" && (
            <>
              <Panel title="Roteiro de demonstração do barema" eyebrow="TESTES REPRODUZÍVEIS"><DemoPanel nodeUrl={nodeUrl} accessToken={accessToken} onResult={addLog} onRefresh={() => void refresh()} /></Panel>
              <Panel title="Logs da apresentação" eyebrow="RESULTADO ESPERADO × OBTIDO"><LogsPanel entries={logs} /></Panel>
            </>
          )}
        </div>
      </main>

      {section !== "demo" && logs.length > 0 && (
        <aside className={`toast ${logs[0].error ? "error" : ""}`}>
          <button onClick={() => setLogs((current) => current.slice(1))}>×</button>
          <Badge tone={logs[0].error ? "danger" : "success"}>{logs[0].error ? "ERRO" : "CONFIRMADO"}</Badge>
          <strong>{logs[0].label}</strong>
          <small>Consulte Demonstrações para ver o log completo.</small>
        </aside>
      )}
    </div>
  );
}
