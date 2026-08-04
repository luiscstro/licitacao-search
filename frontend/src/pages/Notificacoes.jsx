import { useEffect, useState } from "react";
import { Mail } from "lucide-react";
import { api } from "../api";

export default function Notificacoes({ perfil, aoAtualizarPerfil }) {
  const [ligado, setLigado] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState(false);

  useEffect(() => {
    if (perfil) setLigado(perfil.receber_notificacoes !== false);
  }, [perfil]);

  async function alternar(e) {
    const novoValor = e.target.checked;
    setLigado(novoValor);
    setErro("");
    setSucesso(false);
    setSalvando(true);
    try {
      const perfilAtualizado = await api.atualizarPreferencias({ receberNotificacoes: novoValor });
      aoAtualizarPerfil?.(perfilAtualizado);
      setSucesso(true);
      setTimeout(() => setSucesso(false), 2500);
    } catch (err) {
      setLigado(!novoValor); // desfaz a mudança visual se a API recusar
      setErro(err.message);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div>
      <div className="cabecalho-pagina">
        <div>
          <span className="eyebrow">Conta</span>
          <h1>Notificações</h1>
          <div className="contagem">Resumo diário de licitações novas por e-mail</div>
        </div>
      </div>

      {erro && <div className="erro-msg">{erro}</div>}
      {sucesso && <div className="sucesso-msg">Preferência salva.</div>}

      <div className="card-formulario">
        <h2>
          <Mail size={17} strokeWidth={2} style={{ verticalAlign: "-3px", marginRight: 8, color: "var(--selo-gold-deep)" }} />
          Resumo diário por e-mail
        </h2>
        <p className="ajuda" style={{ marginBottom: 18 }}>
          Todo dia, depois da coleta de novas licitações, mandamos um e-mail pra {perfil?.email || "você"} com
          as oportunidades que bateram com os critérios da sua empresa — órgão, valor, prazo e o motivo de cada uma
          ter aparecido.
        </p>

        <div className="campo-checkbox">
          <input
            id="receber-notificacoes"
            type="checkbox"
            checked={ligado}
            disabled={salvando}
            onChange={alternar}
          />
          <label htmlFor="receber-notificacoes">
            {ligado ? "Recebendo o resumo diário" : "Notificações desativadas"}
          </label>
        </div>
      </div>
    </div>
  );
}
