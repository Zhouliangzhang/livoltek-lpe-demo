import {defineConfig} from '@playwright/test'
export default defineConfig({testDir:'e2e',testMatch:'single-line-data.spec.ts',workers:1,timeout:30000})
