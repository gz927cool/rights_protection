import { test, expect } from '@playwright/test';

test.describe('劳动争议咨询流程', () => {
  test.beforeEach(async ({ page }) => {
    // 等待后端 API 准备就绪
    await page.goto('/');
    // 等待页面加载
    await page.waitForLoadState('networkidle');
  });

  test('完整咨询流程：开始咨询 -> 选择案由 -> 选择处理方式 -> 显示问题', async ({ page }) => {
    // 1. 点击"开始咨询"按钮
    const startButton = page.getByRole('button', { name: /开始咨询/i });
    await startButton.waitFor({ state: 'visible', timeout: 30000 });
    await startButton.click();

    // 2. 选择案由类型（如"欠薪/克扣工资"）
    const caseTypeButton = page.getByText(/欠薪|克扣工资/i);
    await caseTypeButton.waitFor({ state: 'visible', timeout: 30000 });
    await caseTypeButton.click();

    // 3. 选择处理方式（如"我来说"）
    const handlingButton = page.getByText(/我来说/i);
    await handlingButton.waitFor({ state: 'visible', timeout: 30000 });
    await handlingButton.click();

    // 4. 验证页面显示第一个问题
    // 等待问题加载（后端可能需要时间生成）
    const questionElement = page.locator('text=/问题|请描述|您的经历/i').first();
    await expect(questionElement).toBeVisible({ timeout: 60000 });
  });

  test('页面加载和基础元素验证', async ({ page }) => {
    // 验证页面标题或主要元素存在
    await expect(page).toHaveTitle(/劳动争议|咨询|维权/i);
  });
});
