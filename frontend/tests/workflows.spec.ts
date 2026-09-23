import { test, expect, type Page } from '@playwright/test';
import path from 'node:path';

async function login(page: Page, role: 'employee' | 'hr') {
  await page.goto('/login');
  await page.getByLabel('Логин', { exact: true }).fill(role);
  await page.getByLabel('Пароль', { exact: true }).fill(`${role}-demo-2026`);
  await page.getByRole('button', { name: 'Войти в пространство' }).click();
  await expect(page).toHaveURL(role === 'hr' ? /\/hr$/ : /\/me$/);
}

test('employee: recommendation, factual evidence, completion and reload', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await login(page, 'employee');
  await expect(page.getByText('Backend Engineer · Middle', { exact: false }).first()).toBeVisible();
  await page.screenshot({ path: '../artifacts/employee-before.png', fullPage: true });
  await page.getByRole('button', { name: /Подобрать с AI|Обновить подбор/ }).click();
  await expect(page.getByText('Почему этот шаг', { exact: false }).first()).toBeVisible({ timeout: 15000 });
  await page.getByText('Почему этот шаг', { exact: false }).first().click();
  await expect(page.getByText('История участия', { exact: true }).first()).toBeVisible();
  await page.screenshot({ path: '../artifacts/employee-recommendations.png', fullPage: true });
  await page.getByRole('button', { name: 'Доступные активности' }).click();
  const complete = page.getByRole('button', { name: 'Завершить', exact: true }).first();
  await expect(complete).toBeVisible();
  {
    const responsePromise = page.waitForResponse(r => r.url().endsWith('/complete') && r.request().method() === 'POST');
    await complete.click();
    const response = await responsePromise;
    expect(response.status()).toBe(200);
    const changed = await response.json();
    expect(changed.development.progress).toBeGreaterThan(changed.before_progress);
    await expect(page.getByText('Готово!', { exact: false })).toBeVisible();
    await page.reload();
    await expect(page.getByRole('progressbar', { name: 'Соответствие карьерной цели' })).toHaveAttribute('aria-valuenow', String(changed.development.progress));
  }
  await page.getByRole('button', { name: /История участия/ }).click();
  await expect(page.getByRole('table')).toBeVisible();
  expect(errors).toEqual([]);
});

test('HR: aggregates, employee lookup, import and new profile', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await login(page, 'hr');
  await expect(page.getByRole('heading', { name: 'Развитие команды' })).toBeVisible();
  await page.screenshot({ path: '../artifacts/hr-overview.png', fullPage: true });
  await page.getByLabel('Поиск сотрудников').fill('E0028');
  await page.getByRole('link', { name: 'Профиль ↗' }).click();
  await expect(page.getByText('ПРОФИЛЬ СОТРУДНИКА', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: /Отметить выполненным/ })).toHaveCount(0);
  await page.getByRole('link', { name: 'Импорт данных' }).click();
  await page.getByLabel('JSON профилей сотрудников').setInputFiles(path.resolve('../docs/fixtures/employees.json'));
  await page.getByLabel('CSV истории участия').setInputFiles(path.resolve('../docs/fixtures/activity_history.csv'));
  await page.getByRole('button', { name: 'Проверить и импортировать' }).click();
  await expect(page.getByRole('heading', { name: 'Результат импорта' })).toBeVisible();
  await page.screenshot({ path: '../artifacts/import-result.png', fullPage: true });
  await page.getByRole('link', { name: /Открыть профиль CQ_CASE_01/ }).click();
  await expect(page.getByRole('heading', { name: 'Synthetic Critical Gap' })).toBeVisible();
  await page.getByRole('button', { name: /Подобрать с AI|Обновить подбор/ }).click();
  await expect(page.getByText('Почему этот шаг', { exact: false }).first()).toBeVisible({ timeout: 15000 });
  expect(errors).toEqual([]);
});
