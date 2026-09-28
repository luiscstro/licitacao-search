import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import NumeroAnimado from "./NumeroAnimado";

describe("NumeroAnimado", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("começa em 0 e anima até o valor final", () => {
    render(<NumeroAnimado valor={42} />);
    expect(screen.getByText("0")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(700);
    });
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("aplica a função de formatação ao valor exibido", () => {
    render(<NumeroAnimado valor={7} formatar={(n) => `R$ ${n}`} />);
    act(() => {
      vi.advanceTimersByTime(700);
    });
    expect(screen.getByText("R$ 7")).toBeInTheDocument();
  });

  it("trata valores não numéricos (undefined) como 0", () => {
    render(<NumeroAnimado valor={undefined} />);
    act(() => {
      vi.advanceTimersByTime(700);
    });
    expect(screen.getByText("0")).toBeInTheDocument();
  });
});
