import {test,expect} from '@playwright/test'

test('running demo scrolls both ways over M1 topology and M2 power curve',async({page})=>{
 await page.goto('/')
 await page.getByLabel('选择项目',{exact:true}).selectOption({label:'CI-20 工厂光储 · PV 1.25MW / BESS 2.612MWh'})
 for(const area of ['topology','curve']){
  if(area==='curve')await page.getByRole('button',{name:'M2 调试与 SAT',exact:true}).click()
  const target=area==='topology'?page.getByTestId('topology-canvas').first():page.locator('.dynChart')
  await target.scrollIntoViewIfNeeded();await target.hover()
  const before=await page.evaluate(()=>scrollY)
  await page.mouse.wheel(0,500)
  await expect.poll(()=>page.evaluate(()=>scrollY)).toBeGreaterThan(before+350)
  const down=await page.evaluate(()=>scrollY)
  await page.mouse.wheel(0,-500)
  await expect.poll(()=>page.evaluate(()=>scrollY)).toBeLessThan(down-350)
  console.log(JSON.stringify({area,before,down,up:await page.evaluate(()=>scrollY)}))
 }
})
