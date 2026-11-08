import {test,expect} from '@playwright/test'
test('M1 start separates offline, simulation and real, and persists boundary',async({page})=>{
 await page.goto('/');
 await expect(page.getByRole('heading',{name:'确认项目与 iEMS',exact:true})).toBeVisible();
 await page.getByLabel('选择 iEMS 环境').selectOption('OFFLINE');
 await expect(page.getByText('未连接控制器 · 仅编制草案',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'确认上下文，进入步骤02'}).click();
 await expect(page.getByRole('alert')).toContainText('操作人');
 await page.getByLabel('本次操作人').fill('EPC 测试工程师');
 await page.getByRole('button',{name:'确认上下文，进入步骤02'}).click();
 await expect(page.getByRole('heading',{name:'定义系统边界',exact:true})).toBeVisible();
 await page.getByLabel('项目时区').selectOption('Africa/Johannesburg');
 await page.getByLabel('本次系统范围').fill('PCC 内光伏、储能与工厂负载');
 await page.getByLabel('项目依据引用').fill('EPC-SLD-TEST Rev A（测试草稿）');
 await page.getByRole('button',{name:'保存系统边界草案',exact:true}).click();
 await expect(page.getByRole('status').filter({hasText:'系统边界已保存'})).toBeVisible();
 await page.reload();
 await page.getByRole('button',{name:'02 定义系统边界',exact:true}).click();
 await expect(page.getByLabel('本次系统范围')).toHaveValue('PCC 内光伏、储能与工厂负载');
 await page.getByLabel('选择 iEMS 环境').selectOption('REAL');
 await expect(page.getByText('现场 iEMS 未连接 · 身份未核验',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'M2 调试与 SAT',exact:true}).click();
 await expect(page.getByRole('heading',{name:'确认项目与 iEMS',exact:true})).toBeVisible();
})
