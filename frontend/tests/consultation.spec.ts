import { test, expect } from '@playwright/test';

test.describe('劳动争议咨询流程', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('首页加载和AI咨询入口验证', async ({ page }) => {
    await expect(page.locator('text=劳动争议')).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=AI智能问答')).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=九步引导').first()).toBeVisible({ timeout: 15000 });
    const aiLink = page.locator('a[href="/chat"]');
    await expect(aiLink).toBeVisible({ timeout: 15000 });
  });

  test('聊天页面加载和快捷案由按钮验证', async ({ page }) => {
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('text=/欢迎|请问|劳动争议/i').first()).toBeVisible({ timeout: 30000 });
    await expect(page.locator('text=欠薪').first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=开除').first()).toBeVisible({ timeout: 15000 });
  });

  test('AI咨询完整流程验证', async ({ page }) => {
    // 进入聊天页面
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    // 等待欢迎消息
    await expect(page.locator('text=/欢迎|请问|劳动争议/i').first()).toBeVisible({ timeout: 30000 });

    // 选择欠薪案由 - 点击按钮会自动填入输入框
    const qianxinBtn = page.locator('button:has-text("欠薪")').first();
    await expect(qianxinBtn).toBeVisible({ timeout: 15000 });
    await qianxinBtn.click();

    // 按Enter发送消息
    const inputArea = page.locator('textarea').first();
    await expect(inputArea).toBeVisible({ timeout: 5000 });
    await inputArea.press('Enter');

    // 等待AI响应选择方式
    await page.waitForTimeout(3000);
    const optionText = page.locator('text=/A.*转律师|B.*自由描述|C.*交互/').first();
    await expect(optionText).toBeVisible({ timeout: 20000 });

    // 选择B-自由描述案情（输入B后按Enter发送）
    const inputB = page.locator('textarea').first();
    await inputB.fill('B');
    await inputB.press('Enter');

    // 等待进入通用问题环节
    await expect(page.locator('text=/通用问题|在职|劳动合同|工资/i').first()).toBeVisible({ timeout: 20000 });

    // 输入"在职"作为就业状态
    const inputArea2 = page.locator('textarea').first();
    await inputArea2.fill('在职');
    await inputArea2.press('Enter');

    // 等待AI响应
    await page.waitForTimeout(2000);
  });
});
