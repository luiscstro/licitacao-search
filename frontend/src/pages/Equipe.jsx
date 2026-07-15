import { useEffect, useState } from "react";
import { api } from "../api";
import Carimbo from "../components/Carimbo";

export default function Equipe({ perfil }) {
  const [empresa, setEmpresa] = useState(null);
  const [membros, setMembros] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [emailConvite, setEmailConvite] = useState("");
  const [linkGerado, setLinkGerado] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  const souOwner = perfil?.papel === "owner";

  function carregar() {
    setCarregando(true);
    Promise.all([api.minhaEmpresa(), api.listarMembros()])
      .then(([emp, mem]) => {
        setEmpresa(emp);
        setMembros(mem);
      })
      .catch((err) => setErro(err.message))
      .finally(() => setCarregando(false));
  }

  useEffect(() => {
    carregar();
  }, []);

  async function convidar(e) {
    e.preventDefault();
    setErro("");
    setEnviando(true);
    setLinkGerado("");
    try {
      const convite = await api.convidarMembro(emailConvite);
      const link = `${window.location.origin}?convite=${convite.token}`;
      setLinkGerado(link);
      setEmailConvite("");
    } catch (err) {
      setErro(err.message);
    } finally {
      setEnviando(false);
    }
  }

  function copiarLink() {
    navigator.clipboard.writeText(linkGerado);
  }

  return (
    <div>
      <div className="cabecalho-pagina">
        <div>
          <h1>Minha equipe</h1>
          <div className="contagem">
            {carregando ? "carregando..." : empresa ? empresa.nome : ""}
          </div>
        </div>
      </div>

      {erro && <div className="erro-msg">{erro}</div>}

      {!carregando && (
        <>
          <div className="lista-criterios">
            {membros.map((m) => (
              <div className="item-criterio" key={m.id}>
                <div>
                  <div className="nome-criterio">{m.email}</div>
                  <div className="resumo-criterio">
                    entrou em {new Date(m.criado_em).toLocaleDateString("pt-BR")}
                  </div>
                </div>
                <Carimbo cor={m.papel === "owner" ? "dourado" : "neutro"}>
                  {m.papel === "owner" ? "dono da conta" : "membro"}
                </Carimbo>
              </div>
            ))}
          </div>

          {souOwner ? (
            <div className="card-formulario">
              <h2>Convidar alguém para a equipe</h2>
              <p className="ajuda" style={{ marginBottom: 16 }}>
                A pessoa convidada vai ver os mesmos critérios e licitações que você — ótimo
                para trabalhar junto com colegas na mesma base.
              </p>

              <form onSubmit={convidar}>
                <div className="campo">
                  <label htmlFor="email-convite">E-mail da pessoa</label>
                  <input
                    id="email-convite"
                    type="email"
                    required
                    value={emailConvite}
                    onChange={(e) => setEmailConvite(e.target.value)}
                    placeholder="colega@empresa.com"
                  />
                </div>
                <button type="submit" className="botao dourado" disabled={enviando}>
                  {enviando ? "Gerando..." : "Gerar convite"}
                </button>
              </form>

              {linkGerado && (
                <div className="sucesso-msg" style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 8 }}>
                  <div>Convite gerado! Envie esse link para a pessoa (por WhatsApp, e-mail etc):</div>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <code style={{ fontSize: 12, wordBreak: "break-all" }}>{linkGerado}</code>
                    <button type="button" className="botao fantasma" onClick={copiarLink} style={{ flexShrink: 0 }}>
                      Copiar
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="ajuda">Só o dono da conta pode convidar novos membros.</p>
          )}
        </>
      )}
    </div>
  );
}