import { CloudOff, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import { formatarDataHora } from "../utils/data";

const INTERVALO_RECONFERENCIA_MS = 10 * 60 * 1000; // reconfere a cada 10 min

// Avisa o usuário quando o coletor do PNCP falhou ou a base está
// desatualizada — pra deixar claro que o problema é externo (o PNCP), não
// um bug da plataforma, e que licitações novas podem não estar aparecendo.
export default function AvisoPncp() {
  const [estado, setEstado] = useState(null);

  useEffect(() => {
    let cancelado = false;

    function buscar() {
      api
        .statusPncp()
        .then((dados) => {
          if (!cancelado) setEstado(dados);
        })
        .catch(() => {});
    }

    buscar();
    const intervalo = setInterval(buscar, INTERVALO_RECONFERENCIA_MS);
    return () => {
      cancelado = true;
      clearInterval(intervalo);
    };
  }, []);

  if (!estado) return null;

  if (estado.pncp_instavel) {
    return (
      <div className="aviso-pncp instavel" role="status">
        <CloudOff size={16} strokeWidth={2} />
        <span>
          <strong>O Portal Nacional de Contratações Públicas (PNCP) apresentou instabilidade</strong> na
          última coleta
          {estado.ultima_execucao_em ? `, em ${formatarDataHora(estado.ultima_execucao_em)}` : ""}. Pode haver
          licitações novas que ainda não aparecem por aqui — assim que o PNCP normalizar, a próxima coleta
          automática traz o que faltou. Isso não é uma falha da nossa plataforma.
        </span>
      </div>
    );
  }

  if (estado.dados_desatualizados) {
    return (
      <div className="aviso-pncp desatualizado" role="status">
        <TriangleAlert size={16} strokeWidth={2} />
        <span>
          Ainda não conseguimos confirmar uma coleta recente e bem-sucedida da base de licitações
          {estado.ultima_coleta_com_sucesso_em
            ? ` (última confirmada em ${formatarDataHora(estado.ultima_coleta_com_sucesso_em)})`
            : ""}
          . Pode haver licitações novas que ainda não aparecem por aqui.
        </span>
      </div>
    );
  }

  return null;
}
