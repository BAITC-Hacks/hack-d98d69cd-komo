import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve('..');
const out = path.join(root, process.env.TEST_ARTIFACT_DIR || 'artifacts/import-formats');
fs.mkdirSync(out, { recursive: true });

test('download Excel and JSON templates, upload, repeat and show errors', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto('/login');
  await page.getByLabel('Логин', { exact: true }).fill('hr');
  await page.getByLabel('Пароль', { exact: true }).fill(process.env.HR_PASSWORD || 'hr-demo-2026');
  await page.getByRole('button', { name: 'Войти в пространство' }).click();
  await expect(page).toHaveURL(/\/hr$/);
  await page.getByRole('link', { name: 'Импорт данных' }).click();
  await page.screenshot({ path: path.join(out, '01-template.png'), fullPage: true });
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Скачать шаблон', exact: true }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('career-quest-template.xlsx');
  const excelPath = path.join(out, download.suggestedFilename());
  await download.saveAs(excelPath);
  // Only synthetic QA IDs are added to the shared demo database.
  const excel = execFileSync('docker', ['compose', 'exec', '-T', 'api', 'python', '-c', `
import io,sys
from uuid import uuid4
from openpyxl import load_workbook
w=load_workbook(io.BytesIO(sys.stdin.buffer.read()))
eid='QA_R2_EXCEL_UI_'+uuid4().hex[:8]
for sheet in [w['employees'],w['employee_skills'],w['history']]:
 for row in sheet.iter_rows():
  for c in row:
   if c.value=='TEMPLATE_EMP_001': c.value=eid
   if c.value=='TEMPLATE_REC_001': c.value=eid+'_REC'
b=io.BytesIO();w.save(b);sys.stdout.buffer.write(b.getvalue())
`], { cwd: root, input: fs.readFileSync(excelPath) });
  await page.getByLabel('Профили сотрудников: Excel или JSON').setInputFiles({ name: 'filled.xlsx', mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer: excel });
  const responsePromise = page.waitForResponse(r => r.url().endsWith('/hr/import') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Проверить и импортировать', exact: false }).click();
  const response = await responsePromise; expect(response.status()).toBe(200);
  const imported = await response.json(); expect(imported.employees_created).toBe(1); expect(imported.history_created).toBe(1);
  await expect(page.getByRole('heading', { name: 'Результат импорта' })).toBeVisible();
  await page.screenshot({ path: path.join(out, '02-excel-imported.png'), fullPage: true });
  await page.getByRole('button', { name: 'Проверить и импортировать', exact: false }).click();
  await expect(page.getByText('Изменений нет: эти данные уже загружены')).toBeVisible();
  await page.getByLabel('Формат шаблона').selectOption('json');
  const jsonPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Скачать шаблон', exact: true }).click();
  const jsonDownload = await jsonPromise;
  const jsonPath = path.join(out, jsonDownload.suggestedFilename()); await jsonDownload.saveAs(jsonPath);
  const data = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
  const id = 'QA_R2_JSON_UI_' + Date.now();
  data.employees[0].employee_id = id; data.history[0].employee_id = id; data.history[0].record_id = id + '_REC';
  await page.getByLabel('Профили сотрудников: Excel или JSON').setInputFiles({ name: 'filled.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(data)) });
  const jsonResponse = page.waitForResponse(r => r.url().endsWith('/hr/import') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Проверить и импортировать', exact: false }).click();
  expect((await jsonResponse).status()).toBe(200);
  await expect(page.getByRole('link', { name: `Открыть профиль ${id} и подобрать шаги ↗` })).toBeVisible();
  await page.getByLabel('Профили сотрудников: Excel или JSON').setInputFiles({ name: 'broken.xlsx', mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer: Buffer.from('broken') });
  await page.getByRole('button', { name: 'Проверить и импортировать', exact: false }).click();
  await expect(page.getByRole('alert').filter({ hasText: 'Не удалось прочитать Excel' })).toContainText('Не удалось прочитать Excel');
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
  await page.screenshot({ path: path.join(out, '03-mobile-error.png'), fullPage: true });
  expect(errors).toEqual([]);
});
