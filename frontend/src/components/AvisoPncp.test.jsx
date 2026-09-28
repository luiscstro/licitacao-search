import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../api";
import AvisoPncp from "./AvisoPncp";

vi.mock("../api", () => ({
  api: { statusPncp: vi.fn() },
}));

function estado(overrides = {}) {
  return {
    ultima_execucao_em: null,
    ultima_execucao_com_sucesso: null,
    ultima_coleta_com_sucesso_em: null,
    horas_desde_ultima_coleta_com_sucesso: null,
    pncp_instavel: false,
    dados_desatualizados: false,
    ...overrides,
  };
}

describe("AvisoPncp", () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it("não mostra nada enquanto o status ainda não chegou, nem quando está tudo normal", async () => {
    api.statusPncp.mockResolvedValue(estado());
    const { container } = render(<AvisoPncp />);

    expect(container.querySelector(".aviso-pncp")).not.toBeInTheDocument();
    await vi.waitFor(() => expect(api.statusPncp).toHaveBeenCalledTimes(1));
    expect(container.querySelector(".aviso-pncp")).not.toBeInTheDocument();
  });

  it("mostra o aviso de instabilidade do PNCP quando a última execução falhou", async () => {
    api.statusPncp.mockResolvedValue(
      estado({ pncp_instavel: true, dados_desatualizados: true, ultima_execucao_em: "2026-09-28T10:00:00" })
    );
    render(<AvisoPncp />);

    const aviso = await screen.findByText(/apresentou instabilidade/i);
    expect(aviso).toBeInTheDocument();
    expect(screen.getByText(/não é uma falha da nossa plataforma/i)).toBeInTheDocument();
  });

  it("mostra o aviso neutro de dados desatualizados quando não há falha registrada, mas faz tempo", async () => {
    api.statusPncp.mockResolvedValue(
      estado({ dados_desatualizados: true, ultima_coleta_com_sucesso_em: "2026-09-26T08:00:00" })
    );
    render(<AvisoPncp />);

    expect(
      await screen.findByText(/não conseguimos confirmar uma coleta recente e bem-sucedida/i)
    ).toBeInTheDocument();
    expect(screen.queryByText(/apresentou instabilidade/i)).not.toBeInTheDocument();
  });

  it("prioriza o aviso de instabilidade quando os dois sinalizadores vêm marcados", async () => {
    api.statusPncp.mockResolvedValue(estado({ pncp_instavel: true, dados_desatualizados: true }));
    render(<AvisoPncp />);

    expect(await screen.findByText(/apresentou instabilidade/i)).toBeInTheDocument();
    expect(screen.queryByText(/não conseguimos confirmar/i)).not.toBeInTheDocument();
  });

  it("ignora silenciosamente uma falha ao buscar o status (não quebra a página)", async () => {
    api.statusPncp.mockRejectedValue(new Error("falha de rede"));
    const { container } = render(<AvisoPncp />);

    await vi.waitFor(() => expect(api.statusPncp).toHaveBeenCalledTimes(1));
    expect(container.querySelector(".aviso-pncp")).not.toBeInTheDocument();
  });

  it("reconfere o status periodicamente", async () => {
    vi.useFakeTimers();
    api.statusPncp.mockResolvedValue(estado());
    render(<AvisoPncp />);

    await act(async () => {
      await Promise.resolve();
    });
    expect(api.statusPncp).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10 * 60 * 1000);
    });
    expect(api.statusPncp).toHaveBeenCalledTimes(2);
  });
});
