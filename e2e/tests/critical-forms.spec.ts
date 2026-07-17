import { test, expect } from "@playwright/test";

const CRITICAL_ROUTES = [
  { path: "/cadastros/clientes/novo", legend: "Cliente" },
  { path: "/locacoes/contratos/novo", legend: "Contrato" },
  { path: "/financeiro/receber/novo", legend: "Receber" },
  { path: "/fiscal/nfse/novo", legend: "NFS" },
  { path: "/comercial/propostas/novo", legend: "Proposta" },
];

test.describe("Formulários críticos — guarda de autenticação", () => {
  for (const route of CRITICAL_ROUTES) {
    test(`redireciona anônimo: ${route.path}`, async ({ page }) => {
      const response = await page.goto(route.path);
      expect(response?.status()).toBeLessThan(500);
      await expect(page).toHaveURL(/\/login/);
    });
  }
});

test.describe("Formulários críticos — autenticado (opcional)", () => {
  const email = process.env.E2E_ADMIN_EMAIL;
  const password = process.env.E2E_ADMIN_PASSWORD;
  test.skip(!email || !password, "Defina E2E_ADMIN_EMAIL e E2E_ADMIN_PASSWORD para E2E autenticado");

  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("E-mail").fill(email!);
    await page.getByLabel("Senha").fill(password!);
    await page.getByRole("button", { name: "Entrar" }).click();
    await page.waitForURL((url) => !url.pathname.endsWith("/login"), { timeout: 15_000 });
  });

  for (const route of CRITICAL_ROUTES) {
    test(`formulário acessível: ${route.path}`, async ({ page }) => {
      const response = await page.goto(route.path);
      expect(response?.status()).toBeLessThan(500);
      await expect(page.locator("form[method='post'], form[method='POST']").first()).toBeVisible();
      await expect(page.locator(".form-legend-required, .erp-form").first()).toBeVisible();
    });
  }
});
