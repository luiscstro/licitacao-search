import { ArrowUpRight, Clock, MapPin, MessageCircle, Star, Wallet } from "lucide-react";
import { useState } from "react";
import { api } from "../api";
import { formatarDataHora, formatarValor, urgente } from "../utils/data";
import Carimbo from "./Carimbo";
import PainelComentarios from "./PainelComentarios";

export default function CartaoLicitacao({ lic, aoMudarFavorito, estilo }) {
  const [favoritada, setFavoritada] = useState(lic.favoritada);
  const [comentariosAbertos, setComentariosAbertos] = useState(false);
  const [alternandoFavorito, setAlternandoFavorito] = useState(false);
  const [pop, setPop] = useState(false);

  async function alternarFavorito() {
    const novoEstado = !favoritada;
    // Otimista: muda a estrela já, junto com a animação de "pop" — não
    // espera a resposta da rede (que pode levar mais de 1s), senão a
    // animação toca e termina bem antes da estrela realmente mudar,
    // parecendo atrasada/dessincronizada. Só reverte se a chamada falhar.
    setFavoritada(novoEstado);
    setAlternandoFavorito(true);
    setPop(true);
    setTimeout(() => setPop(false), 260);
    try {
      if (novoEstado) {
        await api.favoritar(lic.numero_controle);
      } else {
        await api.desfavoritar(lic.numero_controle);
      }
      aoMudarFavorito?.();
    } catch {
      setFavoritada(!novoEstado); // reverte — a chamada não teve sucesso de verdade
    } finally {
      setAlternandoFavorito(false);
    }
  }

  return (
    <div className="cartao-licitacao" style={estilo}>
      <div className="topo-cartao">
        {lic.score > 0 && <Carimbo cor="dourado">{Math.round(lic.score)} pts</Carimbo>}
        {lic.uf && <Carimbo cor="neutro">{lic.uf}</Carimbo>}
        {urgente(lic.data_encerramento_proposta) && <Carimbo cor="terracota">prazo curto</Carimbo>}
        <button
          className={`botao-favorito ${favoritada ? "ativo" : ""} ${pop ? "pop" : ""}`}
          onClick={alternarFavorito}
          disabled={alternandoFavorito}
          title={favoritada ? "Remover dos favoritos" : "Favoritar"}
        >
          <Star fill={favoritada ? "currentColor" : "none"} strokeWidth={1.8} />
        </button>
      </div>

      <h3>{lic.orgao && lic.orgao !== "—" ? lic.orgao : lic.cidade}</h3>
      <p className="objeto">
        {lic.objeto?.slice(0, 220)}
        {lic.objeto && lic.objeto.length > 220 ? "..." : ""}
      </p>

      <div className="meta-linha">
        <span>
          <MapPin strokeWidth={2} /> {lic.cidade}/{lic.uf}
        </span>
        <span>
          <Wallet strokeWidth={2} /> {formatarValor(lic.valor_estimado)}
        </span>
        <span>
          <Clock strokeWidth={2} /> {formatarDataHora(lic.data_encerramento_proposta)}
        </span>
      </div>

      <div className="protocolo">{lic.numero_controle}</div>

      <div style={{ display: "flex", gap: 16, alignItems: "center", marginTop: 2 }}>
        {lic.link_edital && (
          <a href={lic.link_edital} target="_blank" rel="noreferrer" className="link-edital">
            Ver edital no PNCP <ArrowUpRight size={13} strokeWidth={2.2} />
          </a>
        )}
        <button className="botao-comentarios" onClick={() => setComentariosAbertos(true)}>
          <MessageCircle strokeWidth={2} /> Comentários
        </button>
      </div>

      {comentariosAbertos && (
        <PainelComentarios
          numeroControle={lic.numero_controle}
          aoFechar={() => setComentariosAbertos(false)}
        />
      )}
    </div>
  );
}
