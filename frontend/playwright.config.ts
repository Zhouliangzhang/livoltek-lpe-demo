import {defineConfig} from '@playwright/test'
export default defineConfig({testDir:'e2e',workers:1,timeout:60000,use:{baseURL:'http://127.0.0.1:8001',channel:'msedge',headless:true,viewport:{width:1600,height:1000},screenshot:'only-on-failure'},webServer:{command:'..\\.venv\\Scripts\\python.exe -m uvicorn backend.main:app --app-dir .. --host 127.0.0.1 --port 8001',url:'http://127.0.0.1:8001/api/health',reuseExistingServer:false,env:{LPE_DB:'../.e2e-'+Date.now()+'.db'}}})


