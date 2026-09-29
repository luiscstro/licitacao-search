import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

function respostaJson(corpo, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => corpo,
  };
}

describe("api", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal("fetch", vi.fn());
    // jsdom's window.location não permite espionar `reload` diretamente
    // (propriedade não configurável) — substitui o objeto location inteiro.
    vi.stubGlobal("location", { ...window.location, reload: vi.fn() });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  describe("login", () => {
    it("guarda access_token e refresh_token no localStorage", async () => {
      fetch.mockResolvedValueOnce(
        respostaJson({ access_token: "acc-1", refresh_token: "ref-1", token_type: "bearer" })
      );

      await api.login({ email: "a@x.com", senha: "123456" });

      expect(localStorage.getItem("token")).toBe("acc-1");
      expect(localStorage.getItem("refreshToken")).toBe("ref-1");
    });

    it("lança erro com a mensagem do backend quando as credenciais são rejeitadas", async () => {
      fetch.mockResolvedValueOnce(respostaJson({ detail: "E-mail ou senha incorretos" }, 401));
      await expect(api.login({ email: "a@x.com", senha: "errada" })).rejects.toThrow(
        "E-mail ou senha incorretos"
      );
      expect(localStorage.getItem("token")).toBeNull();
    });
  });

  describe("logout", () => {
    it("limpa os tokens localmente e revoga o refresh token no backend", () => {
      localStorage.setItem("token", "acc-1");
      localStorage.setItem("refreshToken", "ref-1");
      fetch.mockResolvedValueOnce(respostaJson(null, 204));

      api.logout();

      expect(localStorage.getItem("token")).toBeNull();
      expect(localStorage.getItem("refreshToken")).toBeNull();
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/auth/logout"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ refresh_token: "ref-1" }),
        })
      );
    });

    it("não chama /auth/logout quando não há refresh token salvo", () => {
      api.logout();
      expect(fetch).not.toHaveBeenCalled();
    });
  });

  describe("renovação automática em 401", () => {
    it("renova a sessão e repete a chamada original quando o access token expirou", async () => {
      localStorage.setItem("token", "acc-velho");
      localStorage.setItem("refreshToken", "ref-1");

      fetch
        .mockResolvedValueOnce(respostaJson({ detail: "expirado" }, 401)) // 1a chamada, token velho
        .mockResolvedValueOnce(
          respostaJson({ access_token: "acc-novo", refresh_token: "ref-2", token_type: "bearer" })
        ) // POST /auth/refresh
        .mockResolvedValueOnce(respostaJson({ email: "a@x.com" }, 200)); // repetição da chamada original

      const perfil = await api.meuPerfil();

      expect(perfil).toEqual({ email: "a@x.com" });
      expect(localStorage.getItem("token")).toBe("acc-novo");
      expect(localStorage.getItem("refreshToken")).toBe("ref-2");
      expect(fetch).toHaveBeenCalledTimes(3);
      expect(fetch.mock.calls[0][1].headers.Authorization).toBe("Bearer acc-velho");
      expect(fetch.mock.calls[2][1].headers.Authorization).toBe("Bearer acc-novo");
    });

    it("desloga (limpa tokens e recarrega a página) quando a renovação também falha", async () => {
      localStorage.setItem("token", "acc-velho");
      localStorage.setItem("refreshToken", "ref-1");

      fetch
        .mockResolvedValueOnce(respostaJson({ detail: "expirado" }, 401))
        .mockResolvedValueOnce(respostaJson({ detail: "refresh invalido" }, 401));

      await expect(api.meuPerfil()).rejects.toThrow("Sessão expirada. Faça login novamente.");

      expect(localStorage.getItem("token")).toBeNull();
      expect(localStorage.getItem("refreshToken")).toBeNull();
      expect(window.location.reload).toHaveBeenCalled();
    });

    it("desloga direto (sem tentar renovar) quando não há refresh token salvo", async () => {
      localStorage.setItem("token", "acc-velho");
      fetch.mockResolvedValueOnce(respostaJson({ detail: "expirado" }, 401));

      await expect(api.meuPerfil()).rejects.toThrow("Sessão expirada. Faça login novamente.");
      expect(fetch).toHaveBeenCalledTimes(1); // não tentou /auth/refresh
    });

    it("deduplica renovações concorrentes: duas chamadas com 401 ao mesmo tempo disparam só um /auth/refresh", async () => {
      localStorage.setItem("token", "acc-velho");
      localStorage.setItem("refreshToken", "ref-1");

      fetch
        .mockResolvedValueOnce(respostaJson({}, 401)) // chamada original #1
        .mockResolvedValueOnce(respostaJson({}, 401)) // chamada original #2
        .mockResolvedValueOnce(
          respostaJson({ access_token: "acc-novo", refresh_token: "ref-2", token_type: "bearer" })
        ) // único /auth/refresh
        .mockResolvedValueOnce(respostaJson({ ok: 1 }, 200)) // repetição #1
        .mockResolvedValueOnce(respostaJson({ ok: 2 }, 200)); // repetição #2

      const [r1, r2] = await Promise.all([api.meuPerfil(), api.listarCriterios()]);

      expect(r1).toEqual({ ok: 1 });
      expect(r2).toEqual({ ok: 2 });
      expect(fetch).toHaveBeenCalledTimes(5);
      const chamadasDeRefresh = fetch.mock.calls.filter(([url]) => url.includes("/auth/refresh"));
      expect(chamadasDeRefresh).toHaveLength(1);
    });
  });
});
