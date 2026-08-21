import { useEffect, useMemo, useState } from "react";
import { Kanban, Wallet, Clock, ArrowUpRight, Trash2 } from "lucide-react";
import { api } from "../api";
import { formatarValor, formatarDataHora, diasRestantes, tempoRelativo, iniciais } from "../utils/data";
import NumeroAnimado from "../components/NumeroAnimado";

const DURACAO_SAIDA = 200;

const COLUNAS = [
  { valor: "monitorando", rotulo: "Monitorando", tag: "neutro" },
  { valor: "analisando", rotulo: "Analisando", tag: "dourado" },
  { valor: "proposta_enviada", rotulo: "Proposta enviada", tag: "escuro" },
  { valor: "ganhou", rotulo: "Ganhou", tag: "verde" },
  { valor: "perdeu", rotulo: "Perdeu", tag: "terracota" },
];

const ROTULOS = Object.fromEntries(COLUNAS.map((c) => [c.valor, c.rotulo]));

const CORES_COLUNA = {
  neutro: "var(--slate-dim)",
  dourado: "var(--selo-gold)",
  escuro: "var(--ink-soft)",
  verde: "var(--verde-protocolo)",
  terracota: "var(--terracota)",
};

function tagDoStatus(status) {
  return COLUNAS.find((c) => c.valor === status)?.tag ?? "neutro";
}

function urgenciaPrazo(dataStr) {
  const dias = diasRestantes(dataStr);
  if (dias === null) return { percentual: 0, cor: "var(--linha)", rotulo: "sem prazo definido" };
  if (dias < 0) return { percentual: 100, cor: "var(--terracota)", rotulo: "prazo encerrado" };
  const percentual = Math.max(6, 100 - (Math.min(dias, 30) / 30) * 100);
  const cor = dias <= 3 ? "var(--terracota)" : dias <= 10 ? "var(--selo-gold)" : "var(--verde-protocolo)";
  const rotulo = dias === 0 ? "encerra hoje" : `${dias} dia${dias === 1 ? "" : "s"} restante${dias === 1 ? "" : "s"}`;
  return { percentual, cor, rotulo };
}

