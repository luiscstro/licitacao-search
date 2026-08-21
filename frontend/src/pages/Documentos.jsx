import { useEffect, useState } from "react";
import {
  Building2, RefreshCw, Upload, Download, Trash2, Pencil, History, X, FolderOpen,
} from "lucide-react";
import { api } from "../api";
import Carimbo from "../components/Carimbo";
import NumeroAnimado from "../components/NumeroAnimado";

const CATEGORIAS = [
  { chave: "juridica", rotulo: "Habilitação Jurídica" },
  { chave: "fiscal", rotulo: "Regularidade Fiscal" },
  { chave: "trabalhista", rotulo: "Regularidade Trabalhista" },
  { chave: "economico_financeira", rotulo: "Qualificação Econômico-Financeira" },
  { chave: "tecnica", rotulo: "Qualificação Técnica" },
  { chave: "outra", rotulo: "Outros" },
];

const SUGESTOES_NOME = [
  "Certidão Negativa de Débitos Federais (Receita/PGFN)",
  "Certidão de Regularidade do FGTS",
  "Certidão Negativa de Débitos Trabalhistas (CNDT)",
  "Certidão Negativa de Débitos Estaduais",
  "Certidão Negativa de Dívida Ativa Estadual",
  "Certidão Negativa Municipal",
  "Certidão Negativa de Falência e Recuperação Judicial",
  "Alvará de Funcionamento",
  "Certidão Simplificada — Junta Comercial",
  "Contrato Social",
];

const STATUS_INFO = {
  valida: { rotulo: "válido", cor: "verde" },
  vencendo: { rotulo: "vencendo", cor: "dourado" },
  vencida: { rotulo: "vencido", cor: "terracota" },
  sem_data: { rotulo: "sem data de validade", cor: "neutro" },
};

const EMPRESA_VAZIA = {
  nome: "", cnpj: "", inscricao_estadual: "", inscricao_municipal: "",
  endereco_logradouro: "", endereco_numero: "", endereco_complemento: "", endereco_bairro: "",
  endereco_cidade: "", endereco_uf: "", endereco_cep: "",
  representante_nome: "", representante_cpf: "", representante_cargo: "",
  representante_email: "", representante_telefone: "",
};

function formatarData(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("pt-BR");
}

