import { useEffect, useState } from "react";
import { api } from "../api";
import Carimbo from "../components/Carimbo";

function formatarValor(valor) {
  if (!valor) return "não informado";
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(valor);
}

function diasAte(dataStr) {
  if (!dataStr) return "—";
  const data = new Date(dataStr);
  const hoje = new Date();
  const diffMs = data.setHours(0, 0, 0, 0) - hoje.setHours(0, 0, 0, 0);
  const dias = Math.round(diffMs / 86400000);
  if (dias < 0) return `venceu há ${Math.abs(dias)}d`;
  if (dias === 0) return "hoje";
  return `em ${dias}d`;
}

export default function Dashboard() {
  const [criterios, setCriterios] = useState([]);
  const [criterioSelecionado, setCriterioSelecionado] = useState("todos");
  const [licitacoes, setLicitacoes] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api.listarCriterios().then(setCriterios).catch(() => {});
  }, []);

  useEffect(() => {
    setCarregando(true);
    setErro("");
    const idFiltro = criterioSelecionado === "todos" ? undefined : criterioSelecionado;
    api
      .listarLicitacoes(idFiltro)
      .then(setLicitacoes)
      .catch((err) => setErro(err.message))
      .finally(() => setCarregando(false));
  }, [criterioSelecionado]);

  const urgenteEmDias = (dataStr) => {
    if (!dataStr) return false;
    const data = new Date(dataStr);
    const hoje = new Date();
    const dias = Math.round((data.setHours(0, 0, 0, 0) - hoje.setHours(0, 0, 0, 0)) / 86400000);
    return dias >= 0 && dias <= 3;
  };

  return (
    <div>
      <div className="cabecalho-pagina">
        <div>
          <h1>Licitações</h1>
          <div className="contagem">
            {carregando ? "carregando..." : `${licitacoes.length} licitação(ões) ativa(s)`}
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

      {erro && <div className="erro-msg">{erro}</div>}

      {criterios.length === 0 && !carregando && (
        <div className="estado-vazio">
          <h3>Nenhum critério configurado ainda</h3>
          <p>Vá até "Meus critérios" no menu e configure o que você procura para começar a ver resultados aqui.</p>
        </div>
      )}

      {!carregando && criterios.length > 0 && licitacoes.length === 0 && (
        <div className="estado-vazio">
          <h3>Nenhuma licitação bate com esse critério agora</h3>
          <p>
            O coletor roda diariamente — volte amanhã, ou ajuste o critério em "Meus critérios"
            se ele estiver restritivo demais.
          </p>
        </div>
      )}

      {carregando && <div className="carregando">Carregando licitações...</div>}

      {!carregando && licitacoes.length > 0 && (
        <div className="grade-licitacoes">
          {licitacoes.map((lic) => (
            <div className="cartao-licitacao" key={lic.numero_controle}>
              <div className="topo-cartao">
                <Carimbo cor="dourado">{Math.round(lic.score)} pts</Carimbo>
                {lic.uf && <Carimbo cor="neutro">{lic.uf}</Carimbo>}
                {urgenteEmDias(lic.data_encerramento_proposta) && (
                  <Carimbo cor="terracota">prazo curto</Carimbo>
                )}
                <span className="pontuacao">{lic.modalidade}</span>
              </div>

              <h3>{lic.orgao}</h3>
              <p className="objeto">
                {lic.objeto?.slice(0, 220)}
                {lic.objeto && lic.objeto.length > 220 ? "..." : ""}
              </p>

              <div className="meta-linha">
                <span>📍 {lic.cidade}/{lic.uf}</span>
                <span>💰 {formatarValor(lic.valor_estimado)}</span>
                <span>⏰ Proposta encerra: {diasAte(lic.data_encerramento_proposta)}</span>
              </div>

              <div className="protocolo">{lic.numero_controle}</div>

              {lic.link_edital && (
                <a href={lic.link_edital} target="_blank" rel="noreferrer" className="link-edital">
                  Ver edital no PNCP →
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}