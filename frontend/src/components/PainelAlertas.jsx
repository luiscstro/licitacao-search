import { useEffect, useRef, useState } from "react";
import { Bell, Clock, ArrowUpRight } from "lucide-react";
import { api } from "../api";
import { diasAte, diasRestantes } from "../utils/data";

export default function PainelAlertas({ aberto, aoAlternar, aoFechar }) {
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");
  const [urgentes, setUrgentes] = useState(null); // null = ainda não buscou
  const ref = useRef(null);

  useEffect(() => {
    if (!aberto) return;
    if (urgentes === null) {
      setCarregando(true);
      setErro("");
      api
        .listarFavoritos()
        .then((favoritos) => {
          const comPrazo = favoritos
            .filter((f) => {
              const dias = diasRestantes(f.data_encerramento_proposta);
              return dias !== null && dias >= 0 && dias <= 5;
            })
            .sort((a, b) => diasRestantes(a.data_encerramento_proposta) - diasRestantes(b.data_encerramento_proposta));
          setUrgentes(comPrazo);
        })
        .catch((err) => setErro(err.message))
        .finally(() => setCarregando(false));
    }
  }, [aberto, urgentes]);

  useEffect(() => {
    function aoClicarFora(e) {
      if (ref.current && !ref.current.contains(e.target)) aoFechar();
    }
    if (aberto) document.addEventListener("mousedown", aoClicarFora);
    return () => document.removeEventListener("mousedown", aoClicarFora);
  }, [aberto, aoFechar]);

  return (
    <div className="navbar-item-wrap" ref={ref}>
      <button
        className={`navbar-icone-botao ${aberto ? "ativo" : ""}`}
        onClick={aoAlternar}
        aria-label="Alertas de prazo"
        title="Alertas de prazo dos seus favoritos"
      >
        <Bell size={18} strokeWidth={2} />
      </button>

      {aberto && (
        <div className="painel-flutuante painel-alertas">
          <div className="painel-flutuante-titulo">
            <span>Alertas de prazo</span>
            <span className="ajuda" style={{ fontSize: 11.5 }}>favoritos vencendo em até 5 dias</span>
          </div>

          {carregando && <div className="carregando" style={{ padding: "16px 4px" }}>Verificando prazos...</div>}
          {erro && <div className="erro-msg" style={{ margin: "8px 4px" }}>{erro}</div>}

          {!carregando && !erro && urgentes && urgentes.length === 0 && (
            <div className="painel-alertas-vazio">Nenhum favorito com prazo apertado no momento.</div>
          )}

          {!carregando && urgentes && urgentes.length > 0 && (
            <div className="painel-alertas-lista">
              {urgentes.map((lic) => (
                <a
                  key={lic.numero_controle}
                  href={lic.link_edital || undefined}
                  target={lic.link_edital ? "_blank" : undefined}
                  rel="noreferrer"
                  className="painel-alertas-item"
                >
                  <div className="painel-alertas-item-topo">
                    <span className="painel-alertas-orgao">{lic.orgao && lic.orgao !== "—" ? lic.orgao : lic.cidade}</span>
                    <ArrowUpRight size={13} strokeWidth={2.2} />
                  </div>
                  <div className="painel-alertas-prazo">
                    <Clock size={12} strokeWidth={2.2} /> encerra {diasAte(lic.data_encerramento_proposta)}
                  </div>
                </a>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
