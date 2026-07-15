import { useState } from "react";
import Carimbo from "./Carimbo";
import PainelComentarios from "./PainelComentarios";
import { api } from "../api";

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

function urgente(dataStr) {
  if (!dataStr) return false;
  const data = new Date(dataStr);
  const hoje = new Date();
  const dias = Math.round((data.setHours(0, 0, 0, 0) - hoje.setHours(0, 0, 0, 0)) / 86400000);
  return dias >= 0 && dias <= 3;
}

export default function CartaoLicitacao({ lic, aoMudarFavorito }) {
  const [favoritada, setFavoritada] = useState(lic.favoritada);
  const [comentariosAbertos, setComentariosAbertos] = useState(false);
  const [alternandoFavorito, setAlternandoFavorito] = useState(false);

  async function alternarFavorito() {
    setAlternandoFavorito(true);
    try {
      if (favoritada) {
        await api.desfavoritar(lic.numero_controle);
      } else {
        await api.favoritar(lic.numero_controle);
      }
      setFavoritada(!favoritada);
      aoMudarFavorito?.();
    } catch {
      // silencioso — não é crítico, usuário pode tentar de novo
    } finally {
      setAlternandoFavorito(false);
    }
  }

  return (
    <div className="cartao-licitacao">
      <div className="topo-cartao">
        {lic.score > 0 && <Carimbo cor="dourado">{Math.round(lic.score)} pts</Carimbo>}
        {lic.uf && <Carimbo cor="neutro">{lic.uf}</Carimbo>}
        {urgente(lic.data_encerramento_proposta) && <Carimbo cor="terracota">prazo curto</Carimbo>}
        <button
          onClick={alternarFavorito}
          disabled={alternandoFavorito}
          title={favoritada ? "Remover dos favoritos" : "Favoritar"}
          style={{
            all: "unset", cursor: "pointer", marginLeft: "auto", fontSize: 18,
            color: favoritada ? "var(--selo-gold)" : "var(--slate-line)", lineHeight: 1,
          }}
        >
          {favoritada ? "★" : "☆"}
        </button>
      </div>

      <h3>{lic.orgao && lic.orgao !== "—" ? lic.orgao : lic.cidade}</h3>
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

      <div style={{ display: "flex", gap: 14, alignItems: "center", marginTop: 2 }}>
        {lic.link_edital && (
          <a href={lic.link_edital} target="_blank" rel="noreferrer" className="link-edital">
            Ver edital no PNCP →
          </a>
        )}
        <button
          onClick={() => setComentariosAbertos(true)}
          style={{ all: "unset", cursor: "pointer", fontSize: 12.5, color: "var(--slate)", textDecoration: "underline" }}
        >
          💬 Comentários
        </button>
      </div>

      {comentariosAbertos && (
        <PainelComentarios numeroControle={lic.numero_controle} aoFechar={() => setComentariosAbertos(false)} />
      )}
    </div>
  );
}