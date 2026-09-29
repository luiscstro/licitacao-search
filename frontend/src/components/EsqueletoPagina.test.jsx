import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import EsqueletoPagina from "./EsqueletoPagina";

describe("EsqueletoPagina", () => {
  it("renderiza o cartão de título e 3 cartões de lista como placeholder", () => {
    const { container } = render(<EsqueletoPagina />);
    expect(container.querySelectorAll(".esqueleto-cartao")).toHaveLength(4);
    expect(container.querySelector(".grade-licitacoes").children).toHaveLength(3);
  });
});
