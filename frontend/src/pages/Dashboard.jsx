import { useEffect, useRef, useState } from "react";
import { Search, SlidersHorizontal, ChevronLeft, ChevronRight, Download, ChevronDown } from "lucide-react";
import { api } from "../api";
import CartaoLicitacao from "../components/CartaoLicitacao";

const FORMATOS_EXPORTACAO = [
  { valor: "csv", rotulo: "CSV" },
  { valor: "xlsx", rotulo: "Excel (.xlsx)" },
  { valor: "pdf", rotulo: "PDF" },
];

const POR_PAGINA = 20;

export default function Dashboard() {
  const [criterios, setCriterios] = useState([]);
  const [criterioSelecionado, setCriterioSelecionado] = useState("todos");
  const [licitacoes, setLicitacoes] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  const [busca, setBusca] = useState("");
  const [filtrosAbertos, setFiltrosAbertos] = useState(false);
  const [uf, setUf] = useState("");
  const [orgao, setOrgao] = useState("");
  const [valorMin, setValorMin] = useState("");
  const [valorMax, setValorMax] = useState("");
  const [dataDe, setDataDe] = useState("");
  const [dataAte, setDataAte] = useState("");

  const [pagina, setPagina] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPaginas, setTotalPaginas] = useState(1);

  const [menuExportarAberto, setMenuExportarAberto] = useState(false);
  const [exportando, setExportando] = useState(false);
  const refExportar = useRef(null);

  useEffect(() => {
    api.listarCriterios().then(setCriterios).catch(() => {});
  }, []);

  useEffect(() => {
    function aoClicarFora(e) {
      if (refExportar.current && !refExportar.current.contains(e.target)) setMenuExportarAberto(false);
    }
    if (menuExportarAberto) document.addEventListener("mousedown", aoClicarFora);
    return () => document.removeEventListener("mousedown", aoClicarFora);
  }, [menuExportarAberto]);

  function filtrosAtuais() {
    return {
      criterioId: criterioSelecionado === "todos" ? undefined : criterioSelecionado,
      busca: busca.trim() || undefined,
      uf: uf || undefined,
      orgao: orgao || undefined,
      valorMin: valorMin || undefined,
      valorMax: valorMax || undefined,
      dataDe: dataDe || undefined,
      dataAte: dataAte || undefined,
    };
  }

  async function exportar(formato) {
    setMenuExportarAberto(false);
    setErro("");
    setExportando(true);
    try {
      await api.exportarLicitacoes(filtrosAtuais(), formato);
    } catch (err) {
      setErro(err.message);
    } finally {
      setExportando(false);
    }
  }

  function buscarLicitacoes(paginaAlvo = 1) {
    setCarregando(true);
    setErro("");
    api
      .listarLicitacoes({
        ...filtrosAtuais(),
        pagina: paginaAlvo,
        porPagina: POR_PAGINA,
      })
      .then((resultado) => {
        setLicitacoes(resultado.itens);
        setTotal(resultado.total);
        setTotalPaginas(resultado.total_paginas);
        setPagina(resultado.pagina);
      })
      .catch((err) => setErro(err.message))
      .finally(() => setCarregando(false));
  }

  useEffect(() => {
    buscarLicitacoes(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [criterioSelecionado]);

  function aoSubmeterBusca(e) {
    e.preventDefault();
    buscarLicitacoes(1); // toda nova busca volta pra página 1
  }

  function limparFiltros() {
    setBusca("");
    setUf("");
    setOrgao("");
    setValorMin("");
    setValorMax("");
    setDataDe("");
    setDataAte("");
    setTimeout(() => buscarLicitacoes(1), 0);
  }

  function irParaPagina(novaPagina) {
    if (novaPagina < 1 || novaPagina > totalPaginas) return;
    buscarLicitacoes(novaPagina);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const temFiltroAvancadoAtivo = uf || orgao || valorMin || valorMax || dataDe || dataAte;

  return (
    <div>
      <div className="cabecalho-pagina">
        <div>
          <span className="eyebrow">Painel</span>
          <h1>Licitações</h1>
          <div className="contagem">
            {carregando
              ? "carregando..."
              : `${total} licitação(ões) encontrada(s)${totalPaginas > 1 ? ` · página ${pagina} de ${totalPaginas}` : ""}`}
          </div>
        </div>

        {criterios.length > 0 && (
          <div className="seletor-criterio">
            <label htmlFor="criterio" style={{ fontSize: 13, color: "var(--slate)" }}>
              Critério
            </label>
            <select
              id="criterio"
              value={criterioSelecionado}
              onChange={(e) => setCriterioSelecionado(e.target.value)}
            >
              <option value="todos">Todos os critérios</option>
              {criterios.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nome}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      <form onSubmit={aoSubmeterBusca} style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", gap: 8 }}>
          <div style={{ position: "relative", flex: 1 }}>
            <Search
              size={16}
              strokeWidth={2}
              style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--slate-dim)" }}
            />
            <input
              type="text"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Buscar por palavra (funciona com ou sem critério selecionado)..."
              style={{
                width: "100%", fontFamily: "var(--fonte-ui)", fontSize: 14, padding: "10px 12px 10px 36px",
                border: "1.5px solid var(--slate-line)", borderRadius: "var(--radius)",
              }}
            />
          </div>
          <button type="submit" className="botao primario" disabled={carregando}>
            {carregando ? "Buscando..." : "Buscar"}
          </button>
          <button type="button" className="botao fantasma" onClick={() => setFiltrosAbertos(!filtrosAbertos)}>
            <SlidersHorizontal size={15} strokeWidth={2} />
            {filtrosAbertos ? "Ocultar filtros" : "Filtros avançados"}
          </button>

          <div className="navbar-item-wrap" ref={refExportar}>
            <button
              type="button"
              className="botao fantasma"
              disabled={exportando || licitacoes.length === 0}
              onClick={() => setMenuExportarAberto((v) => !v)}
            >
              {exportando ? <span className="spinner-inline" /> : <Download size={15} strokeWidth={2} />}
              {exportando ? "Exportando..." : "Exportar"}
              <ChevronDown size={13} strokeWidth={2.2} />
            </button>

            {menuExportarAberto && (
              <div className="painel-flutuante painel-exportar">
                {FORMATOS_EXPORTACAO.map((f) => (
                  <button key={f.valor} type="button" onClick={() => exportar(f.valor)}>
                    {f.rotulo}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {filtrosAbertos && (
          <div className="card-formulario" style={{ marginTop: 12, maxWidth: "none" }}>
            <div className="linha-dupla">
              <div className="campo">
                <label>UF</label>
                <input type="text" value={uf} onChange={(e) => setUf(e.target.value.toUpperCase())} placeholder="Ex: MA" maxLength={2} />
              </div>
              <div className="campo">
                <label>Órgão</label>
                <input type="text" value={orgao} onChange={(e) => setOrgao(e.target.value)} placeholder="Nome do órgão" />
              </div>
            </div>
            <div className="linha-dupla">
              <div className="campo">
                <label>Valor mínimo (R$)</label>
                <input type="number" min="0" value={valorMin} onChange={(e) => setValorMin(e.target.value)} />
              </div>
              <div className="campo">
                <label>Valor máximo (R$)</label>
                <input type="number" min="0" value={valorMax} onChange={(e) => setValorMax(e.target.value)} />
              </div>
            </div>
            <div className="linha-dupla">
              <div className="campo">
                <label>Prazo de proposta de</label>
                <input type="date" value={dataDe} onChange={(e) => setDataDe(e.target.value)} />
              </div>
              <div className="campo">
                <label>até</label>
                <input type="date" value={dataAte} onChange={(e) => setDataAte(e.target.value)} />
              </div>
            </div>
            <div className="acoes-formulario">
              <button type="submit" className="botao primario">Aplicar filtros</button>
              <button type="button" className="botao fantasma" onClick={limparFiltros}>Limpar tudo</button>
            </div>
          </div>
        )}
      </form>

      {erro && <div className="erro-msg">{erro}</div>}

      {criterios.length === 0 && !busca && !temFiltroAvancadoAtivo && !carregando && licitacoes.length === 0 && (
        <div className="estado-vazio">
          <Search strokeWidth={1.5} />
          <h3>Nenhum critério configurado ainda</h3>
          <p>
            Vá até "Meus critérios" no menu e configure o que você procura — ou use a busca
            acima pra pesquisar livremente, sem precisar de critério.
          </p>
        </div>
      )}

      {!carregando && licitacoes.length === 0 && (criterios.length > 0 || busca || temFiltroAvancadoAtivo) && (
        <div className="estado-vazio">
          <Search strokeWidth={1.5} />
          <h3>Nenhuma licitação encontrada</h3>
          <p>Tente ajustar a busca, os filtros, ou o critério selecionado.</p>
        </div>
      )}

      {carregando && (
        <div className="grade-licitacoes">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="esqueleto-cartao">
              <div className="esqueleto-linha curta" />
              <div className="esqueleto-linha media" />
              <div className="esqueleto-linha larga" />
              <div className="esqueleto-linha larga" />
            </div>
          ))}
        </div>
      )}

      {!carregando && licitacoes.length > 0 && (
        <>
          <div className="grade-licitacoes entrada-escalonada">
            {licitacoes.map((lic, indice) => (
              <CartaoLicitacao key={lic.numero_controle} lic={lic} estilo={{ "--i": indice }} />
            ))}
          </div>

          {totalPaginas > 1 && (
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 12, marginTop: 28 }}>
              <button className="botao fantasma" disabled={pagina <= 1} onClick={() => irParaPagina(pagina - 1)}>
                <ChevronLeft size={15} strokeWidth={2.2} /> Anterior
              </button>
              <span style={{ fontFamily: "var(--fonte-mono)", fontSize: 13, color: "var(--slate)" }}>
                página {pagina} de {totalPaginas}
              </span>
              <button className="botao fantasma" disabled={pagina >= totalPaginas} onClick={() => irParaPagina(pagina + 1)}>
                Próxima <ChevronRight size={15} strokeWidth={2.2} />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}