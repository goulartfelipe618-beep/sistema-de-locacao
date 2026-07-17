import { test, expect } from "@playwright/test";

test.describe("Login — formulário crítico", () => {
  test("renderiza labels, ajuda e legenda de obrigatórios", async ({ page }) => {
    await page.goto("/login");

    await expect(page.getByRole("heading", { name: "Sistema de Locação" })).toBeVisible();
    await expect(page.getByLabel("E-mail")).toBeVisible();
    await expect(page.getByLabel("Senha")).toBeVisible();
    await expect(page.getByText("E-mail de acesso ao painel administrativo.")).toBeVisible();
    await expect(page.getByText("* Campos obrigatórios")).toBeVisible();
    await expect(page.getByRole("button", { name: "Entrar" })).toBeEnabled();
  });

  test("campos obrigatórios bloqueiam submit vazio", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: "Entrar" }).click();
    await expect(page).toHaveURL(/\/login/);
  });

  test("carrega form-engine.js", async ({ page }) => {
    await page.goto("/login");
    const loaded = await page.evaluate(() => typeof (window as { ErpForms?: unknown }).ErpForms !== "undefined");
    expect(loaded).toBe(true);
  });
});
