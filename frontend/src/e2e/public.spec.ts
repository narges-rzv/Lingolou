import { test, expect } from '@playwright/test'

test.describe('Public pages', () => {
  test('homepage shows public stories or empty state', async ({ page }) => {
    await page.goto('/')

    // Wait for the page to finish loading (budget banner or heading appears)
    await expect(page.locator('h1').first()).toBeVisible({ timeout: 10000 })

    // Should see either a story link or the "No public stories" empty state
    const hasStories = await page.locator('a[href^="/public/stories/"]').count()
    const hasEmpty = await page.getByText('No public stories').count()

    expect(hasStories > 0 || hasEmpty > 0).toBeTruthy()
  })

  test('budget banner visible', async ({ page }) => {
    await page.goto('/')

    // Budget banner should appear (may take a moment to fetch)
    await expect(page.getByText('Community pool')).toBeVisible({ timeout: 10000 })
  })
})
