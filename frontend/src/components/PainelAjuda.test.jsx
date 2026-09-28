import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PainelAjuda from "./PainelAjuda";

describe("PainelAjuda", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("mostra todos os tópicos de ajuda", () => {
    render(<PainelAjuda aoFechar={() => {}} />);
    expect(screen.getByText("Central de ajuda")).toBeInTheDocument();
    expect(screen.getByText("Como funciona a pontuação")).toBeInTheDocument();
    expect(screen.getByText("Como montar um bom critério")).toBeInTheDocument();
    expect(screen.getByText("Busca livre × critérios salvos")).toBeInTheDocument();
    expect(screen.getByText("Favoritos e alertas de prazo")).toBeInTheDocument();
  });

  it("chama aoFechar (após a animação de saída) ao clicar no botão de fechar", () => {
    const aoFechar = vi.fn();
    render(<PainelAjuda aoFechar={aoFechar} />);

    fireEvent.click(screen.getByLabelText("Fechar"));
    expect(aoFechar).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(aoFechar).toHaveBeenCalledTimes(1);
  });

  it("fecha ao clicar fora do modal (no overlay)", () => {
    const aoFechar = vi.fn();
    const { container } = render(<PainelAjuda aoFechar={aoFechar} />);

    fireEvent.click(container.querySelector(".painel-overlay"));
    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(aoFechar).toHaveBeenCalledTimes(1);
  });

  it("não fecha ao clicar dentro do conteúdo do modal", () => {
    const aoFechar = vi.fn();
    render(<PainelAjuda aoFechar={aoFechar} />);

    fireEvent.click(screen.getByText("Central de ajuda"));
    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(aoFechar).not.toHaveBeenCalled();
  });
});
