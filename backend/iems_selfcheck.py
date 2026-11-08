"""Step02 synthetic observations only. No hardware probing, configuration writes or control lease."""
SCENARIOS=['normal','controller_mismatch','configuration_mismatch','driver_mismatch','engine_restart','clock_unsynced','log_unwritable','storage_fault','interface_conflict','owner_lost','strategy_conflict','readonly_only','unknown_device']


def selfcheck(session, scenario):
    route=session['route']; checks=[]
    def add(key,label,actual,expected,fault,reason,action,owner='iEMS 厂家',layer=None):
        failed=scenario==fault
        checks.append(dict(key=key,label=label,actual=reason if failed else actual,expected=expected,passed=not failed,severity='BLOCK' if failed else 'PASS',reason=reason if failed else '',action=action,owner=owner,layer=layer))
    add('identity','控制器身份与站点绑定','SIM-IEMS-001 · 模拟站点绑定一致','匹配本次会话的模拟身份','controller_mismatch','读回 SIM-IEMS-OTHER，与冻结身份不符；不能视作换机自动接纳','回 M1 核对控制器 SN、站点和换机记录，重新建立会话','EPC 现场工程师','L3')
    add('configuration','冻结配置与生效读回','模拟配置哈希与会话一致','读回哈希与冻结模型一致','configuration_mismatch','模拟生效配置与冻结版本不一致','回 M1 核对下发与读回，保存新基线并重新建立会话','EPC 现场工程师','L5')
    add('engine','测试引擎与启动代次','SIM-ENGINE-1 · boot-001','本轮启动代次不变','engine_restart','引擎启动代次从 boot-001 变为 boot-002，本轮执行上下文失效','停止新测试动作；核对重启原因及批准退出程序后新建一轮自检')
    add('driver','驱动与测试包适配','SIM-METER-DRIVER/1 · SIM-METER-SEQ-1','仅匹配演练驱动及夹具版本','driver_mismatch','模拟驱动版本与测试包适配清单不匹配','请厂家确认型号、固件、驱动与测试包版本适配表')
    add('storage','存储与本地状态','模拟可写 · 状态快照读回一致','状态可以写入并读回','storage_fault','模拟状态存储写入失败，不能恢复运行上下文','停止新测试动作；由厂家核查存储空间、介质和读写权限')
    add('clock','时间同步与质量','SIM-CLOCK · 偏差 +12 ms · GOOD','演练偏差绝对值 ≤100 ms；非厂家判据','clock_unsynced','模拟偏差 +2500 ms · UNSYNC，超出演练时间质量要求','核对时钟源、同步状态和偏差；现场允许误差须由厂家按测试包确认')
    add('logs','日志与证据持久化','模拟日志写入/读回成功','证据可持久化并关联运行 ID','log_unwritable','模拟控制器日志无法持久化；本网页记录不代表控制器日志正常','停止新测试动作；核查日志路径、存储和权限，恢复后重新自检')
    add('interfaces','通信接口与地址','%s ↔ %s · %s · 演练地址1，无冲突'%(route['ems']['port_id'],route['meter']['port_id'],route['domain']),'仅扫描冻结范围；不修改网络、总线或地址','interface_conflict','模拟发现同一总线地址冲突，不能确定唯一目标','回 M1 核对接口和地址；只能依据批准设置实施通信引导配置','EPC / iEMS 厂家','L4')
    add('owner','控制模式与指令所有者','诊断模式 · SIM-TEST-ENGINE · 单一所有者','本轮范围内唯一执行所有者','owner_lost','模拟所有者变更为上层 EMS，本轮所有权丢失','停止新测试动作；协调上层 EMS，按批准程序重新确认控制权')
    add('strategies','上层 EMS、本地策略与定时任务','模拟扫描：无冲突任务；未停用任何策略','不得自动抢占或关闭既有策略','strategy_conflict','模拟定时任务与本轮范围冲突，尚未协调','由 EPC 与厂家按批准程序协调；确认后重新自检，不自动停用策略','EPC / iEMS 厂家')
    add('permission','远程权限与测试边界','只读权限；禁止功率影响动作' if scenario=='readonly_only' else '演练诊断权限；本次范围不包含功率控制','只读诊断不依赖远程写权限',None,'','控制试验需另行批准测试范围、权限和退出策略')
    if scenario=='readonly_only':checks[-1].update(severity='NOTICE',reason='模拟没有远程写权限；只读诊断可继续，功率影响动作锁定')
    first_failure=next((i for i,c in enumerate(checks) if not c['passed']),None)
    if first_failure is not None:
        for c in checks[first_failure+1:]:
            c.update(actual='前置异常，本项未执行',passed=False,severity='SKIPPED',reason='前置自检未满足，本项没有形成观测结论',action='先处理前置异常，再重新执行本轮自检')
    passed=all(c['passed'] for c in checks)
    checks.append(dict(key='lease',label='测试范围与执行约束',actual='本轮模拟只读范围已绑定；不授予现场控制权' if passed else '本轮范围不放行，停止新测试动作',expected='仅限会话内零馈表与 iEMS；不得扩展设备或动作',passed=passed,severity='PASS' if passed else 'BLOCK',reason='' if passed else '前置自检异常，不能建立有效执行范围',action='先处理上方异常，再重新自检',owner='iEMS 厂家',layer=None))
    failed=next((c for c in checks if not c['passed']),None)
    return dict(status='PASS' if passed else 'FAIL',checks=checks,samples=[],code='SIM_SELF_CHECK_READY' if passed else 'SIM_'+scenario.upper(),source='SIMULATOR',field_result=None,manufacturer_basis='PENDING',criteria_version='SIM-SELF-CHECK-2',exit_state='NO_PHYSICAL_ACTION',
        capabilities=dict(read_only=passed,power_control=False,reason='本次仅为诊断和计量范围；现场控制许可、租约和退出策略均未批准'),
        lease=dict(status='SIMULATED_READ_SCOPE' if passed else 'NOT_GRANTED',owner='SIM-TEST-ENGINE' if passed else None,control_domain=route['ems']['node_id'],scope=session.get('scope','METER_VALIDATION'),devices=[route['ems']['node_id'],route['meter']['node_id']],allowed_actions=['READ_DIAGNOSTICS'] if passed else [],physical_lease=False),
        initial_snapshot=dict(controller_sn='SIM-IEMS-OTHER' if scenario=='controller_mismatch' else 'SIM-IEMS-001',site_id=session.get('snapshot',{}).get('project_id'),expected_hash=session['model_hash'],readback_hash='SIM-DIFFERENT-HASH' if scenario=='configuration_mismatch' else session['model_hash'],engine_boot='boot-002' if scenario=='engine_restart' else 'boot-001',clock_offset_ms=2500 if scenario=='clock_unsynced' else 12,clock_quality='UNSYNC' if scenario=='clock_unsynced' else 'GOOD',mode='DIAGNOSTIC',source='SYNTHETIC'),
        interfaces=[dict(port=route['ems']['port_id'],peer=route['meter']['port_id'],domain=route['domain'],address='1（演练专用，不覆盖 M1）',configuration_changed=False,before=None,readback=None)],
        candidates=[dict(identity='SIM-UNKNOWN-001',admitted=False,action='候选设备，须回 M1 确认；未加入控制组')] if scenario=='unknown_device' else [],
        stop=dict(new_actions_blocked=not passed,trigger=failed['label'] if failed else None,exit_policy='未执行现场退出动作；批准退出策略待厂家提供',recovery='按原运行 ID 查询已保存结果；复测必须明确建立新运行'),
        basis_pending=[dict(title=t,missing=v,owner=o) for t,v,o in [
            ('身份与适配','控制器 SN/站点绑定接口、型号/固件/驱动和测试包适配表','iEMS 厂家'),
            ('时间与持久化','各测试的时钟质量阈值、日志持久化及重启恢复接口','iEMS 厂家'),
            ('控制权与退出','单一所有者仲裁、控制租约范围/有效期/撤销、冲突协调及安全退出规程','iEMS 厂家 / 项目授权方'),
            ('通信引导配置','可修改的端口/总线/网络白名单、修改前值与生效读回接口','iEMS 厂家 / EPC')]])
