import { test, expect } from '@playwright/test'

async function registerAndLogin(page) {
  const ts = Date.now()
  await page.goto('/login')
  await page.click('button:has-text("Register")')
  await page.fill('#reg-email', `story-${ts}@example.com`)
  await page.fill('#reg-user', `storyuser-${ts}`)
  await page.fill('#reg-pass', 'testpass123')
  await page.click('button[type="submit"]:has-text("Create account")')
  await expect(page).toHaveURL(/dashboard/, { timeout: 10000 })
}

test.describe('Stories', () => {
  test('create story and see it on dashboard', async ({ page }) => {
    await registerAndLogin(page)

    // Navigate to new story
    await page.click('a:has-text("New Story")')
    await expect(page).toHaveURL(/new/, { timeout: 5000 })

    // Fill form
    await page.fill('#title', 'My Test Story')
    await page.fill('#plot', 'A fun adventure in the park')

    // Submit
    await page.click('button[type="submit"]:has-text("Create Story")')

    // Should navigate to story detail
    await expect(page).toHaveURL(/stories\/\d+/, { timeout: 10000 })

    // Go back to dashboard
    await page.click('a:has-text("My Stories")')
    await expect(page.locator('text=My Test Story')).toBeVisible()
  })

  test('delete story', async ({ page }) => {
    await registerAndLogin(page)

    // Create a story first
    await page.click('a:has-text("New Story")')
    await page.fill('#title', 'Story to Delete')
    await page.fill('#plot', 'Will be deleted')
    await page.click('button[type="submit"]:has-text("Create Story")')
    await expect(page).toHaveURL(/stories\/\d+/, { timeout: 10000 })

    // Delete it
    await page.click('button:has-text("Delete")')

    // Confirm if there's a confirmation dialog
    page.on('dialog', (dialog) => dialog.accept())
    await page.click('button:has-text("Delete")')

    // Should be back at dashboard
    await expect(page).toHaveURL(/dashboard/, { timeout: 10000 })
  })
})
