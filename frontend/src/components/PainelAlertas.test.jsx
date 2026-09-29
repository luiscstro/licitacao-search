import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../api";
import PainelAlertas from "./PainelAlertas";

vi.mock("../api", () => ({
  api: { listarFavoritos: vi.fn() },
}));

function isoDaquiA(dias) {
  const data = new Date();
  data.setDate(data.getDate() + dias);
  return data.toISOString();
}

function favorito(overrides = {}) {
  return {
    numero_controle: "PNCP-1",
    orgao: "Órgão Teste",
    cidade: "Cidade Teste",
    link_edital: "",
    data_encerramento_proposta: isoDaquiA(2),
    ...overrides,
  };
}

describe("PainelAlertas", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("não busca favoritos enquanto o painel está fechado", () => {
    render(<PainelAlertas aberto={false} aoAlternar={() => {}} aoFechar={() => {}} />);
    expect(api.listarFavoritos).not.toHaveBeenCalled();
  });

  it("mostra apenas favoritos com prazo de até 5 dias, ordenados do mais urgente pro menos urgente", async () => {
    api.listarFavoritos.mockResolvedValue([
      favorito({
        numero_controle: "PNCP-longe",
        orgao: "Órgão Longe",
        data_encerramento_proposta: isoDaquiA(40),
      }),
      favorito({
        numero_controle: "PNCP-perto",
        orgao: "Órgão Perto",
        data_encerramento_proposta: isoDaquiA(4),
      }),
      favorito({
        numero_controle: "PNCP-hoje",
        orgao: "Órgão Hoje",
        data_encerramento_proposta: isoDaquiA(0),
      }),
    ]);

    render(<PainelAlertas aberto={true} aoAlternar={() => {}} aoFechar={() => {}} />);

    await waitFor(() => expect(api.listarFavoritos).toHaveBeenCalledTimes(1));

    expect(await screen.findByText("Órgão Hoje")).toBeInTheDocument();
    expect(screen.getByText("Órgão Perto")).toBeInTheDocument();
    expect(screen.queryByText("Órgão Longe")).not.toBeInTheDocument();

    const itens = screen.getAllByText(/Órgão (Hoje|Perto)/);
    expect(itens.map((el) => el.textContent)).toEqual(["Órgão Hoje", "Órgão Perto"]);
  });

  it("mostra mensagem de vazio quando nenhum favorito está com prazo apertado", async () => {
    api.listarFavoritos.mockResolvedValue([favorito({ data_encerramento_proposta: isoDaquiA(40) })]);
    render(<PainelAlertas aberto={true} aoAlternar={() => {}} aoFechar={() => {}} />);
    expect(await screen.findByText("Nenhum favorito com prazo apertado no momento.")).toBeInTheDocument();
  });

  it("mostra mensagem de erro quando a busca falha", async () => {
    api.listarFavoritos.mockRejectedValue(new Error("Falha ao buscar favoritos"));
    render(<PainelAlertas aberto={true} aoAlternar={() => {}} aoFechar={() => {}} />);
    expect(await screen.findByText("Falha ao buscar favoritos")).toBeInTheDocument();
  });
});
