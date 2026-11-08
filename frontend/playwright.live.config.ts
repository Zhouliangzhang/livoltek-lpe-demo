import {defineConfig} from '@playwright/test'
// Read-only smoke check against the already running local demo.
export default defineConfig({testDir:'e2e',testMatch:'live-scroll.spec.ts',workers:1,timeout:60000,use:{baseURL:'http://127.0.0.1:8000',channel:'msedge',headless:true,viewport:{width:1495,height:790}}})
