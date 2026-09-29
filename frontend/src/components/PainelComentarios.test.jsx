import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../api";
import PainelComentarios from "./PainelComentarios";

vi.mock("../api", () => ({
  api: { listarComentarios: vi.fn(), criarComentario: vi.fn() },
}));

describe("PainelComentarios", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("busca e mostra os comentários da licitação ao montar", async () => {
    api.listarComentarios.mockResolvedValue([
      { id: 1, texto: "Primeiro comentário", autor_email: "a@x.com", criado_em: "2026-01-01T10:00:00" },
    ]);
    render(<PainelComentarios numeroControle="PNCP-1" aoFechar={() => {}} />);

    expect(api.listarComentarios).toHaveBeenCalledWith("PNCP-1");
    expect(await screen.findByText("Primeiro comentário")).toBeInTheDocument();
  });

  it("mostra mensagem de vazio quando não há comentários", async () => {
    api.listarComentarios.mockResolvedValue([]);
    render(<PainelComentarios numeroControle="PNCP-1" aoFechar={() => {}} />);
    expect(
      await screen.findByText("Nenhum comentário ainda. Seja o primeiro da equipe a anotar algo aqui.")
    ).toBeInTheDocument();
  });

  it("envia um novo comentário e recarrega a lista", async () => {
    api.listarComentarios
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        { id: 2, texto: "Novo comentário", autor_email: "a@x.com", criado_em: "2026-01-01T10:00:00" },
      ]);
    api.criarComentario.mockResolvedValue({});

    render(<PainelComentarios numeroControle="PNCP-1" aoFechar={() => {}} />);
    await screen.findByText("Nenhum comentário ainda. Seja o primeiro da equipe a anotar algo aqui.");

    fireEvent.change(screen.getByPlaceholderText("Escreva uma anotação..."), {
      target: { value: "Novo comentário" },
    });
    fireEvent.click(screen.getByRole("button", { name: /enviar/i }));

    await waitFor(() => expect(api.criarComentario).toHaveBeenCalledWith("PNCP-1", "Novo comentário"));
    expect(await screen.findByText("Novo comentário")).toBeInTheDocument();
  });

  it("não envia comentário em branco", async () => {
    api.listarComentarios.mockResolvedValue([]);
    render(<PainelComentarios numeroControle="PNCP-1" aoFechar={() => {}} />);
    await screen.findByText("Nenhum comentário ainda. Seja o primeiro da equipe a anotar algo aqui.");

    fireEvent.click(screen.getByRole("button", { name: /enviar/i }));
    expect(api.criarComentario).not.toHaveBeenCalled();
  });

  it("mostra mensagem de erro quando o envio falha", async () => {
    api.listarComentarios.mockResolvedValue([]);
    api.criarComentario.mockRejectedValue(new Error("Falha ao enviar"));
    render(<PainelComentarios numeroControle="PNCP-1" aoFechar={() => {}} />);
    await screen.findByText("Nenhum comentário ainda. Seja o primeiro da equipe a anotar algo aqui.");

    fireEvent.change(screen.getByPlaceholderText("Escreva uma anotação..."), { target: { value: "Oi" } });
    fireEvent.click(screen.getByRole("button", { name: /enviar/i }));

    expect(await screen.findByText("Falha ao enviar")).toBeInTheDocument();
  });
});
