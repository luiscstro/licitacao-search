import { expect, test } from "@playwright/test";

// Ignora erros de console esperados quando o backend (127.0.0.1:8000) não
// está rodando — essas mensagens de rede não indicam um bug de frontend.
function ehErroDeRedeEsperado(texto) {
  return texto.includes("Failed to fetch") || texto.includes("127.0.0.1:8000");
}

test.describe("Login / navegação básica", () => {
  test("mostra a tela de login para um visitante não autenticado", async ({ page }) => {
    const errosDeConsole = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errosDeConsole.push(msg.text());
    });

    await page.goto("/");

    await expect(page.getByText("Entrar na conta")).toBeVisible();

    const errosInesperados = errosDeConsole.filter((texto) => !ehErroDeRedeEsperado(texto));
    expect(errosInesperados).toEqual([]);
  });

  test("mostra a navegação principal quando há um token salvo e navega entre abas", async ({ page }) => {
    const errosDeConsole = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errosDeConsole.push(msg.text());
    });

    await page.goto("/");
    await page.evaluate(() => {
      window.localStorage.setItem("token", "token-falso-para-teste-e2e");
    });
    await page.reload();

    const nav = page.getByRole("navigation");
    await expect(nav.getByText("Licitações")).toBeVisible();

    await nav.getByText("Meus critérios").click();

    const errosInesperados = errosDeConsole.filter((texto) => !ehErroDeRedeEsperado(texto));
    expect(errosInesperados).toEqual([]);
  });
});
