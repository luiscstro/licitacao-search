import { useState } from "react";
import { api } from "../api";

// Se o link de convite tiver "?convite=TOKEN" na URL, já pega automaticamente
function pegarConviteDaUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("convite") || "";
}

export default function TelaAutenticacao({ aoAutenticar }) {
  const conviteDaUrl = pegarConviteDaUrl();
  const [modo, setModo] = useState(conviteDaUrl ? "cadastro" : "login"); // "login" | "cadastro"
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [nomeEmpresa, setNomeEmpresa] = useState("");
  const [tokenConvite, setTokenConvite] = useState(conviteDaUrl);
  const [mostrarCampoConvite, setMostrarCampoConvite] = useState(!!conviteDaUrl);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function enviar(e) {
    e.preventDefault();
    setErro("");
    setCarregando(true);
    try {
      if (modo === "cadastro") {
        await api.registrar({ email, senha, nomeEmpresa, tokenConvite });
      }
      await api.login({ email, senha });
      aoAutenticar();
    } catch (err) {
      setErro(err.message || "Não foi possível continuar. Tente de novo.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-lado-marca">
        <div className="marca">
          Achador de
          <br />
          Licitações
        </div>
        <p className="tagline">
          Todo dia, uma leitura das novas licitações do PNCP — só as que
          realmente batem com o seu negócio chegam até você.
        </p>
        <div className="protocolo-exemplo">
          PNCP-59949362000176-1-000051/2026
        </div>
      </div>

      <div className="auth-lado-form">
        <h2>{modo === "login" ? "Entrar na conta" : "Criar conta"}</h2>
        <p className="subtitulo">
          {tokenConvite
            ? "Você foi convidado para entrar numa equipe. Complete seu cadastro abaixo."
            : modo === "login"
            ? "Acesse seu painel de licitações filtradas."
            : "Leva menos de um minuto para começar."}
        </p>

        {erro && <div className="erro-msg">{erro}</div>}

        <form onSubmit={enviar}>
          {modo === "cadastro" && !tokenConvite && (
            <div className="campo">
              <label htmlFor="empresa">Nome da empresa</label>
              <input
                id="empresa"
                type="text"
                value={nomeEmpresa}
                onChange={(e) => setNomeEmpresa(e.target.value)}
                placeholder="Ex: Apoio & Cia Serviços LTDA"
              />
              <span className="ajuda">Você vai virar o administrador dessa conta.</span>
            </div>
          )}

          <div className="campo">
            <label htmlFor="email">E-mail</label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="voce@empresa.com"
            />
          </div>

          <div className="campo">
            <label htmlFor="senha">Senha</label>
            <input
              id="senha"
              type="password"
              required
              minLength={6}
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              placeholder="Mínimo de 6 caracteres"
            />
          </div>

          {modo === "cadastro" && !conviteDaUrl && (
            <div className="campo">
              {!mostrarCampoConvite ? (
                <button
                  type="button"
                  className="auth-troca"
                  style={{ all: "unset", cursor: "pointer", fontSize: 13, color: "var(--slate)", textDecoration: "underline" }}
                  onClick={() => setMostrarCampoConvite(true)}
                >
                  Tenho um código de convite de equipe
                </button>
              ) : (
                <>
                  <label htmlFor="convite">Código de convite (opcional)</label>
                  <input
                    id="convite"
                    type="text"
                    value={tokenConvite}
                    onChange={(e) => setTokenConvite(e.target.value)}
                    placeholder="Cole aqui o código que você recebeu"
                  />
                </>
              )}
            </div>
          )}

          <button type="submit" className="botao primario" disabled={carregando} style={{ width: "100%" }}>
            {carregando ? "Aguarde..." : modo === "login" ? "Entrar" : "Criar conta"}
          </button>
        </form>

        {!conviteDaUrl && (
          <div className="auth-troca">
            {modo === "login" ? (
              <>
                Ainda não tem conta?{" "}
                <button onClick={() => { setModo("cadastro"); setErro(""); }}>Criar agora</button>
              </>
            ) : (
              <>
                Já tem conta?{" "}
                <button onClick={() => { setModo("login"); setErro(""); }}>Entrar</button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}