import { useEffect, useState } from "react";
import { api } from "../api";

const CRITERIO_VAZIO = {
  nome: "",
  palavra_obrigatoria: "",
  palavras_bonus: "",
  valor_minimo: 0,
  valor_maximo: 20000000,
  estados_permitidos: "",
  exigir_dedicacao_exclusiva: true,
  exigir_pregao: true,
};

export default function Criterios() {
  const [criterios, setCriterios] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [editando, setEditando] = useState(null); // null = não editando, "novo" = criando, ou o objeto do critério
  const [form, setForm] = useState(CRITERIO_VAZIO);
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);

  function carregar() {
    setCarregando(true);
    api
      .listarCriterios()
      .then(setCriterios)
      .catch((err) => setErro(err.message))
      .finally(() => setCarregando(false));
  }

  useEffect(() => {
    carregar();
  }, []);

  function abrirNovo() {
    setForm(CRITERIO_VAZIO);
    setEditando("novo");
    setErro("");
  }

  function abrirEdicao(criterio) {
    setForm({
      nome: criterio.nome,
      palavra_obrigatoria: criterio.palavra_obrigatoria,
      palavras_bonus: criterio.palavras_bonus,
      valor_minimo: criterio.valor_minimo,
      valor_maximo: criterio.valor_maximo,
      estados_permitidos: criterio.estados_permitidos,
      exigir_dedicacao_exclusiva: criterio.exigir_dedicacao_exclusiva,
      exigir_pregao: criterio.exigir_pregao,
    });
    setEditando(criterio);
    setErro("");
  }

  async function salvar(e) {
    e.preventDefault();
    setSalvando(true);
    setErro("");
    try {
      if (editando === "novo") {
        await api.criarCriterio(form);
      } else {
        await api.atualizarCriterio(editando.id, form);
      }
      setEditando(null);
      carregar();
    } catch (err) {
      setErro(err.message);
    } finally {
      setSalvando(false);
    }
  }

  async function apagar(id) {
    if (!confirm("Tem certeza que quer apagar esse critério?")) return;
    try {
      await api.deletarCriterio(id);
      carregar();
    } catch (err) {
      setErro(err.message);
    }
  }

  function resumoCriterio(c) {
    const partes = [`palavra: "${c.palavra_obrigatoria}"`];
    if (c.estados_permitidos) partes.push(`estados: ${c.estados_permitidos}`);
    partes.push(`até ${new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(c.valor_maximo)}`);
    if (c.exigir_dedicacao_exclusiva) partes.push("DEMO");
    if (c.exigir_pregao) partes.push("só pregão");
    return partes.join(" · ");
  }

  return (
    <div>
      <div className="cabecalho-pagina">
        <div>
          <h1>Meus critérios</h1>
          <div className="contagem">defina o que conta como uma boa licitação para você</div>
        </div>
        {!editando && (
          <button className="botao dourado" onClick={abrirNovo}>
            + Novo critério
          </button>
        )}
      </div>

      {erro && <div className="erro-msg">{erro}</div>}

      {!editando && (
        <>
          {carregando && <div className="carregando">Carregando...</div>}

          {!carregando && criterios.length === 0 && (
            <div className="estado-vazio">
              <h3>Nenhum critério ainda</h3>
              <p>Crie o primeiro para começar a ver licitações no seu painel.</p>
            </div>
          )}

          <div className="lista-criterios">
            {criterios.map((c) => (
              <div className="item-criterio" key={c.id}>
                <div>
                  <div className="nome-criterio">{c.nome}</div>
                  <div className="resumo-criterio">{resumoCriterio(c)}</div>
                </div>
                <div className="acoes">
                  <button className="botao fantasma" onClick={() => abrirEdicao(c)}>
                    Editar
                  </button>
                  <button className="botao perigo" onClick={() => apagar(c.id)}>
                    Apagar
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {editando && (
        <div className="card-formulario">
          <h2>{editando === "novo" ? "Novo critério" : `Editando: ${editando.nome}`}</h2>

          <form onSubmit={salvar}>
            <div className="campo">
              <label htmlFor="nome">Nome do critério</label>
              <input
                id="nome"
                type="text"
                required
                value={form.nome}
                onChange={(e) => setForm({ ...form, nome: e.target.value })}
                placeholder="Ex: Apoio Administrativo - Região MA"
              />
            </div>

            <div className="campo">
              <label htmlFor="palavra_obrigatoria">Palavra-chave obrigatória</label>
              <input
                id="palavra_obrigatoria"
                type="text"
                required
                value={form.palavra_obrigatoria}
                onChange={(e) => setForm({ ...form, palavra_obrigatoria: e.target.value })}
                placeholder="Ex: apoio administrativo"
              />
              <span className="ajuda">Toda licitação aprovada precisa conter esse termo.</span>
            </div>

            <div className="campo">
              <label htmlFor="palavras_bonus">Palavras-chave complementares</label>
              <input
                id="palavras_bonus"
                type="text"
                value={form.palavras_bonus}
                onChange={(e) => setForm({ ...form, palavras_bonus: e.target.value })}
                placeholder="Ex: limpeza, recepção, copeiragem"
              />
              <span className="ajuda">Separadas por vírgula. Não aprovam sozinhas, só somam pontos.</span>
            </div>

            <div className="linha-dupla">
              <div className="campo">
                <label htmlFor="valor_minimo">Valor mínimo (R$)</label>
                <input
                  id="valor_minimo"
                  type="number"
                  min="0"
                  value={form.valor_minimo}
                  onChange={(e) => setForm({ ...form, valor_minimo: Number(e.target.value) })}
                />
              </div>
              <div className="campo">
                <label htmlFor="valor_maximo">Valor máximo (R$)</label>
                <input
                  id="valor_maximo"
                  type="number"
                  min="0"
                  value={form.valor_maximo}
                  onChange={(e) => setForm({ ...form, valor_maximo: Number(e.target.value) })}
                />
              </div>
            </div>

            <div className="campo">
              <label htmlFor="estados">Estados aceitos</label>
              <input
                id="estados"
                type="text"
                value={form.estados_permitidos}
                onChange={(e) => setForm({ ...form, estados_permitidos: e.target.value.toUpperCase() })}
                placeholder="Ex: MA,PI,PA,TO,CE"
              />
              <span className="ajuda">Siglas separadas por vírgula. Deixe em branco para aceitar qualquer estado.</span>
            </div>

            <div className="campo-checkbox">
              <input
                id="demo"
                type="checkbox"
                checked={form.exigir_dedicacao_exclusiva}
                onChange={(e) => setForm({ ...form, exigir_dedicacao_exclusiva: e.target.checked })}
              />
              <label htmlFor="demo">Exigir dedicação exclusiva de mão de obra (DEMO)</label>
            </div>

            <div className="campo-checkbox">
              <input
                id="pregao"
                type="checkbox"
                checked={form.exigir_pregao}
                onChange={(e) => setForm({ ...form, exigir_pregao: e.target.checked })}
              />
              <label htmlFor="pregao">Aceitar somente modalidade Pregão</label>
            </div>

            <div className="acoes-formulario">
              <button type="submit" className="botao primario" disabled={salvando}>
                {salvando ? "Salvando..." : "Salvar critério"}
              </button>
              <button type="button" className="botao fantasma" onClick={() => setEditando(null)}>
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}