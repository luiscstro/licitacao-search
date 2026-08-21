import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { diasAte, diasRestantes, formatarValor, urgente } from "./data";

describe("formatarValor", () => {
  it("formata um número como moeda em pt-BR (BRL)", () => {
    expect(formatarValor(1500)).toBe(
      new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(1500)
    );
  });

  it("formata valores decimais corretamente", () => {
    expect(formatarValor(1234.56)).toBe(
      new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(1234.56)
    );
  });

  it("retorna 'não informado' para 0", () => {
    expect(formatarValor(0)).toBe("não informado");
  });

  it("retorna 'não informado' para null", () => {
    expect(formatarValor(null)).toBe("não informado");
  });

  it("retorna 'não informado' para undefined", () => {
    expect(formatarValor(undefined)).toBe("não informado");
  });

  it("retorna 'não informado' para string vazia", () => {
    expect(formatarValor("")).toBe("não informado");
  });
});

describe("funções relativas a data (diasAte, diasRestantes, urgente)", () => {
  beforeEach(() => {
    // Fixa "hoje" em 2026-08-19 para tornar os testes determinísticos.
    // Importante: usamos meia-noite UTC (mesmo formato que "new Date('YYYY-MM-DD')"
    // usa para parsear as datas de entrada) para que o deslocamento de fuso horário
    // local aplicado por `setHours(0,0,0,0)` afete "hoje" e as datas de entrada de
    // forma idêntica — mantendo a diferença em dias correta em qualquer timezone.
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-19T00:00:00.000Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("diasRestantes", () => {
    it("retorna null quando a data não é informada", () => {
      expect(diasRestantes(null)).toBeNull();
      expect(diasRestantes(undefined)).toBeNull();
      expect(diasRestantes("")).toBeNull();
    });

    it("retorna 0 para a data de hoje", () => {
      expect(diasRestantes("2026-08-19")).toBe(0);
    });

    it("retorna um número positivo para datas futuras", () => {
      expect(diasRestantes("2026-08-24")).toBe(5);
    });

    it("retorna um número negativo para datas passadas", () => {
      expect(diasRestantes("2026-08-14")).toBe(-5);
    });
  });

  describe("diasAte", () => {
    it("retorna '—' quando a data não é informada", () => {
      expect(diasAte(null)).toBe("—");
      expect(diasAte(undefined)).toBe("—");
      expect(diasAte("")).toBe("—");
    });

    it("retorna 'hoje' para a data de hoje", () => {
      expect(diasAte("2026-08-19")).toBe("hoje");
    });

    it("retorna 'em Nd' para datas futuras", () => {
      expect(diasAte("2026-08-24")).toBe("em 5d");
    });

    it("retorna 'venceu há Nd' para datas passadas", () => {
      expect(diasAte("2026-08-14")).toBe("venceu há 5d");
    });
  });

  describe("urgente", () => {
    it("é falso quando a data não é informada", () => {
      expect(urgente(null)).toBe(false);
      expect(urgente(undefined)).toBe(false);
    });

    it("é verdadeiro para hoje (0 dias)", () => {
      expect(urgente("2026-08-19")).toBe(true);
    });

    it("é verdadeiro até 3 dias no futuro (limite inclusivo)", () => {
      expect(urgente("2026-08-22")).toBe(true);
    });

    it("é falso a partir de 4 dias no futuro", () => {
      expect(urgente("2026-08-23")).toBe(false);
    });

    it("é falso para datas já vencidas", () => {
      expect(urgente("2026-08-18")).toBe(false);
    });
  });
});
