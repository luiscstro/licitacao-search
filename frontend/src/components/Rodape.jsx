import { useState } from "react";
import PainelLegal from "./PainelLegal";

const ANO = new Date().getFullYear();

export default function Rodape() {
  const [painelAberto, setPainelAberto] = useState(null); // null | "termos" | "privacidade" | "cookies"

  return (
    <footer className="rodape">
      <div className="rodape-linha">
        <span className="rodape-marca">
          <span className="licit">Licit</span>
          <span className="tracker">Tracker</span>
        </span>
        <span className="rodape-separador" aria-hidden="true">
          ·
        </span>
        <span>© {ANO}</span>
        <span className="rodape-separador" aria-hidden="true">
          ·
        </span>
        <span>Dados públicos via PNCP</span>
      </div>

      <nav className="rodape-links" aria-label="Links legais">
        <button type="button" onClick={() => setPainelAberto("termos")}>
          Termos de Uso
        </button>
        <button type="button" onClick={() => setPainelAberto("privacidade")}>
          Privacidade
        </button>
        <button type="button" onClick={() => setPainelAberto("cookies")}>
          Cookies
        </button>
      </nav>

      {painelAberto && <PainelLegal tipo={painelAberto} aoFechar={() => setPainelAberto(null)} />}
    </footer>
  );
}
