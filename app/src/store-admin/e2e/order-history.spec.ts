import { test, expect } from '@playwright/test'

for (const colorScheme of ['light', 'dark'] as const) {
  test.describe(`${colorScheme} system appearance`, () => {
    test.use({ colorScheme })

    test('keeps the portal light and displays the latest 15 orders', async ({ page }) => {
      const orders = Array.from({ length: 15 }, (_, index) => ({
        orderId: String(index),
        customerId: 'customer',
        status: index === 0 ? 0 : 2,
        updatedAtUnixSeconds: 1793772000 - index,
        items: [{ productId: 1, quantity: 1, price: 10 }],
      }))
      await page.route('**/api/products', route => route.fulfill({ json: [] }))
      await page.route('**/api/makeline/order/recent', route => route.fulfill({ json: orders }))
      await page.goto('/orders?scoutTheme=dark')

      await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
      await expect(page.locator('html')).toHaveCSS('color-scheme', 'light only')
      await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(247, 244, 239)')
      await expect(page.locator('nav')).toHaveCSS('background-color', 'rgb(255, 255, 255)')
      await expect(page.locator('h1')).toHaveCSS('color', 'rgb(36, 36, 36)')
      await expect(page.locator('table')).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)')
      await expect(page.locator('.table-container')).toHaveCSS('background-color', 'rgb(255, 255, 255)')
      await expect(page.getByText('Latest 15 orders', { exact: false })).toBeVisible()
      await expect(page.locator('tbody tr')).toHaveCount(15)
      await expect(page.locator('.pending')).toHaveText('Pending')
      await expect(page.locator('.completed')).toHaveCount(14)

      await page.setViewportSize({ width: 390, height: 844 })
      await page.getByRole('button', { name: 'Toggle navigation' }).click()
      await expect(page.getByRole('link', { name: 'Orders', exact: true })).toBeVisible()
      await expect(page.getByRole('link', { name: 'Products', exact: true })).toBeVisible()
    })
  })
}
