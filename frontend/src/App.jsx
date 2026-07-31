import { useEffect, useRef, useState } from "react";
import { Search, Star, ListChecks, Users2, LogOut, HelpCircle, ChevronDown, LayoutGrid } from "lucide-react";
import { api } from "./api";
import { LogoCompacto } from "./components/Logo";
import TelaAutenticacao from "./pages/TelaAutenticacao";
import Ferramentas from "./pages/Ferramentas";
import Dashboard from "./pages/Dashboard";
import Criterios from "./pages/Criterios";
import Favoritos from "./pages/Favoritos";
import Equipe from "./pages/Equipe";
import PainelAlertas from "./components/PainelAlertas";
import PainelAjuda from "./components/PainelAjuda";

const ITENS_NAV = [
  { id: "ferramentas", rotulo: "Ferramentas", Icone: LayoutGrid },
  { id: "dashboard", rotulo: "Licitações", Icone: Search },
  { id: "criterios", rotulo: "Meus critérios", Icone: ListChecks },
  { id: "favoritos", rotulo: "Favoritos", Icone: Star },
  { id: "equipe", rotulo: "Minha equipe", Icone: Users2 },
];

function iniciais(email) {
  if (!email) return "?";
  const nome = email.split("@")[0];
  const partes = nome.split(/[._-]/).filter(Boolean);
  if (partes.length >= 2) return (partes[0][0] + partes[1][0]).toUpperCase();
  return nome.slice(0, 2).toUpperCase();
}

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
      api.meuPerfil().then(setPerfil).catch(() => {});
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
    equipe: <Equipe perfil={perfil} />,
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
                  <div className="painel-avatar-papel">{perfil.papel === "owner" ? "Dono da conta" : "Membro"}</div>
                )}
                <button className="painel-avatar-sair" onClick={sair}>
                  <LogOut size={13} strokeWidth={2} /> Sair da conta
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="conteudo">{paginas[pagina]}</main>

      {ajudaAberta && <PainelAjuda aoFechar={() => setAjudaAberta(false)} />}
    </div>
  );
}
