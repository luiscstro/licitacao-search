import { useEffect, useState } from "react";
import { api } from "../api";
import CartaoLicitacao from "../components/CartaoLicitacao";

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

  useEffect(() => {
    api.listarCriterios().then(setCriterios).catch(() => {});
  }, []);

  function buscarLicitacoes() {
    setCarregando(true);
    setErro("");
    const idFiltro = criterioSelecionado === "todos" ? undefined : criterioSelecionado;
    const buscaLimpa = busca.trim();
    api
      .listarLicitacoes({
        criterioId: idFiltro,
        busca: buscaLimpa || undefined,
        uf: uf || undefined,
        orgao: orgao || undefined,
        valorMin: valorMin || undefined,
        valorMax: valorMax || undefined,
        dataDe: dataDe || undefined,
        dataAte: dataAte || undefined,
      })
      .then((resultado) => {
        setLicitacoes(resultado);
        console.log(`Busca retornou ${resultado.length} licitação(ões)`, resultado);
      })
      .catch((err) => setErro(err.message))
      .finally(() => setCarregando(false));
  }

  useEffect(() => {
    buscarLicitacoes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [criterioSelecionado]);

  function aoSubmeterBusca(e) {
    e.preventDefault();
    buscarLicitacoes();
  }

  function limparFiltros() {
    setBusca("");
    setUf("");
    setOrgao("");
    setValorMin("");
    setValorMax("");
    setDataDe("");
    setDataAte("");
    setTimeout(buscarLicitacoes, 0);
  }

  const temFiltroAvancadoAtivo = uf || orgao || valorMin || valorMax || dataDe || dataAte;

  return (
    <div>
      <div className="cabecalho-pagina">
        <div>
          <h1>Licitações</h1>
          <div className="contagem">
            {carregando ? "carregando..." : `${licitacoes.length} licitação(ões) encontrada(s)`}
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
          <input
            type="text"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar por palavra (funciona com ou sem critério selecionado)..."
            style={{
              flex: 1, fontFamily: "var(--fonte-ui)", fontSize: 14, padding: "10px 12px",
              border: "1.5px solid var(--slate-line)", borderRadius: "var(--radius)",
            }}
          />
          <button type="submit" className="botao primario" disabled={carregando}>
            {carregando ? "Buscando..." : "Buscar"}
          </button>
          <button type="button" className="botao fantasma" onClick={() => setFiltrosAbertos(!filtrosAbertos)}>
            {filtrosAbertos ? "Ocultar filtros" : "Filtros avançados"}
          </button>
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
          <h3>Nenhum critério configurado ainda</h3>
          <p>
            Vá até "Meus critérios" no menu e configure o que você procura — ou use a busca
            acima pra pesquisar livremente, sem precisar de critério.
          </p>
        </div>
      )}

      {!carregando && licitacoes.length === 0 && (criterios.length > 0 || busca || temFiltroAvancadoAtivo) && (
        <div className="estado-vazio">
          <h3>Nenhuma licitação encontrada</h3>
          <p>Tente ajustar a busca, os filtros, ou o critério selecionado.</p>
        </div>
      )}

      {carregando && <div className="carregando">Carregando licitações...</div>}

      {!carregando && licitacoes.length > 0 && (
        <div className="grade-licitacoes">
          {licitacoes.map((lic) => (
            <CartaoLicitacao key={lic.numero_controle} lic={lic} />
          ))}
        </div>
      )}
    </div>
  );
}