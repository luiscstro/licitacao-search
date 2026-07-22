import { useEffect, useState } from "react";
import { api } from "./api";
import TelaAutenticacao from "./pages/TelaAutenticacao";
import Dashboard from "./pages/Dashboard";
import Criterios from "./pages/Criterios";
import Favoritos from "./pages/Favoritos";
import Equipe from "./pages/Equipe";

export default function App() {
  const [logado, setLogado] = useState(api.estaLogado());
  const [pagina, setPagina] = useState("dashboard"); // "dashboard" | "criterios" | "favoritos" | "equipe"
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
          <div className="marca">LicitTraker</div>
          <div className="subtitulo">Licitações · PNCP</div>
        </div>

        <nav className="sidebar-nav">
          <button className={pagina === "dashboard" ? "ativo" : ""} onClick={() => setPagina("dashboard")}>
            Licitações
          </button>
          <button className={pagina === "favoritos" ? "ativo" : ""} onClick={() => setPagina("favoritos")}>
            Favoritos
          </button>
          <button className={pagina === "criterios" ? "ativo" : ""} onClick={() => setPagina("criterios")}>
            Meus critérios
          </button>
          <button className={pagina === "equipe" ? "ativo" : ""} onClick={() => setPagina("equipe")}>
            Minha equipe
          </button>
        </nav>

        <div className="sidebar-footer">
          {perfil && <span>{perfil.email}</span>}
          <button onClick={sair}>Sair da conta</button>
        </div>
      </aside>

      <main className="conteudo">{paginas[pagina]}</main>
    </div>
  );
}