function PainelUpload({ categoriaInicial, documento, aoFechar, aoSalvar }) {
  const [nome, setNome] = useState(documento?.nome || "");
  const [categoria, setCategoria] = useState(documento?.categoria || categoriaInicial || "outra");
  const [dataEmissao, setDataEmissao] = useState("");
  const [dataValidade, setDataValidade] = useState("");
  const [arquivo, setArquivo] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  const substituindo = !!documento;

  async function salvar(e) {
    e.preventDefault();
    if (!arquivo) {
      setErro("Selecione um arquivo.");
      return;
    }
    setSalvando(true);
    setErro("");
    try {
      const formData = new FormData();
      formData.append("file", arquivo);
      if (dataEmissao) formData.append("data_emissao", dataEmissao);
      if (dataValidade) formData.append("data_validade", dataValidade);

      if (substituindo) {
        await api.substituirDocumento(documento.id, formData);
      } else {
        formData.append("categoria", categoria);
        formData.append("nome", nome);
        await api.enviarDocumento(formData);
      }
      aoSalvar();
    } catch (err) {
      setErro(err.message);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="painel-overlay" onClick={aoFechar}>
      <div className="painel-modal card-formulario" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
          <h2 style={{ marginBottom: 0 }}>{substituindo ? `Substituir: ${documento.nome}` : "Adicionar documento"}</h2>
          <button className="botao fantasma" onClick={aoFechar} style={{ padding: 8, borderRadius: "50%", width: 32, height: 32 }} aria-label="Fechar">
            <X size={15} strokeWidth={2.2} />
          </button>
        </div>

        {erro && <div className="erro-msg">{erro}</div>}

        <form onSubmit={salvar}>
          {!substituindo && (
            <>
              <div className="campo">
                <label htmlFor="doc-nome">Nome do documento</label>
                <input
                  id="doc-nome"
                  type="text"
                  list="sugestoes-nome-documento"
                  required
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  placeholder="Ex: Certidão Negativa de Débitos Estaduais"
                />
                <datalist id="sugestoes-nome-documento">
                  {SUGESTOES_NOME.map((s) => <option key={s} value={s} />)}
                </datalist>
              </div>

              <div className="campo">
                <label htmlFor="doc-categoria">Categoria</label>
                <select id="doc-categoria" value={categoria} onChange={(e) => setCategoria(e.target.value)}>
                  {CATEGORIAS.map((c) => <option key={c.chave} value={c.chave}>{c.rotulo}</option>)}
                </select>
              </div>
            </>
          )}

          <div className="linha-dupla">
            <div className="campo">
              <label htmlFor="doc-emissao">Data de emissão (opcional)</label>
              <input id="doc-emissao" type="date" value={dataEmissao} onChange={(e) => setDataEmissao(e.target.value)} />
            </div>
            <div className="campo">
              <label htmlFor="doc-validade">Data de validade (opcional)</label>
              <input id="doc-validade" type="date" value={dataValidade} onChange={(e) => setDataValidade(e.target.value)} />
            </div>
          </div>

          <div className="campo">
            <label htmlFor="doc-arquivo">Arquivo (PDF, imagem ou Word — até 15MB)</label>
            <input
              id="doc-arquivo"
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
              required
              onChange={(e) => setArquivo(e.target.files?.[0] || null)}
            />
          </div>

          <div className="acoes-formulario">
            <button type="submit" className="botao primario" disabled={salvando}>
              {salvando ? "Enviando..." : "Salvar"}
            </button>
            <button type="button" className="botao fantasma" onClick={aoFechar}>Cancelar</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function PainelHistorico({ documento, aoFechar }) {
  const [historico, setHistorico] = useState([]);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    api.historicoDocumento(documento.id).then(setHistorico).finally(() => setCarregando(false));
  }, [documento.id]);

  return (
    <div className="painel-overlay" onClick={aoFechar}>
      <div className="painel-modal card-formulario" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
          <h2 style={{ marginBottom: 0 }}>Histórico: {documento.nome}</h2>
          <button className="botao fantasma" onClick={aoFechar} style={{ padding: 8, borderRadius: "50%", width: 32, height: 32 }} aria-label="Fechar">
            <X size={15} strokeWidth={2.2} />
          </button>
        </div>

        {carregando && <div className="carregando">Carregando...</div>}
        {!carregando && historico.length === 0 && <p className="ajuda">Ainda não houve substituições desse documento.</p>}

        <div style={{ display: "flex", flexDirection: "column", gap: 10, overflowY: "auto" }}>
          {historico.map((h) => (
            <div key={h.id} style={{ borderBottom: "1px dashed var(--linha)", paddingBottom: 8 }}>
              <div style={{ fontSize: 13.5, fontWeight: 600, color: "var(--ink)" }}>{h.nome_arquivo_original}</div>
              <div style={{ fontSize: 12.5, color: "var(--slate)", marginTop: 2 }}>
                validade anterior: {formatarData(h.data_validade)}
              </div>
              <div style={{ fontSize: 11, color: "var(--slate-dim)", marginTop: 4, fontFamily: "var(--fonte-mono)" }}>
                substituído em {new Date(h.substituido_em).toLocaleString("pt-BR")} por {h.substituido_por_email}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function Documentos({ perfil }) {
  const [empresa, setEmpresa] = useState(null);
  const [documentos, setDocumentos] = useState([]);
  const [indicadores, setIndicadores] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [sincronizando, setSincronizando] = useState(false);

  const [editandoEmpresa, setEditandoEmpresa] = useState(false);
  const [formEmpresa, setFormEmpresa] = useState(EMPRESA_VAZIA);
  const [salvandoEmpresa, setSalvandoEmpresa] = useState(false);

  const [uploadCategoria, setUploadCategoria] = useState(null);
  const [documentoSubstituindo, setDocumentoSubstituindo] = useState(null);
  const [documentoHistorico, setDocumentoHistorico] = useState(null);

  const souOwner = perfil?.papel === "owner";

  function carregar() {
    setCarregando(true);
    setErro("");
    Promise.all([api.minhaEmpresa(), api.listarDocumentos(), api.indicadoresDocumentos()])
      .then(([emp, docs, ind]) => {
        setEmpresa(emp);
        setDocumentos(docs);
        setIndicadores(ind);
      })
      .catch((err) => setErro(err.message))
      .finally(() => setCarregando(false));
  }

  useEffect(() => {
    carregar();
  }, []);

  function abrirEdicaoEmpresa() {
    setFormEmpresa({
      nome: empresa.nome || "",
      cnpj: empresa.cnpj || "",
      inscricao_estadual: empresa.inscricao_estadual || "",
      inscricao_municipal: empresa.inscricao_municipal || "",
      endereco_logradouro: empresa.endereco_logradouro || "",
      endereco_numero: empresa.endereco_numero || "",
      endereco_complemento: empresa.endereco_complemento || "",
      endereco_bairro: empresa.endereco_bairro || "",
      endereco_cidade: empresa.endereco_cidade || "",
      endereco_uf: empresa.endereco_uf || "",
      endereco_cep: empresa.endereco_cep || "",
      representante_nome: empresa.representante_nome || "",
      representante_cpf: empresa.representante_cpf || "",
      representante_cargo: empresa.representante_cargo || "",
      representante_email: empresa.representante_email || "",
      representante_telefone: empresa.representante_telefone || "",
    });
    setEditandoEmpresa(true);
    setErro("");
  }

  async function salvarEmpresa(e) {
    e.preventDefault();
    setSalvandoEmpresa(true);
    setErro("");
    try {
      const atualizada = await api.atualizarEmpresa(formEmpresa);
      setEmpresa(atualizada);
      setEditandoEmpresa(false);
    } catch (err) {
      setErro(err.message);
    } finally {
      setSalvandoEmpresa(false);
    }
  }

  async function sincronizarCnpj() {
    setSincronizando(true);
    setErro("");
    setSucesso("");
    try {
      const atualizada = await api.sincronizarCnpj();
      setEmpresa(atualizada);
      setSucesso("Dados sincronizados com a Receita Federal.");
      setTimeout(() => setSucesso(""), 4000);
    } catch (err) {
      setErro(err.message);
    } finally {
      setSincronizando(false);
    }
  }

  async function apagar(documento) {
    if (!confirm(`Apagar "${documento.nome}"? Isso remove o arquivo e o histórico dele.`)) return;
    try {
      await api.removerDocumento(documento.id);
      carregar();
    } catch (err) {
      setErro(err.message);
    }
  }

  function contarPorStatus(status) {
    return indicadores?.por_status.find((s) => s.status === status)?.quantidade || 0;
  }

  return (
    <div>
      <div className="cabecalho-pagina">
        <div>
          <span className="eyebrow">Habilitação</span>
          <h1>Documentos e Certidões</h1>
          <div className="contagem">
            {carregando ? "carregando..." : `${documentos.length} documento(s) cadastrado(s)`}
          </div>
        </div>
      </div>

      {erro && <div className="erro-msg">{erro}</div>}
      {sucesso && <div className="sucesso-msg">{sucesso}</div>}

      {carregando && (
        <div className="grade-indicadores">
          {[0, 1, 2].map((i) => (
            <div key={i} className="esqueleto-cartao">
              <div className="esqueleto-linha media" />
              <div className="esqueleto-linha larga" />
              <div className="esqueleto-linha curta" />
            </div>
          ))}
        </div>
      )}

      {!carregando && indicadores && (
        <div className="grade-resumo-indicadores">
          <div className="pastilha-resumo">
            <span className="pastilha-resumo-rotulo">Válidos</span>
            <span className="pastilha-resumo-valor"><NumeroAnimado valor={contarPorStatus("valida")} /></span>
          </div>
          <div className="pastilha-resumo">
            <span className="pastilha-resumo-rotulo">Vencendo (30 dias)</span>
            <span className="pastilha-resumo-valor"><NumeroAnimado valor={contarPorStatus("vencendo")} /></span>
          </div>
          <div className="pastilha-resumo">
            <span className="pastilha-resumo-rotulo">Vencidos</span>
            <span className="pastilha-resumo-valor"><NumeroAnimado valor={contarPorStatus("vencida")} /></span>
          </div>
        </div>
      )}

      {!carregando && empresa && !editandoEmpresa && (
        <div className="card-formulario" style={{ marginBottom: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
            <div>
              <h2 style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Building2 size={17} strokeWidth={2} /> Dados da empresa
              </h2>
              <div style={{ fontSize: 14, color: "var(--slate)", marginTop: 4 }}>{empresa.nome}</div>
              <div style={{ fontSize: 13, color: "var(--slate)", marginTop: 2, fontFamily: "var(--fonte-mono)" }}>
                CNPJ: {empresa.cnpj || "não cadastrado"}
              </div>
              {empresa.situacao_cadastral && (
                <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 8 }}>
                  <Carimbo cor={empresa.situacao_cadastral === "ATIVA" ? "verde" : "terracota"}>
                    situação: {empresa.situacao_cadastral.toLowerCase()}
                  </Carimbo>
                  {empresa.cnpj_sincronizado_em && (
                    <span style={{ fontSize: 11.5, color: "var(--slate-dim)" }}>
                      sincronizado em {new Date(empresa.cnpj_sincronizado_em).toLocaleString("pt-BR")}
                    </span>
                  )}
                </div>
              )}
              {(empresa.endereco_cidade || empresa.endereco_uf) && (
                <div style={{ fontSize: 13, color: "var(--slate)", marginTop: 6 }}>
                  {[empresa.endereco_logradouro, empresa.endereco_numero, empresa.endereco_cidade, empresa.endereco_uf].filter(Boolean).join(", ")}
                </div>
              )}
            </div>
            {souOwner && (
              <div style={{ display: "flex", flexDirection: "column", gap: 8, flexShrink: 0 }}>
                <button className="botao fantasma" onClick={abrirEdicaoEmpresa}>
                  <Pencil size={13} strokeWidth={2.1} /> Editar
                </button>
                <button className="botao fantasma" onClick={sincronizarCnpj} disabled={sincronizando || !empresa.cnpj}>
                  <RefreshCw size={13} strokeWidth={2.1} /> {sincronizando ? "Sincronizando..." : "Sincronizar CNPJ"}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {editandoEmpresa && (
        <div className="card-formulario" style={{ marginBottom: 24 }}>
          <h2>Editar dados da empresa</h2>
          <form onSubmit={salvarEmpresa}>
            <div className="campo">
              <label htmlFor="emp-nome">Razão social</label>
              <input id="emp-nome" type="text" required value={formEmpresa.nome} onChange={(e) => setFormEmpresa({ ...formEmpresa, nome: e.target.value })} />
            </div>
            <div className="linha-dupla">
              <div className="campo">
                <label htmlFor="emp-cnpj">CNPJ</label>
                <input id="emp-cnpj" type="text" value={formEmpresa.cnpj} onChange={(e) => setFormEmpresa({ ...formEmpresa, cnpj: e.target.value })} placeholder="00000000000000" />
              </div>
              <div className="campo">
                <label htmlFor="emp-ie">Inscrição Estadual</label>
                <input id="emp-ie" type="text" value={formEmpresa.inscricao_estadual} onChange={(e) => setFormEmpresa({ ...formEmpresa, inscricao_estadual: e.target.value })} />
              </div>
            </div>
            <div className="linha-dupla">
              <div className="campo">
                <label htmlFor="emp-im">Inscrição Municipal</label>
                <input id="emp-im" type="text" value={formEmpresa.inscricao_municipal} onChange={(e) => setFormEmpresa({ ...formEmpresa, inscricao_municipal: e.target.value })} />
              </div>
              <div className="campo">
                <label htmlFor="emp-cep">CEP</label>
                <input id="emp-cep" type="text" value={formEmpresa.endereco_cep} onChange={(e) => setFormEmpresa({ ...formEmpresa, endereco_cep: e.target.value })} />
              </div>
            </div>
            <div className="linha-dupla">
              <div className="campo">
                <label htmlFor="emp-logradouro">Logradouro</label>
                <input id="emp-logradouro" type="text" value={formEmpresa.endereco_logradouro} onChange={(e) => setFormEmpresa({ ...formEmpresa, endereco_logradouro: e.target.value })} />
              </div>
              <div className="campo">
                <label htmlFor="emp-numero">Número</label>
                <input id="emp-numero" type="text" value={formEmpresa.endereco_numero} onChange={(e) => setFormEmpresa({ ...formEmpresa, endereco_numero: e.target.value })} />
              </div>
            </div>
            <div className="linha-dupla">
              <div className="campo">
                <label htmlFor="emp-bairro">Bairro</label>
                <input id="emp-bairro" type="text" value={formEmpresa.endereco_bairro} onChange={(e) => setFormEmpresa({ ...formEmpresa, endereco_bairro: e.target.value })} />
              </div>
              <div className="campo">
                <label htmlFor="emp-complemento">Complemento</label>
                <input id="emp-complemento" type="text" value={formEmpresa.endereco_complemento} onChange={(e) => setFormEmpresa({ ...formEmpresa, endereco_complemento: e.target.value })} />
              </div>
            </div>
            <div className="linha-dupla">
              <div className="campo">
                <label htmlFor="emp-cidade">Cidade</label>
                <input id="emp-cidade" type="text" value={formEmpresa.endereco_cidade} onChange={(e) => setFormEmpresa({ ...formEmpresa, endereco_cidade: e.target.value })} />
              </div>
              <div className="campo">
                <label htmlFor="emp-uf">UF</label>
                <input id="emp-uf" type="text" maxLength={2} value={formEmpresa.endereco_uf} onChange={(e) => setFormEmpresa({ ...formEmpresa, endereco_uf: e.target.value.toUpperCase() })} />
              </div>
            </div>
            <div className="linha-dupla">
              <div className="campo">
                <label htmlFor="emp-rep-nome">Representante legal</label>
                <input id="emp-rep-nome" type="text" value={formEmpresa.representante_nome} onChange={(e) => setFormEmpresa({ ...formEmpresa, representante_nome: e.target.value })} />
              </div>
              <div className="campo">
                <label htmlFor="emp-rep-cpf">CPF do representante</label>
                <input id="emp-rep-cpf" type="text" value={formEmpresa.representante_cpf} onChange={(e) => setFormEmpresa({ ...formEmpresa, representante_cpf: e.target.value })} />
              </div>
            </div>
            <div className="linha-dupla">
              <div className="campo">
                <label htmlFor="emp-rep-cargo">Cargo</label>
                <input id="emp-rep-cargo" type="text" value={formEmpresa.representante_cargo} onChange={(e) => setFormEmpresa({ ...formEmpresa, representante_cargo: e.target.value })} />
              </div>
              <div className="campo">
                <label htmlFor="emp-rep-telefone">Telefone</label>
                <input id="emp-rep-telefone" type="text" value={formEmpresa.representante_telefone} onChange={(e) => setFormEmpresa({ ...formEmpresa, representante_telefone: e.target.value })} />
              </div>
            </div>
            <div className="campo">
              <label htmlFor="emp-rep-email">E-mail do representante</label>
              <input id="emp-rep-email" type="email" value={formEmpresa.representante_email} onChange={(e) => setFormEmpresa({ ...formEmpresa, representante_email: e.target.value })} />
            </div>

            <div className="acoes-formulario">
              <button type="submit" className="botao primario" disabled={salvandoEmpresa}>
                {salvandoEmpresa ? "Salvando..." : "Salvar dados"}
              </button>
              <button type="button" className="botao fantasma" onClick={() => setEditandoEmpresa(false)}>Cancelar</button>
            </div>
          </form>
        </div>
      )}

      {!carregando && CATEGORIAS.map((cat) => {
        const docsDaCategoria = documentos.filter((d) => d.categoria === cat.chave);
        return (
          <section key={cat.chave} style={{ marginBottom: 28 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <h2 className="painel-grupo-titulo" style={{ margin: 0 }}>
                {cat.rotulo} <span style={{ color: "var(--slate-dim)", fontWeight: 400 }}>({docsDaCategoria.length})</span>
              </h2>
              <button className="botao fantasma" onClick={() => setUploadCategoria(cat.chave)}>
                <Upload size={13} strokeWidth={2.1} /> Adicionar
              </button>
            </div>

            {docsDaCategoria.length === 0 && (
              <p className="ajuda">Nenhum documento nessa categoria ainda.</p>
            )}

            <div className="lista-criterios entrada-escalonada">
              {docsDaCategoria.map((doc, indice) => {
                const info = STATUS_INFO[doc.status] || STATUS_INFO.sem_data;
                return (
                  <div className="item-criterio" key={doc.id} style={{ "--i": indice }}>
                    <div>
                      <div className="nome-criterio">{doc.nome}</div>
                      <div className="resumo-criterio">
                        <Carimbo cor={info.cor}>{info.rotulo}</Carimbo>
                        {doc.data_validade && <span style={{ marginLeft: 8 }}>validade: {formatarData(doc.data_validade)}</span>}
                        {doc.data_emissao && <span style={{ marginLeft: 8 }}>emitido: {formatarData(doc.data_emissao)}</span>}
                      </div>
                    </div>
                    <div className="acoes">
                      <button className="botao fantasma" onClick={() => api.baixarArquivoDocumento(doc.id).catch((err) => setErro(err.message))} title="Baixar">
                        <Download size={13} strokeWidth={2.1} />
                      </button>
                      <button className="botao fantasma" onClick={() => setDocumentoHistorico(doc)} title="Histórico">
                        <History size={13} strokeWidth={2.1} />
                      </button>
                      <button className="botao fantasma" onClick={() => setDocumentoSubstituindo(doc)} title="Substituir arquivo">
                        <Upload size={13} strokeWidth={2.1} />
                      </button>
                      <button className="botao perigo" onClick={() => apagar(doc)} title="Apagar">
                        <Trash2 size={13} strokeWidth={2.1} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        );
      })}

      {!carregando && documentos.length === 0 && (
        <div className="estado-vazio">
          <FolderOpen strokeWidth={1.5} />
          <h3>Nenhum documento cadastrado ainda</h3>
          <p>Use o botão "Adicionar" em qualquer categoria acima pra começar a centralizar suas certidões e documentos de habilitação.</p>
        </div>
      )}

      {uploadCategoria && (
        <PainelUpload
          categoriaInicial={uploadCategoria}
          aoFechar={() => setUploadCategoria(null)}
          aoSalvar={() => { setUploadCategoria(null); carregar(); }}
        />
      )}
      {documentoSubstituindo && (
        <PainelUpload
          documento={documentoSubstituindo}
          aoFechar={() => setDocumentoSubstituindo(null)}
          aoSalvar={() => { setDocumentoSubstituindo(null); carregar(); }}
        />
      )}
      {documentoHistorico && (
        <PainelHistorico documento={documentoHistorico} aoFechar={() => setDocumentoHistorico(null)} />
      )}
    </div>
  );
}
