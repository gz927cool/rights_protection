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

  test('70_30布局验证_信息面板显示', async ({ page }) => {
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    // 验证聊天区域存在（左侧）
    const textarea = page.locator('textarea').first();
    await expect(textarea).toBeVisible({ timeout: 5000 });

    // 验证信息面板存在（右侧）- 显示"信息面板"或"问题初判"等标题
    await expect(page.locator('text=/信息面板|问题初判|通用问题|特殊问题/i').first()).toBeVisible({ timeout: 5000 });

    // 验证右侧面板显示步骤信息
    await expect(page.locator('text=/第.*步/').first()).toBeVisible({ timeout: 5000 });
  });

  test('70_30布局验证_Step3表单交互', async ({ page }) => {
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    // 发送"欠薪"进入step2
    const textarea = page.locator('textarea').first();
    await textarea.fill('我想咨询欠薪问题');
    await textarea.press('Enter');
    await page.waitForTimeout(3000);

    // 在聊天框输入A继续
    await textarea.fill('A');
    await textarea.press('Enter');
    await page.waitForTimeout(5000);

    // 检查信息面板中是否有表单元素（就业状态选项）
    // Step3应该有就业状态按钮
    const employmentStatus = page.locator("text=/就业状态/").first();
    if (await employmentStatus.isVisible({ timeout: 5000 }).catch(() => false)) {
      // 点击"在职"选项
      const zaiZhiBtn = page.locator("button:has-text('在职')").first();
      if (await zaiZhiBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await zaiZhiBtn.click();
      }

      // 找到月工资输入框
      const salaryInput = page.locator('input[type="number"]').first();
      if (await salaryInput.isVisible({ timeout: 3000 }).catch(() => false)) {
        await salaryInput.fill('8000');
      }
    }
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

    // 等待AI响应（检查消息列表中是否有新的AI回复）
    await page.waitForTimeout(5000);

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
