// URL do backend. Em desenvolvimento, o backend roda em localhost:8000
// (uvicorn app.main:app --reload). Quando for hospedar de verdade, troque
// isso pela URL pública do backend (ou use uma variável de ambiente do Vite).
const API_BASE = "http://127.0.0.1:8000";

function pegarToken() {
  return localStorage.getItem("token");
}

function salvarToken(token) {
  localStorage.setItem("token", token);
}

function limparToken() {
  localStorage.removeItem("token");
}

async function requisicao(caminho, opcoes = {}) {
  const token = pegarToken();
  const headers = {
    ...(opcoes.headers || {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const resp = await fetch(`${API_BASE}${caminho}`, { ...opcoes, headers });

  if (resp.status === 401) {
    limparToken();
    window.location.reload();
    throw new Error("Sessão expirada. Faça login novamente.");
  }

  if (!resp.ok) {
    let detalhe = "Erro na requisição";
    try {
      const corpo = await resp.json();
      detalhe = corpo.detail || detalhe;
    } catch {
      // ignora se não vier JSON
    }
    throw new Error(detalhe);
  }

  if (resp.status === 204) return null;
  return resp.json();
}

export const api = {
  async registrar({ email, senha, nomeEmpresa }) {
    return requisicao("/auth/registrar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, senha, nome_empresa: nomeEmpresa || null }),
    });
  },

  async login({ email, senha }) {
    const form = new URLSearchParams();
    form.set("username", email);
    form.set("password", senha);

    const resp = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form.toString(),
    });

    if (!resp.ok) {
      const corpo = await resp.json().catch(() => ({}));
      throw new Error(corpo.detail || "E-mail ou senha incorretos");
    }

    const dados = await resp.json();
    salvarToken(dados.access_token);
    return dados;
  },

  logout() {
    limparToken();
  },

  estaLogado() {
    return !!pegarToken();
  },

  async meuPerfil() {
    return requisicao("/auth/me");
  },

  async listarCriterios() {
    return requisicao("/criterios");
  },

  async criarCriterio(dados) {
    return requisicao("/criterios", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(dados),
    });
  },

  async atualizarCriterio(id, dados) {
    return requisicao(`/criterios/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(dados),
    });
  },

  async deletarCriterio(id) {
    return requisicao(`/criterios/${id}`, { method: "DELETE" });
  },

  async listarLicitacoes(criterioId) {
    const query = criterioId ? `?criterio_id=${criterioId}` : "";
    return requisicao(`/licitacoes${query}`);
  },
};