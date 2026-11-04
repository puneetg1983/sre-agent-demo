import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const catalog = JSON.parse(readFileSync(fileURLToPath(
  new URL('../../product-service/catalog.json', import.meta.url)), 'utf8'))

test('browses all eight categories and adds an expanded-catalog product to the cart', async ({ page }) => {
  await page.route('**/api/products', route => route.fulfill({ json: catalog }))
  await page.goto('/')
  await expect(page.getByRole('status')).toHaveText('210 products')
  await expect(page.locator('.category-filters button')).toHaveCount(9)
  await expect(page.locator('.product-card')).toHaveCount(24)
  for (const category of [...new Set<string>(catalog.map((p: { category: string }) => p.category))]) {
    const records = catalog.filter((p: { category: string }) => p.category === category)
    await page.getByRole('button', { name: `${category} ${records.length}`, exact: true }).click()
    await expect(page.getByRole('status')).toHaveText(`${records.length} products`)
    await expect(page.locator('.product-card .category')).toHaveText(
      Array(Math.min(records.length, 24)).fill(category))
  }
  await page.getByRole('button', { name: 'Running 21', exact: true }).click()
  await page.locator('.product-card').nth(1).getByRole('button', { name: 'Add to Cart' }).click()
  await page.getByRole('link', { name: 'Cart (1)' }).click()
  await expect(page.locator('.cart-items')).toContainText('Daily Trainer')
})
