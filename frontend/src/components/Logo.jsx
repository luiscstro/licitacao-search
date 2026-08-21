// Marca "LicitTracker" — ícone recriado em SVG a partir do brandbook
// (quadrado arredondado + check dourado) e wordmark em Poppins.

function Marca({ tamanho = 30 }) {
  return (
    <svg
      width={tamanho}
      height={tamanho}
      viewBox="0 0 40 40"
      fill="none"
      aria-hidden="true"
      className="logo-marca-svg"
    >
      <rect x="2" y="2" width="36" height="36" rx="10" stroke="var(--selo-gold)" strokeWidth="2.25" />
      <path
        d="M11.5 20.5L16.5 25.5L28.5 13.5"
        stroke="var(--selo-gold)"
        strokeWidth="3.25"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
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
