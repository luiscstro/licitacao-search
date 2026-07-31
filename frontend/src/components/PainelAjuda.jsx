import { X, Target, ListChecks, Search, Star } from "lucide-react";

const TOPICOS = [
  {
    Icone: Target,
    titulo: "Como funciona a pontuação",
    corpo: (
      <>
        Cada licitação que bate com um critério recebe uma pontuação: <strong>30 pontos</strong> por
        atender ao termo obrigatório, <strong>+10</strong> para cada variação extra do termo que também
        aparecer, <strong>+15</strong> por palavra-chave complementar encontrada, e um bônus proporcional
        ao valor estimado (até +20). A lista ordena sempre da pontuação mais alta para a mais baixa.
      </>
    ),
  },
  {
    Icone: ListChecks,
    titulo: "Como montar um bom critério",
    corpo: (
      <>
        Separe variações do termo obrigatório por vírgula (ex: "apoio administrativo, auxiliar
        administrativo") — basta <strong>uma</strong> aparecer no objeto da licitação para passar.
        Palavras-chave complementares não aprovam sozinhas, só somam pontos. Deixe estados e
        modalidades em branco para aceitar qualquer um.
      </>
    ),
  },
  {
    Icone: Search,
    titulo: "Busca livre × critérios salvos",
    corpo: (
      <>
        Na tela "Licitações", buscar por palavra sem selecionar um critério pesquisa em{" "}
        <strong>todas as licitações ativas do Brasil</strong>, qualquer modalidade. Selecionando um
        critério, o sistema aplica as regras salvas dele — os dois modos podem ser combinados.
      </>
    ),
  },
  {
    Icone: Star,
    titulo: "Favoritos e alertas de prazo",
    corpo: (
      <>
        Favorite licitações relevantes para acompanhá-las na aba "Favoritos". O sino no topo avisa
        quando algum favorito está a 5 dias ou menos do encerramento da proposta.
      </>
    ),
  },
];

export default function PainelAjuda({ aoFechar }) {
  return (
    <div className="painel-overlay" onClick={aoFechar}>
      <div className="painel-modal painel-ajuda card-formulario" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
          <div>
            <span className="eyebrow">Guia rápido</span>
            <h2 style={{ marginBottom: 0 }}>Central de ajuda</h2>
          </div>
          <button
            className="botao fantasma"
            onClick={aoFechar}
            style={{ padding: 8, borderRadius: "50%", width: 32, height: 32, flexShrink: 0 }}
            aria-label="Fechar"
          >
            <X size={15} strokeWidth={2.2} />
          </button>
        </div>

        <div className="painel-ajuda-lista">
          {TOPICOS.map(({ Icone, titulo, corpo }) => (
            <div className="painel-ajuda-item" key={titulo}>
              <div className="painel-ajuda-icone">
                <Icone size={16} strokeWidth={2} />
              </div>
              <div>
                <div className="painel-ajuda-titulo">{titulo}</div>
                <p className="painel-ajuda-corpo">{corpo}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
