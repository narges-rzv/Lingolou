import { test, expect } from '@playwright/test'

async function registerAndLogin(page) {
  const ts = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  await page.goto('/login')
  await page.click('button:has-text("Register")')
  await page.fill('#reg-email', `settings-${ts}@example.com`)
  await page.fill('#reg-user', `setuser-${ts}`)
  await page.fill('#reg-pass', 'testpass123')
  await page.click('button[type="submit"]:has-text("Create account")')
  await expect(page).toHaveURL(/dashboard/, { timeout: 15000 })
}

test.describe('Settings', () => {
  test('navigate to settings and see key status', async ({ page }) => {
    await registerAndLogin(page)

    await page.click('a:has-text("Settings")')
    await expect(page).toHaveURL(/settings/, { timeout: 5000 })

    // Should show "Not set" for both keys
    await expect(page.locator('text=Not set').first()).toBeVisible()
  })

  test('save and remove API key', async ({ page }) => {
    await registerAndLogin(page)
    await page.click('a:has-text("Settings")')
    await expect(page).toHaveURL(/settings/, { timeout: 5000 })

    // Type an API key
    await page.fill('input[placeholder="sk-..."]', 'sk-test123456')
    await page.click('button:has-text("Save Keys")')

    // Should show success
    await expect(page.locator('text=Keys saved successfully.')).toBeVisible({ timeout: 5000 })

    // Should now show "Configured"
    await expect(page.locator('text=Configured').first()).toBeVisible()

    // Remove the key
    await page.click('button:has-text("Remove")')
    await expect(page.locator('text=Key removed.')).toBeVisible({ timeout: 5000 })
  })
})
