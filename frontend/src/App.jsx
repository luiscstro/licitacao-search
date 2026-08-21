import {
  Bell,
  ChevronDown,
  FileCheck2,
  HelpCircle,
  Kanban,
  LayoutGrid,
  ListChecks,
  LogOut,
  Search,
  Star,
  Users2,
} from "lucide-react";
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { api } from "./api";
import EsqueletoPagina from "./components/EsqueletoPagina";
import { LogoCompacto } from "./components/Logo";
import PainelAjuda from "./components/PainelAjuda";
import PainelAlertas from "./components/PainelAlertas";
import Rodape from "./components/Rodape";
import TelaAutenticacao from "./pages/TelaAutenticacao";
import { iniciais } from "./utils/data";

// Cada página vira um chunk separado, baixado só quando o usuário navega
// até ela — a tela de login continua no bundle principal (é a primeira
// coisa renderizada, não faz sentido adiar).
const Ferramentas = lazy(() => import("./pages/Ferramentas"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Criterios = lazy(() => import("./pages/Criterios"));
const Favoritos = lazy(() => import("./pages/Favoritos"));
const Equipe = lazy(() => import("./pages/Equipe"));
const Notificacoes = lazy(() => import("./pages/Notificacoes"));
const Indicadores = lazy(() => import("./pages/Indicadores"));
const Pipeline = lazy(() => import("./pages/Pipeline"));
const Documentos = lazy(() => import("./pages/Documentos"));

const ITENS_NAV = [
  { id: "ferramentas", rotulo: "Ferramentas", Icone: LayoutGrid },
  { id: "dashboard", rotulo: "Licitações", Icone: Search },
  { id: "criterios", rotulo: "Meus critérios", Icone: ListChecks },
  { id: "favoritos", rotulo: "Favoritos", Icone: Star },
  { id: "pipeline", rotulo: "Pipeline", Icone: Kanban },
  { id: "documentos", rotulo: "Documentos", Icone: FileCheck2 },
  { id: "equipe", rotulo: "Minha equipe", Icone: Users2 },
];

export default function App() {
  const [logado, setLogado] = useState(api.estaLogado());
  const [pagina, setPagina] = useState("ferramentas");
  const [perfil, setPerfil] = useState(null);

  const [alertasAbertos, setAlertasAbertos] = useState(false);
  const [ajudaAberta, setAjudaAberta] = useState(false);
  const [menuAbertoAvatar, setMenuAbertoAvatar] = useState(false);
  const refAvatar = useRef(null);

  useEffect(() => {
    if (logado) {
      api
        .meuPerfil()
        .then(setPerfil)
        .catch(() => {});
    }
  }, [logado]);

  useEffect(() => {
    function aoClicarFora(e) {
      if (refAvatar.current && !refAvatar.current.contains(e.target)) setMenuAbertoAvatar(false);
    }
    if (menuAbertoAvatar) document.addEventListener("mousedown", aoClicarFora);
    return () => document.removeEventListener("mousedown", aoClicarFora);
  }, [menuAbertoAvatar]);

  if (!logado) {
    return <TelaAutenticacao aoAutenticar={() => setLogado(true)} />;
  }

  function sair() {
    api.logout();
    setLogado(false);
    setPerfil(null);
  }

  function navegarPara(id) {
    setPagina(id);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const paginas = {
    ferramentas: <Ferramentas perfil={perfil} aoNavegar={navegarPara} />,
    dashboard: <Dashboard />,
    criterios: <Criterios />,
    favoritos: <Favoritos />,
    pipeline: <Pipeline />,
    documentos: <Documentos perfil={perfil} />,
    equipe: <Equipe perfil={perfil} />,
    notificacoes: <Notificacoes perfil={perfil} aoAtualizarPerfil={setPerfil} />,
    indicadores: <Indicadores />,
  };

  return (
    <div className="app-shell">
      <header className="navbar-topo">
        <button className="navbar-marca" onClick={() => navegarPara("ferramentas")}>
          <LogoCompacto />
        </button>

        <nav className="navbar-abas">
          {ITENS_NAV.map(({ id, rotulo, Icone }) => (
            <button
              key={id}
              className={pagina === id ? "ativo" : ""}
              onClick={() => navegarPara(id)}
              aria-label={rotulo}
              title={rotulo}
            >
              <Icone size={15} strokeWidth={2} />
              <span>{rotulo}</span>
            </button>
          ))}
        </nav>

        <div className="navbar-acoes">
          <button className="botao-ajuda-navbar" onClick={() => setAjudaAberta(true)}>
            <HelpCircle size={15} strokeWidth={2} /> <span>Ajuda</span>
          </button>

          <PainelAlertas
            aberto={alertasAbertos}
            aoAlternar={() => setAlertasAbertos((v) => !v)}
            aoFechar={() => setAlertasAbertos(false)}
          />

          <div className="navbar-item-wrap" ref={refAvatar}>
            <button className="navbar-avatar-botao" onClick={() => setMenuAbertoAvatar((v) => !v)}>
              <span className="navbar-avatar-circulo">{iniciais(perfil?.email)}</span>
              <ChevronDown size={13} strokeWidth={2.4} />
            </button>

            {menuAbertoAvatar && (
              <div className="painel-flutuante painel-avatar">
                <div className="painel-avatar-email">{perfil?.email}</div>
                {perfil?.papel && (
                  <div className="painel-avatar-papel">
                    {perfil.papel === "owner" ? "Dono da conta" : "Membro"}
                  </div>
                )}
                <button
                  className="painel-avatar-notificacoes"
                  onClick={() => {
                    setMenuAbertoAvatar(false);
                    navegarPara("notificacoes");
                  }}
                >
                  <Bell size={13} strokeWidth={2} /> Notificações
                </button>
                <button className="painel-avatar-sair" onClick={sair}>
                  <LogOut size={13} strokeWidth={2} /> Sair da conta
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="conteudo">
        <div key={pagina} className="conteudo-pagina">
          <Suspense fallback={<EsqueletoPagina />}>{paginas[pagina]}</Suspense>
        </div>
      </main>

      <Rodape />

      {ajudaAberta && <PainelAjuda aoFechar={() => setAjudaAberta(false)} />}
    </div>
  );
}
