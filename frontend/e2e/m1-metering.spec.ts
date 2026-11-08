import {test,expect} from '@playwright/test'
import {meterConversion,meterIssues,type MeterPlan} from '../src/meteringModel'
const plan=()=>({ct_mode:'EXTERNAL',ct_primary:'4000',ct_secondary:'5',pt_mode:'DIRECT',pt_primary:'',pt_secondary:'',meter_ct_ratio:'800',meter_pt_ratio:'1',read_side:'PRIMARY',input_unit:'W',driver_scale:'1',raw_sign:'IMPORT_POSITIVE'} as MeterPlan)
test('primary power is not multiplied by CT again; secondary and sign conversion are explicit',()=>{
 const c=plan();expect(meterConversion(c)).toBe('P_pcc (kW) = 原始读数 × 0.001');c.read_side='SECONDARY';expect(meterConversion(c)).toBe('P_pcc (kW) = 原始读数 × 0.8');c.raw_sign='EXPORT_POSITIVE';expect(meterConversion(c)).toBe('P_pcc (kW) = 原始读数 × -0.8');c.input_unit='';expect(meterConversion(c)).toContain('待确认');
})
test('mismatch, denominator zero and missing evidence remain distinct',()=>{
 const c=plan();expect(meterIssues(c).some(i=>i.field==='manufacturer_ref'&&!i.conflict)).toBeTruthy();c.meter_ct_ratio='400';expect(meterIssues(c).some(i=>i.field==='meter_ct_ratio'&&i.conflict)).toBeTruthy();c.ct_secondary='0';expect(meterIssues(c).some(i=>i.field==='ct_secondary'&&i.conflict)).toBeTruthy();
})
