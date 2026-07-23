import { useEffect, useState } from "react";
import { Search, Star, ListChecks, Users2, LogOut } from "lucide-react";
import { api } from "./api";
import TelaAutenticacao from "./pages/TelaAutenticacao";
import Dashboard from "./pages/Dashboard";
import Criterios from "./pages/Criterios";
import Favoritos from "./pages/Favoritos";
import Equipe from "./pages/Equipe";

const ITENS_NAV = [
  { id: "dashboard", rotulo: "Licitações", Icone: Search },
  { id: "favoritos", rotulo: "Favoritos", Icone: Star },
  { id: "criterios", rotulo: "Meus critérios", Icone: ListChecks },
  { id: "equipe", rotulo: "Minha equipe", Icone: Users2 },
];

export default function App() {
  const [logado, setLogado] = useState(api.estaLogado());
  const [pagina, setPagina] = useState("dashboard");
  const [perfil, setPerfil] = useState(null);

  useEffect(() => {
    if (logado) {
      api.meuPerfil().then(setPerfil).catch(() => {});
    }
  }, [logado]);

  if (!logado) {
    return <TelaAutenticacao aoAutenticar={() => setLogado(true)} />;
  }

  function sair() {
    api.logout();
    setLogado(false);
    setPerfil(null);
  }

  const paginas = {
    dashboard: <Dashboard />,
    criterios: <Criterios />,
    favoritos: <Favoritos />,
    equipe: <Equipe perfil={perfil} />,
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="marca">Achador</div>
          <div className="subtitulo">Licitações · PNCP</div>
        </div>

        <nav className="sidebar-nav">
          {ITENS_NAV.map(({ id, rotulo, Icone }) => (
            <button key={id} className={pagina === id ? "ativo" : ""} onClick={() => setPagina(id)}>
              <Icone strokeWidth={2} />
              {rotulo}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          {perfil && <span className="email-usuario">{perfil.email}</span>}
          <button onClick={sair} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <LogOut size={13} strokeWidth={2} />
            Sair da conta
          </button>
        </div>
      </aside>

      <main className="conteudo">{paginas[pagina]}</main>
    </div>
  );
}