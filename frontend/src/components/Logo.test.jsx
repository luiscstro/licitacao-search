import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LogoCompacto, LogoCompleto } from "./Logo";

describe("LogoCompacto", () => {
  it("renderiza a marca 'LicitTracker'", () => {
    render(<LogoCompacto />);
    expect(screen.getByText("Licit")).toBeInTheDocument();
    expect(screen.getByText("Tracker")).toBeInTheDocument();
  });

  it("mostra a tagline por padrão", () => {
    render(<LogoCompacto />);
    expect(screen.getByText("Licitações · PNCP")).toBeInTheDocument();
  });

  it("omite a tagline quando comTagline é falso", () => {
    render(<LogoCompacto comTagline={false} />);
    expect(screen.queryByText("Licitações · PNCP")).not.toBeInTheDocument();
  });
});

describe("LogoCompleto", () => {
  it("renderiza a marca e a tagline completa", () => {
    render(<LogoCompleto />);
    expect(screen.getByText("Licit")).toBeInTheDocument();
    expect(screen.getByText("Tracker")).toBeInTheDocument();
    expect(screen.getByText("Plataforma de Licitações Online")).toBeInTheDocument();
  });
});
