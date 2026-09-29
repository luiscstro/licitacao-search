// Marca "LicitTracker" — raposa com lupa (brandbook) e wordmark em Poppins.

import logoRaposa from "../assets/logo-raposa.png";

function Marca({ tamanho = 30 }) {
  return <img src={logoRaposa} alt="" width={tamanho} height={tamanho} className="logo-marca-img" />;
}

export function LogoCompacto({ comTagline = true }) {
  return (
    <span className="logo-compacto">
      <Marca tamanho={28} />
      <span className="logo-texto-wrap">
        <span className="logo-texto">
          <span className="licit">Licit</span>
          <span className="tracker">Tracker</span>
        </span>
        {comTagline && <span className="logo-tagline-mini">Licitações · PNCP</span>}
      </span>
    </span>
  );
}

export function LogoCompleto() {
  return (
    <div className="logo-completo">
      <Marca tamanho={54} />
      <div className="logo-texto grande">
        <span className="licit">Licit</span>
        <span className="tracker">Tracker</span>
      </div>
      <div className="logo-tagline">Plataforma de Licitações Online</div>
    </div>
  );
}
