import { test, expect } from '@playwright/test'

test.describe('Public pages', () => {
  test('homepage shows public stories or empty state', async ({ page }) => {
    await page.goto('/')

    // Should see either stories or empty state
    const hasStories = await page.locator('.story-card').count()
    const hasEmpty = await page.locator('text=No public stories').count()

    expect(hasStories > 0 || hasEmpty > 0).toBeTruthy()
  })

  test('budget banner visible', async ({ page }) => {
    await page.goto('/')

    // Budget banner should appear (may take a moment to fetch)
    await expect(page.locator('.budget-banner').first()).toBeVisible({ timeout: 5000 })
  })
})
