import {test,expect} from '@playwright/test'
test('M1 structure edits preserve ownership and wheel scrolling over topology',async({page})=>{
 await page.goto('/');await page.getByLabel('本次操作人').fill('结构测试工程师');await page.getByRole('button',{name:'确认上下文，进入步骤02'}).click();
 await page.getByRole('button',{name:'03 建立电气结构',exact:true}).click();
 await expect(page.getByRole('heading',{name:'建立电气结构',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'添加电气结构',exact:true}).click();
 await page.getByLabel('结构编号').fill('FEEDER_TEST');await page.getByLabel('结构名称').fill('储能备用馈线');await page.getByLabel('结构类型').selectOption('FEEDER');
 await page.getByLabel('所属结构').selectOption({index:1});await page.getByLabel('回路编号').fill('CKT-TEST');
 await page.getByRole('button',{name:'保存结构并更新拓扑',exact:true}).click();
 await expect(page.getByRole('status').filter({hasText:'结构已保存'})).toBeVisible();
 await expect(page.getByRole('row').filter({hasText:'FEEDER_TEST'})).toContainText('待 EPC 补充');
 const canvas=page.getByTestId('structure-topology').first();await canvas.scrollIntoViewIfNeeded();await canvas.hover();
 await page.mouse.wheel(0,-400);await page.waitForTimeout(250);const before=await page.evaluate(()=>scrollY);await page.mouse.wheel(0,300);await expect.poll(()=>page.evaluate(()=>scrollY)).toBeGreaterThan(before+100);
 const down=await page.evaluate(()=>scrollY);await page.mouse.wheel(0,-300);await expect.poll(()=>page.evaluate(()=>scrollY)).toBeLessThan(down-100);
 await page.reload();await page.getByRole('button',{name:'03 建立电气结构',exact:true}).click();await page.getByLabel('结构清单筛选').selectOption('FEEDER');await expect(page.getByRole('row').filter({hasText:'FEEDER_TEST'})).toContainText('CKT-TEST');
})
