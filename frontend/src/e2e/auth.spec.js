import { test, expect } from '@playwright/test'

const TEST_USER = {
  email: `test-${Date.now()}@example.com`,
  username: `testuser-${Date.now()}`,
  password: 'testpass123',
}

test.describe('Authentication', () => {
  test('register new user', async ({ page }) => {
    await page.goto('/login')

    // Switch to register tab
    await page.click('button:has-text("Register")')

    // Fill registration form
    await page.fill('#reg-email', TEST_USER.email)
    await page.fill('#reg-user', TEST_USER.username)
    await page.fill('#reg-pass', TEST_USER.password)

    // Submit
    await page.click('button[type="submit"]:has-text("Create account")')

    // Should redirect to dashboard
    await expect(page).toHaveURL(/dashboard/, { timeout: 10000 })
  })

  test('login with credentials', async ({ page }) => {
    // First register
    await page.goto('/login')
    await page.click('button:has-text("Register")')
    const email = `login-${Date.now()}@example.com`
    const username = `loginuser-${Date.now()}`
    await page.fill('#reg-email', email)
    await page.fill('#reg-user', username)
    await page.fill('#reg-pass', 'testpass123')
    await page.click('button[type="submit"]:has-text("Create account")')
    await expect(page).toHaveURL(/dashboard/, { timeout: 10000 })

    // Logout
    await page.click('button:has-text("Log out")')

    // Login
    await page.goto('/login')
    await page.fill('#login-user', username)
    await page.fill('#login-pass', 'testpass123')
    await page.click('button[type="submit"]:has-text("Log in")')

    await expect(page).toHaveURL(/dashboard/, { timeout: 10000 })
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
