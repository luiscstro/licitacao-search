import { useEffect, useState } from "react";
import { BarChart3 } from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import { api } from "../api";
import NumeroAnimado from "../components/NumeroAnimado";

const CORES = ["#d4af37", "#0f0f11", "#2f6b4f", "#b14b3b", "#5b5b62", "#a9872a", "#8b8b93", "#dedee2"];

function formatarMoeda(valor) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(valor || 0);
}

function CardIndicador({ titulo, children }) {
  return (
    <div className="card-formulario card-indicador">
      <h2>{titulo}</h2>
      {children}
    </div>
  );
}

export default function Indicadores() {
  const [criterios, setCriterios] = useState([]);
  const [criterioSelecionado, setCriterioSelecionado] = useState("todos");
  const [estatisticas, setEstatisticas] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api.listarCriterios().then(setCriterios).catch(() => {});
  }, []);

  useEffect(() => {
    setCarregando(true);
    setErro("");
    const criterioId = criterioSelecionado === "todos" ? undefined : criterioSelecionado;
    api
      .buscarEstatisticas({ criterioId })
      .then(setEstatisticas)
      .catch((err) => setErro(err.message))
      .finally(() => setCarregando(false));
  }, [criterioSelecionado]);

  return (
    <div>
      <div className="cabecalho-pagina">
        <div>
          <span className="eyebrow">Painel</span>
          <h1>Indicadores</h1>
          <div className="contagem">
            {carregando ? "carregando..." : estatisticas ? `${estatisticas.total} licitação(ões) no conjunto atual` : ""}
          </div>
        </div>

        {criterios.length > 0 && (
          <div className="seletor-criterio">
            <label htmlFor="criterio-indicadores" style={{ fontSize: 13, color: "var(--slate)" }}>
              Critério
            </label>
            <select
              id="criterio-indicadores"
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

      {carregando && (
        <div className="grade-indicadores">
          {[0, 1, 2].map((i) => (
            <div key={i} className="esqueleto-cartao" style={{ minHeight: 300 }}>
              <div className="esqueleto-linha media" />
              <div className="esqueleto-linha larga" style={{ height: 220 }} />
            </div>
          ))}
        </div>
      )}

      {!carregando && estatisticas && estatisticas.total === 0 && (
        <div className="estado-vazio">
          <BarChart3 strokeWidth={1.5} />
          <h3>Sem dados suficientes ainda</h3>
          <p>Ajuste ou crie um critério em "Meus critérios" pra começar a ver indicadores aqui.</p>
        </div>
      )}

      {!carregando && estatisticas && estatisticas.total > 0 && (
        <>
          <div className="grade-resumo-indicadores">
            <div className="pastilha-resumo">
              <span className="pastilha-resumo-rotulo">Total de licitações</span>
              <span className="pastilha-resumo-valor"><NumeroAnimado valor={estatisticas.total} /></span>
            </div>
            <div className="pastilha-resumo">
              <span className="pastilha-resumo-rotulo">Valor total estimado</span>
              <span className="pastilha-resumo-valor">
                <NumeroAnimado valor={estatisticas.valor_total_estimado} formatar={formatarMoeda} />
              </span>
            </div>
          </div>

          <div className="grade-indicadores">
            <CardIndicador titulo="Por estado (UF)">
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={estatisticas.por_uf} margin={{ top: 4, right: 8, left: -18, bottom: 0 }}>
                  <CartesianGrid stroke="#e7e7ea" vertical={false} />
                  <XAxis dataKey="chave" tick={{ fontSize: 12, fill: "#5b5b62" }} axisLine={{ stroke: "#dedee2" }} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#5b5b62" }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e7e7ea", fontSize: 13 }} />
                  <Bar dataKey="quantidade" fill="#d4af37" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardIndicador>

            <CardIndicador titulo="Por modalidade">
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={estatisticas.por_modalidade}
                    dataKey="quantidade"
                    nameKey="chave"
                    innerRadius={55}
                    outerRadius={90}
                    paddingAngle={2}
                  >
                    {estatisticas.por_modalidade.map((_, indice) => (
                      <Cell key={indice} fill={CORES[indice % CORES.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e7e7ea", fontSize: 13 }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            </CardIndicador>

            <CardIndicador titulo="Por mês de encerramento da proposta">
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={estatisticas.por_mes} margin={{ top: 4, right: 8, left: -18, bottom: 0 }}>
                  <CartesianGrid stroke="#e7e7ea" vertical={false} />
                  <XAxis dataKey="chave" tick={{ fontSize: 12, fill: "#5b5b62" }} axisLine={{ stroke: "#dedee2" }} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#5b5b62" }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e7e7ea", fontSize: 13 }} />
                  <Bar dataKey="quantidade" fill="#2f6b4f" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardIndicador>
          </div>
        </>
      )}
    </div>
  );
}
