import { useEffect, useState } from "react";
import { X, Send } from "lucide-react";
import { api } from "../api";

export default function PainelComentarios({ numeroControle, aoFechar }) {
  const [comentarios, setComentarios] = useState([]);
  const [texto, setTexto] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");

  function carregar() {
    setCarregando(true);
    api
      .listarComentarios(numeroControle)
      .then(setComentarios)
      .catch((err) => setErro(err.message))
      .finally(() => setCarregando(false));
  }

  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [numeroControle]);

  async function enviar(e) {
    e.preventDefault();
    if (!texto.trim()) return;
    setEnviando(true);
    setErro("");
    try {
      await api.criarComentario(numeroControle, texto.trim());
      setTexto("");
      carregar();
    } catch (err) {
      setErro(err.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="painel-overlay" onClick={aoFechar}>
      <div className="painel-modal card-formulario" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
          <h2 style={{ marginBottom: 0 }}>Comentários da equipe</h2>
          <button
            className="botao fantasma"
            onClick={aoFechar}
            style={{ padding: 8, borderRadius: "50%", width: 32, height: 32 }}
            aria-label="Fechar"
          >
            <X size={15} strokeWidth={2.2} />
          </button>
        </div>

        <div className="protocolo" style={{ marginBottom: 16 }}>{numeroControle}</div>

        {erro && <div className="erro-msg">{erro}</div>}

        <div style={{ overflowY: "auto", flex: 1, marginBottom: 16, display: "flex", flexDirection: "column", gap: 10 }}>
          {carregando && <div className="carregando">Carregando comentários...</div>}
          {!carregando && comentarios.length === 0 && (
            <p className="ajuda">Nenhum comentário ainda. Seja o primeiro da equipe a anotar algo aqui.</p>
          )}
          {comentarios.map((c) => (
            <div key={c.id} style={{ borderBottom: "1px dashed var(--linha)", paddingBottom: 8 }}>
              <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--ink)" }}>{c.autor_email}</div>
              <div style={{ fontSize: 13.5, color: "var(--slate)", marginTop: 2, lineHeight: 1.5 }}>{c.texto}</div>
              <div style={{ fontSize: 11, color: "var(--slate-dim)", marginTop: 4, fontFamily: "var(--fonte-mono)" }}>
                {new Date(c.criado_em).toLocaleString("pt-BR")}
              </div>
            </div>
          ))}
        </div>

        <form onSubmit={enviar} style={{ display: "flex", gap: 8 }}>
          <input
            type="text"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Escreva uma anotação..."
            style={{
              flex: 1, fontFamily: "var(--fonte-ui)", fontSize: 14, padding: "10px 12px",
              border: "1.5px solid var(--slate-line)", borderRadius: "var(--radius)",
            }}
          />
          <button type="submit" className="botao primario" disabled={enviando}>
            {enviando ? "..." : <><Send size={14} strokeWidth={2.2} /> Enviar</>}
          </button>
        </form>
      </div>
    </div>
  );
}