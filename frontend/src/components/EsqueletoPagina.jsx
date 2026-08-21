// Fallback do Suspense enquanto o código da página (lazy-loaded) baixa.
// Reaproveita o mesmo esqueleto de cartão usado nas listas, pra não haver
// um flash em branco entre trocar de aba e o conteúdo real aparecer.
export default function EsqueletoPagina() {
  return (
    <div>
      <div className="esqueleto-cartao" style={{ maxWidth: 320, marginBottom: 24 }}>
        <div className="esqueleto-linha curta" />
      </div>
      <div className="grade-licitacoes">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="esqueleto-cartao">
            <div className="esqueleto-linha curta" />
            <div className="esqueleto-linha media" />
            <div className="esqueleto-linha larga" />
          </div>
        ))}
      </div>
    </div>
  );
}
