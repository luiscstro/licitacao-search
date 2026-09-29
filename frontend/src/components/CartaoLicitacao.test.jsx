import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../api";
import CartaoLicitacao from "./CartaoLicitacao";

vi.mock("../api", () => ({
  api: { favoritar: vi.fn(), desfavoritar: vi.fn() },
}));

function licitacao(overrides = {}) {
  return {
    numero_controle: "PNCP-1",
    orgao: "Órgão Teste",
    cidade: "Cidade Teste",
    uf: "MA",
    objeto: "objeto de teste",
    valor_estimado: 1000,
    data_encerramento_proposta: null,
    link_edital: "",
    score: 0,
    favoritada: false,
    ...overrides,
  };
}

describe("CartaoLicitacao — favoritar", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("muda a estrela imediatamente (otimista), sem esperar a resposta da rede", async () => {
    let resolverChamada;
    api.favoritar.mockReturnValue(
      new Promise((resolve) => {
        resolverChamada = resolve;
      })
    );

    render(<CartaoLicitacao lic={licitacao()} />);
    const botao = screen.getByTitle("Favoritar");

    fireEvent.click(botao);

    // Muda na hora — não espera a promise de api.favoritar resolver.
    expect(screen.getByTitle("Remover dos favoritos")).toBeInTheDocument();

    resolverChamada();
    await screen.findByTitle("Remover dos favoritos");
  });

  it("reverte a estrela se a chamada falhar de verdade", async () => {
    api.favoritar.mockRejectedValue(new Error("falhou"));

    render(<CartaoLicitacao lic={licitacao()} />);
    fireEvent.click(screen.getByTitle("Favoritar"));

    expect(screen.getByTitle("Remover dos favoritos")).toBeInTheDocument();

    expect(await screen.findByTitle("Favoritar")).toBeInTheDocument();
  });

  it("desfavoritar também é otimista", async () => {
    api.desfavoritar.mockResolvedValue(undefined);

    render(<CartaoLicitacao lic={licitacao({ favoritada: true })} />);
    fireEvent.click(screen.getByTitle("Remover dos favoritos"));

    expect(screen.getByTitle("Favoritar")).toBeInTheDocument();
    await screen.findByTitle("Favoritar");
    expect(api.desfavoritar).toHaveBeenCalledWith("PNCP-1");
  });

  it("chama aoMudarFavorito só depois que a chamada tem sucesso", async () => {
    api.favoritar.mockResolvedValue(undefined);
    const aoMudarFavorito = vi.fn();

    render(<CartaoLicitacao lic={licitacao()} aoMudarFavorito={aoMudarFavorito} />);
    fireEvent.click(screen.getByTitle("Favoritar"));

    expect(aoMudarFavorito).not.toHaveBeenCalled();
    await screen.findByTitle("Remover dos favoritos");
    expect(aoMudarFavorito).toHaveBeenCalledTimes(1);
  });
});
