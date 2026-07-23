import { useEffect, useState } from "react";
import { Star } from "lucide-react";
import { api } from "../api";
import CartaoLicitacao from "../components/CartaoLicitacao";

export default function Favoritos() {
  const [favoritos, setFavoritos] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  function carregar() {
    setCarregando(true);
    api
      .listarFavoritos()
      .then(setFavoritos)
      .catch((err) => setErro(err.message))
      .finally(() => setCarregando(false));
  }

  useEffect(() => {
    carregar();
  }, []);

  return (
    <div>
      <div className="cabecalho-pagina">
        <div>
          <span className="eyebrow">Guardados</span>
          <h1>Favoritos</h1>
          <div className="contagem">
            {carregando ? "carregando..." : `${favoritos.length} licitação(ões) favoritada(s)`}
          </div>
        </div>
      </div>

      {erro && <div className="erro-msg">{erro}</div>}

      {!carregando && favoritos.length === 0 && (
        <div className="estado-vazio">
          <Star strokeWidth={1.5} />
          <h3>Nenhum favorito ainda</h3>
          <p>Clique na estrela ☆ de qualquer licitação na tela "Licitações" para guardá-la aqui.</p>
        </div>
      )}

      {carregando && <div className="carregando">Carregando favoritos...</div>}

      {!carregando && favoritos.length > 0 && (
        <div className="grade-licitacoes">
          {favoritos.map((lic) => (
            <CartaoLicitacao key={lic.numero_controle} lic={lic} aoMudarFavorito={carregar} />
          ))}
        </div>
      )}
    </div>
  );
}