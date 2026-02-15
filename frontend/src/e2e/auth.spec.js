import { test, expect } from '@playwright/test'

function uniqueId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

test.describe('Authentication', () => {
  test('register new user', async ({ page }) => {
    const id = uniqueId()
    await page.goto('/login')

    // Switch to register tab
    await page.click('button:has-text("Register")')

    // Fill registration form
    await page.fill('#reg-email', `test-${id}@example.com`)
    await page.fill('#reg-user', `testuser-${id}`)
    await page.fill('#reg-pass', 'testpass123')

    // Submit
    await page.click('button[type="submit"]:has-text("Create account")')

    // Should redirect to dashboard
    await expect(page).toHaveURL(/dashboard/, { timeout: 15000 })
  })

  test('login with credentials', async ({ page }) => {
    const id = uniqueId()
    const email = `login-${id}@example.com`
    const username = `loginuser-${id}`

    // First register
    await page.goto('/login')
    await page.click('button:has-text("Register")')
    await page.fill('#reg-email', email)
    await page.fill('#reg-user', username)
    await page.fill('#reg-pass', 'testpass123')
    await page.click('button[type="submit"]:has-text("Create account")')
    await expect(page).toHaveURL(/dashboard/, { timeout: 15000 })

    // Logout
    await page.click('button:has-text("Log out")')

    // Login
    await page.goto('/login')
    await page.fill('#login-user', username)
    await page.fill('#login-pass', 'testpass123')
    await page.click('button[type="submit"]:has-text("Log in")')

    await expect(page).toHaveURL(/dashboard/, { timeout: 15000 })
  })

  test('access private route when logged out redirects to login', async ({ page }) => {
    // Clear any stored tokens
    await page.goto('/login')
    await page.evaluate(() => localStorage.clear())

    await page.goto('/dashboard')
    // Should be redirected to login or show login page
    await expect(page.locator('text=Log in').first()).toBeVisible({ timeout: 5000 })
  })
})