function AnelProgresso({ percentual, tamanho = 108, espessura = 10 }) {
  const raio = (tamanho - espessura) / 2;
  const circunferencia = 2 * Math.PI * raio;
  const offset = circunferencia - (Math.max(0, Math.min(100, percentual)) / 100) * circunferencia;
  return (
    <svg width={tamanho} height={tamanho} viewBox={`0 0 ${tamanho} ${tamanho}`}>
      <circle cx={tamanho / 2} cy={tamanho / 2} r={raio} fill="none" stroke="var(--linha)" strokeWidth={espessura} />
      <circle
        cx={tamanho / 2}
        cy={tamanho / 2}
        r={raio}
        fill="none"
        stroke="var(--selo-gold)"
        strokeWidth={espessura}
        strokeLinecap="round"
        strokeDasharray={circunferencia}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${tamanho / 2} ${tamanho / 2})`}
        style={{ transition: "stroke-dashoffset 700ms cubic-bezier(0.2, 0.6, 0.3, 1)" }}
      />
    </svg>
  );
}

export default function Pipeline() {
  const [itens, setItens] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [saindo, setSaindo] = useState({}); // numero_controle -> true enquanto o cartão está saindo de vista
  const [anelPronto, setAnelPronto] = useState(false);

  function carregar() {
    setCarregando(true);
    setErro("");
    api
      .listarPipeline()
      .then(setItens)
      .catch((err) => setErro(err.message))
      .finally(() => setCarregando(false));
  }

  useEffect(() => {
    carregar();
  }, []);

  useEffect(() => {
    // atrasa um quadro pra garantir que o anel pinte em 0% antes de animar até o valor real
    const t = setTimeout(() => setAnelPronto(true), 60);
    return () => clearTimeout(t);
  }, []);

  const stats = useMemo(() => {
    const porStatus = Object.fromEntries(COLUNAS.map((c) => [c.valor, 0]));
    itens.forEach((o) => {
      porStatus[o.status] = (porStatus[o.status] || 0) + 1;
    });
    const decididas = porStatus.ganhou + porStatus.perdeu;
    const taxaConversao = decididas > 0 ? Math.round((porStatus.ganhou / decididas) * 100) : null;
    const emAndamento = porStatus.monitorando + porStatus.analisando + porStatus.proposta_enviada;
    return { total: itens.length, porStatus, decididas, taxaConversao, emAndamento };
  }, [itens]);

  const recentes = useMemo(() => {
    return [...itens]
      .filter((o) => o.status_atualizado_em)
      .sort((a, b) => new Date(b.status_atualizado_em) - new Date(a.status_atualizado_em))
      .slice(0, 5);
  }, [itens]);

  async function moverStatus(numeroControle, statusNovo) {
    // deixa o cartão "sair" da coluna atual antes de trocar o status —
    // sem isso a troca de coluna acontece instantânea e sem transição
    setSaindo((s) => ({ ...s, [numeroControle]: true }));
    setTimeout(() => {
      setItens((atual) => atual.map((o) => (o.numero_controle === numeroControle ? { ...o, status: statusNovo } : o)));
      setSaindo((s) => {
        const copia = { ...s };
        delete copia[numeroControle];
        return copia;
      });
    }, DURACAO_SAIDA);
    try {
      await api.atualizarStatusPipeline(numeroControle, statusNovo);
    } catch (err) {
      setErro(err.message);
      carregar(); // desfaz a mudança otimista se a API recusar
    }
  }

  async function remover(numeroControle) {
    if (!confirm("Remover essa licitação do pipeline da equipe? Isso não afeta os favoritos de ninguém.")) return;
    setSaindo((s) => ({ ...s, [numeroControle]: true }));
    setTimeout(() => {
      setItens((atual) => atual.filter((o) => o.numero_controle !== numeroControle));
      setSaindo((s) => {
        const copia = { ...s };
        delete copia[numeroControle];
        return copia;
      });
    }, DURACAO_SAIDA);
    try {
      await api.removerDoPipeline(numeroControle);
    } catch (err) {
      setErro(err.message);
      carregar();
    }
  }

  return (
    <div>
      <div className="cabecalho-pagina">
        <div>
          <span className="eyebrow">Negócio</span>
          <h1>Pipeline</h1>
          <div className="contagem">
            {carregando ? "carregando..." : `${itens.length} oportunidade(s) em acompanhamento pela equipe`}
          </div>
        </div>
      </div>

      {erro && <div className="erro-msg">{erro}</div>}

      {carregando && (
        <div className="quadro-pipeline">
          {COLUNAS.map((coluna) => (
            <div key={coluna.valor} className="coluna-pipeline" style={{ borderTopColor: CORES_COLUNA[coluna.tag] }}>
              <div className="coluna-pipeline-titulo">
                <span className="coluna-pipeline-titulo-texto">
                  <span className="coluna-pipeline-dot" style={{ background: CORES_COLUNA[coluna.tag] }} />
                  {coluna.rotulo}
                </span>
                <span className="coluna-pipeline-contagem">···</span>
              </div>
              <div className="coluna-pipeline-cartoes">
                {[0, 1].map((i) => (
                  <div key={i} className="esqueleto-cartao">
                    <div className="esqueleto-linha media" />
                    <div className="esqueleto-linha larga" />
                    <div className="esqueleto-linha curta" />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {!carregando && itens.length === 0 && (
        <div className="estado-vazio">
          <Kanban strokeWidth={1.5} />
          <h3>Nenhuma oportunidade no pipeline ainda</h3>
          <p>Favorite uma licitação na tela "Licitações" (clique na estrela) pra ela entrar aqui automaticamente.</p>
        </div>
      )}

      {!carregando && itens.length > 0 && (
        <div className="pipeline-layout">
          <div className="quadro-pipeline">
            {COLUNAS.map((coluna) => {
              const itensDaColuna = itens.filter((o) => o.status === coluna.valor);
              return (
                <div key={coluna.valor} className="coluna-pipeline" style={{ borderTopColor: CORES_COLUNA[coluna.tag] }}>
                  <div className="coluna-pipeline-titulo">
                    <span className="coluna-pipeline-titulo-texto">
                      <span className="coluna-pipeline-dot" style={{ background: CORES_COLUNA[coluna.tag] }} />
                      {coluna.rotulo}
                    </span>
                    <span className="coluna-pipeline-contagem">{itensDaColuna.length}</span>
                  </div>

                  <div className="coluna-pipeline-cartoes entrada-escalonada">
                    {itensDaColuna.map((o, indice) => {
                      const urgencia = urgenciaPrazo(o.data_encerramento_proposta);
                      return (
                        <div
                          key={o.numero_controle}
                          className={`cartao-pipeline ${saindo[o.numero_controle] ? "saindo" : ""}`}
                          style={{ "--i": indice }}
                        >
                          <div className="cartao-pipeline-topo">
                            <h4>{o.orgao && o.orgao !== "—" ? o.orgao : o.cidade}</h4>
                            <select
                              className={`chip-status ${coluna.tag}`}
                              value={o.status}
                              onChange={(e) => moverStatus(o.numero_controle, e.target.value)}
                              title="Mover para outra etapa"
                            >
                              {COLUNAS.map((c) => (
                                <option key={c.valor} value={c.valor}>
                                  {c.rotulo}
                                </option>
                              ))}
                            </select>
                          </div>

                          <p className="objeto">
                            {o.objeto?.slice(0, 140)}
                            {o.objeto && o.objeto.length > 140 ? "..." : ""}
                          </p>

                          <div className="cartao-pipeline-prazo">
                            <div className="cartao-pipeline-prazo-barra">
                              <div
                                className="cartao-pipeline-prazo-preenchido"
                                style={{ width: `${urgencia.percentual}%`, background: urgencia.cor }}
                              />
                            </div>
                            <span style={{ color: urgencia.cor }}>{urgencia.rotulo}</span>
                          </div>

                          <div className="cartao-pipeline-meta">
                            <span><Wallet size={12} strokeWidth={2} /> {formatarValor(o.valor_estimado)}</span>
                            <span><Clock size={12} strokeWidth={2} /> {formatarDataHora(o.data_encerramento_proposta)}</span>
                          </div>

                          <div className="cartao-pipeline-rodape">
                            {o.atualizado_por_email ? (
                              <span className="cartao-pipeline-avatar" title={`Atualizado por ${o.atualizado_por_email}`}>
                                {iniciais(o.atualizado_por_email)}
                              </span>
                            ) : <span />}
                            <div className="cartao-pipeline-rodape-acoes">
                              {o.link_edital && (
                                <a
                                  href={o.link_edital}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="link-edital"
                                  title="Ver edital no PNCP"
                                  aria-label="Ver edital no PNCP"
                                >
                                  <ArrowUpRight size={13} strokeWidth={2.2} />
                                </a>
                              )}
                              <button
                                type="button"
                                className="cartao-pipeline-remover"
                                title="Remover do pipeline"
                                aria-label="Remover do pipeline"
                                onClick={() => remover(o.numero_controle)}
                              >
                                <Trash2 size={13} strokeWidth={2} />
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>

          <aside className="pipeline-resumo">
            <div className="pipeline-resumo-card pipeline-resumo-anel-card">
              <span className="pipeline-resumo-titulo">Taxa de conversão</span>
              <div className="pipeline-resumo-anel-wrap">
                <AnelProgresso percentual={anelPronto ? stats.taxaConversao ?? 0 : 0} />
                <div className="pipeline-resumo-anel-texto">
                  <strong>{stats.taxaConversao === null ? "—" : <><NumeroAnimado valor={stats.taxaConversao} />%</>}</strong>
                  <span>{stats.decididas === 0 ? "sem decisões ainda" : <>{stats.porStatus.ganhou} de {stats.decididas} decididas</>}</span>
                </div>
              </div>
            </div>

            <div className="pipeline-resumo-card pipeline-resumo-stats">
              <div className="pipeline-resumo-stat">
                <span className="pipeline-resumo-stat-rotulo">Total</span>
                <span className="pipeline-resumo-stat-valor"><NumeroAnimado valor={stats.total} /></span>
              </div>
              <div className="pipeline-resumo-stat">
                <span className="pipeline-resumo-stat-rotulo">Em andamento</span>
                <span className="pipeline-resumo-stat-valor"><NumeroAnimado valor={stats.emAndamento} /></span>
              </div>
              <div className="pipeline-resumo-stat">
                <span className="pipeline-resumo-stat-rotulo">Ganhou</span>
                <span className="pipeline-resumo-stat-valor cor-verde"><NumeroAnimado valor={stats.porStatus.ganhou} /></span>
              </div>
              <div className="pipeline-resumo-stat">
                <span className="pipeline-resumo-stat-rotulo">Perdeu</span>
                <span className="pipeline-resumo-stat-valor cor-terracota"><NumeroAnimado valor={stats.porStatus.perdeu} /></span>
              </div>
            </div>

            <div className="pipeline-resumo-card pipeline-resumo-atividade">
              <span className="pipeline-resumo-titulo">Atualizações recentes</span>
              {recentes.length === 0 ? (
                <p className="pipeline-resumo-atividade-vazio">Nenhuma movimentação ainda.</p>
              ) : (
                <ul>
                  {recentes.map((o) => (
                    <li key={o.numero_controle}>
                      <span className="pipeline-resumo-atividade-dot" style={{ background: CORES_COLUNA[tagDoStatus(o.status)] }} />
                      <div className="pipeline-resumo-atividade-texto">
                        <strong>{o.orgao && o.orgao !== "—" ? o.orgao : o.cidade}</strong>
                        <span>movido para {ROTULOS[o.status]} · {tempoRelativo(o.status_atualizado_em)}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
