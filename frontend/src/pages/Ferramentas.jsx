import {
  Search, ListChecks, Star, Users2, MessageCircle,
  Mail, BarChart3, Download, RefreshCw, ArrowRight, Clock,
} from "lucide-react";

const GRUPOS = [
  {
    id: "negocio",
    titulo: "Oportunidades de Negócio",
    destaque: false,
    cartoes: [
      {
        Icone: Search,
        titulo: "Buscar Licitações",
        descricao: "Busca livre em todo o Brasil ou filtrada pelos seus critérios salvos.",
        pagina: "dashboard",
      },
      {
        Icone: ListChecks,
        titulo: "Meus Critérios",
        descricao: "Configure palavras-chave, valores, estados e modalidades que te interessam.",
        pagina: "criterios",
      },
      {
        Icone: Star,
        titulo: "Favoritos",
        descricao: "Licitações que você guardou para acompanhar de perto.",
        pagina: "favoritos",
      },
    ],
  },
  {
    id: "equipe",
    titulo: "Equipe & Colaboração",
    destaque: false,
    cartoes: [
      {
        Icone: Users2,
        titulo: "Minha Equipe",
        descricao: "Veja quem faz parte da conta e convide novos colegas.",
        pagina: "equipe",
      },
      {
        Icone: MessageCircle,
        titulo: "Comentários da Equipe",
        descricao: "Anotações deixadas em cada licitação ficam visíveis para todo o time.",
        pagina: "dashboard",
      },
    ],
  },
  {
    id: "roadmap",
    titulo: "Em Desenvolvimento",
    destaque: true,
    cartoes: [
      { Icone: Mail, titulo: "Notificações por E-mail", descricao: "Receba um resumo das novas licitações relevantes direto na caixa de entrada." },
      { Icone: BarChart3, titulo: "Dashboard com Indicadores", descricao: "Gráficos de volume, valores e desempenho por critério." },
      { Icone: Download, titulo: "Exportação de Resultados", descricao: "Baixe suas licitações filtradas em planilha." },
      { Icone: RefreshCw, titulo: "Atualização Automática", descricao: "Coleta diária de novas licitações do PNCP, sem rodar nada manualmente." },
    ],
  },
];

export default function Ferramentas({ perfil, aoNavegar }) {
  const primeiroNome = perfil?.email ? perfil.email.split("@")[0] : "";

  return (
    <div>
      <div className="cabecalho-pagina">
        <div>
          <span className="eyebrow">Início</span>
          <h1>Nossas Ferramentas</h1>
          <div className="contagem">
            {primeiroNome ? `Bem-vindo(a) de volta, ${primeiroNome}.` : "Tudo o que você precisa em um só lugar."}
          </div>
        </div>
      </div>

      <div className="grade-grupos">
        {GRUPOS.map((grupo) => (
          <section key={grupo.id} className={`painel-grupo ${grupo.destaque ? "destaque" : ""}`}>
            <h2 className="painel-grupo-titulo">{grupo.titulo}</h2>
            <div className="grade-cartoes-ferramenta">
              {grupo.cartoes.map((cartao) => {
                const emBreve = !cartao.pagina;
                const Icone = cartao.Icone;
                return (
                  <button
                    key={cartao.titulo}
                    type="button"
                    className={`cartao-ferramenta ${emBreve ? "bloqueado" : ""}`}
                    onClick={() => !emBreve && aoNavegar(cartao.pagina)}
                    disabled={emBreve}
                  >
                    {emBreve && (
                      <span className="selo-em-breve">
                        <Clock size={10} strokeWidth={2.4} /> Em breve
                      </span>
                    )}
                    <span className="cartao-ferramenta-icone">
                      <Icone size={22} strokeWidth={1.8} />
                    </span>
                    <span className="cartao-ferramenta-titulo">{cartao.titulo}</span>
                    <span className="cartao-ferramenta-descricao">{cartao.descricao}</span>
                    {!emBreve && (
                      <span className="cartao-ferramenta-ir">
                        Acessar <ArrowRight size={13} strokeWidth={2.2} />
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
