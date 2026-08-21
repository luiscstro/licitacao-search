import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Carimbo from "./Carimbo";

describe("Carimbo", () => {
  it("renderiza os filhos passados como children", () => {
    render(<Carimbo cor="urgente">Vence hoje</Carimbo>);
    expect(screen.getByText("Vence hoje")).toBeInTheDocument();
  });

  it("aplica a classe CSS correspondente à cor informada", () => {
    render(<Carimbo cor="urgente">Vence hoje</Carimbo>);
    expect(screen.getByText("Vence hoje")).toHaveClass("carimbo", "urgente");
  });

  it("usa 'neutro' como cor padrão quando nenhuma é informada", () => {
    render(<Carimbo>Sem cor definida</Carimbo>);
    expect(screen.getByText("Sem cor definida")).toHaveClass("carimbo", "neutro");
  });
});
