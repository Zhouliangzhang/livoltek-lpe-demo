# LIVOLTEK Project Engineer
## M2 引导式安装（Guided Installation）详细设计说明书 V1.1

## 修订总原则：完整相关系统建模与合同责任分离

**产品定位（修订后的权威定义）：** LIVOLTEK Project Engineer 是主设备厂家提供给EPC工程师的系统感知型安装调试辅助、现场故障排查及远程技术支持协同工具。它不取代EPC专业电气设计、施工管理、法定检验或合同验收工具。

**系统建模覆盖范围：** 凡是会实质影响LIVOLTEK设备的安装、控制、保护、并离网协同、自测、系统功能或故障定位的设备和接口，均须纳入相关系统模型；无论其品牌、供货商或是否由LIVOLTEK生产。包括第三方PV逆变器、柴油机、ATS/STS、变压器、电表、保护开关、充电桩及相关负载/电网边界。无需复制整座工厂或EPC的全部工程设计。

**模型深度独立于品牌：** L1为具备完整参数/遥测/控制资料的设备级模型；L2为支持关键指令、反馈、通信映射及接口验证的集成设备模型；L3为仅建模边界、额定参数、运行状态和关键测量的简化外部系统。第三方设备可以达到L1，LIVOLTEK设备也可因资料不全暂处待核验状态。

**权限与责任分离：** `manufacturer`描述设备品牌；`responsibility_owner`描述工程/合同责任；`control_capabilities`描述技术可用性；`authorization`单独约束谁在何种条件下有权读写、控制和执行测试。**可建模≠可远程控制≠厂家承担质保。**

**数据与安全：** 第三方设备接入须有协议/寄存器来源和兼容性验证；无有效数据不得模拟真实故障结论或显示实时能量流动；无授权不得写第三方参数、触发保护或远程启动设备。未知字段和未批准SOP允许形成待评审草案，不得自动发布生产作业。


## V1.1新增：基于完整相关系统的厂家辅助式安装

### M2.1 功能定位重述

本模块是LIVOLTEK为EPC提供的**厂家指导式安装辅助工具**，不是承包商施工组织管理或第三方设备内部安装手册生成器。它须读取M1的L1/L2/L3混合设备模型，为LIVOLTEK主设备及其与第三方设备的必要接口生成受控安装检查任务。项目施工及安全作业的法定和合同责任仍由EPC承担。

### M2.2 SOP来源分层

| 来源类型 | 允许生成的内容 | 必须阻止的内容 |
| --- | --- | --- |
| LIVOLTEK厂家批准的设备SOP | LIVOLTEK设备安装环境、接线检查、端口配置、安装前验证 | 无依据的参数和自主上电序列 |
| 经过审核的接口SOP | 与第三方设备通信线、信号表、测点映射、反馈和联调前检查 | 第三方设备内部拆机、参数写入、继保整定 |
| EPC提供的批准工程资料 | 依据设计图纸做现场一致性核对及必要证据记录 | 取代EPC施工方案及正式验收 |
| 未核验第三方资料 | 生成“待提供资料/待人工检查”草案项 | 正式执行或自动标记通过 |

### M2.3 生成条件与操作逻辑

输入：`system_context_baseline` + `modeling_level` + `interface_contract` + 经过审批的LIVOLTEK/接口SOP + 现场工程条件。规则引擎按“设备型号 → 接口依赖 → 工程功能”生成任务；没有完整单线图可先生成设备级草案，但正式接线与通电任务必须满足设计文件、安全许可及专业审核门禁。

任务结果包含`task_owner`（EPC或厂家指导）、`scope_type`（LIVOLTEK_DEVICE / THIRD_PARTY_INTERFACE / EPC_DOCUMENT_CHECK）、`source_document_ref`、`execution_authority`、`missing_inputs`、`review_status`。工程师可在App逐条评论、提出修改，但不能直接把草案设为正式批准SOP。

### M2.4 M3与M5衔接

M2记录第三方接口连接、线缆/信号核验、真实设备端口映射和安装观察结果，传给M3作为接口级/系统级自测输入，传给M5作为故障检查基线。第三方内部施工工艺不作为本系统必须完成的里程碑。

### V1.1新增验收用例

- UAT-19：L2第三方PV接入后自动生成接口通信检查，不生成未经批准的光伏逆变器内部安装SOP。
- UAT-20：柴油机控制接口资料缺失时显示BLOCKED及待补字段。
- UAT-21：L3外部负载可触发边界测量/检查任务，不要求设备扫码。
- UAT-22：修改第三方通信协议后，受影响步骤重新评审，原完成记录不覆盖。
- UAT-23：EPC确认作业结果与厂家批准技术操作权限分别审计。


---

## 既有详细设计（未冲突条款继续适用）

**文件状态：** 研发与EPC联合评审稿  
**上游基线：** 《LIVOLTEK Project Engineer 工商业工程师App PRD V2.0》及《M1 项目建立与配置详细设计 V1.1》  
**产品范围：** 工商业储能、光储、光储柴、储充、光储充及微电网项目的EPC现场安装作业  
**交付边界：** M2负责安装SOP生成与执行、现场证据、安全门禁和受控上电前置检查；M3负责正式设备调试、自测及SAT；M4负责交接报告和业主签署。

## 1. 模块目标、边界与设计原则

### 1.1 业务目标

将M1已经审核发布的工程数字基线转化为EPC可执行的现场工作包（Work Package）、步骤（Step）、验收判据和证据要求。使安装过程标准化、可追踪、可复查，并为M3提供可信的安装完成与安全准入记录。

### 1.2 关键设计原则

1. **拓扑驱动而非固定流程：** 以Project ID、Topology Version、Device Asset、Parameter Set、国家规范包、厂家正式SOP及现场条件共同决定任务。
2. **标准规则确定，AI辅助解释：** AI可检索SOP、推荐任务模板、提示偏差和生成非安全关键说明；不得独立生成未经批准的通电顺序、保护定值或危险作业指令。
3. **安全门禁硬控制：** 缺少资质、作业许可、关键安全记录、设计审批或设备匹配时，系统不得放行相应高风险步骤。
4. **任务与证据一体：** 每一步拥有执行人、设备及拓扑版本、验收判据、照片/读数、时间戳、审核和重测历史。
5. **异常必须闭环：** 失败、阻塞、设计偏差、设备替换和现场技术求助均形成独立记录；不允许删除失败历史后直接改为通过。
6. **离线可作业但不能假确认：** 本地加密暂存、恢复同步；云端未确认的记录标记为Pending Sync。需要在线授权的安全关键操作离线时保持阻塞。

### 1.3 与其他模块的接口边界

| 模块 | 对M2的输入或输出 | 责任归属 |
|---|---|---|
| M1 项目建立与配置 | 已发布Project/Topology Version、设备SN和型号、Parameter Set、审批偏差、国家与运行模式 | M1为主数据来源，M2只引用不可自行覆盖 |
| M2 引导式安装 | SOP工作包、现场证据、缺陷、检查签署、G2放行记录 | M2为安装过程事实来源 |
| M3 调试与SAT | 接收G2通过记录、安装基线和通电前检查证据；负责正式调试及SAT用例 | M3不得用简单勾选替代M2安装证据 |
| M4 项目交接 | 调用M2通过步骤、版本、证据链接及未结项 | M4生成正式报告和业主确认 |
| M5 现场服务 | 可回看M2原始安装记录与后续改动 | M5只创建售后记录，不修改原始安装事实 |
| M6 远程技术协同 / RSP | 接收现场技术求助、证据、风险等级及专家回复 | 技术协作记录回挂M2任务 |

## 2. 输入基线及启动前置条件

### 2.1 M1发布基线（强制）

必须取得Project ID、项目分类、Topology Version、项目级设备资产清单、设备-节点映射、三类拓扑关系（Electrical / Communication / Control）、Parameter Set引用、M1设计差异与批准结果、设计文件版本及EPC负责人。

项目分类遵循：LV-01单台区、LV-02多台区协同；MV-01单中压母线、MV-02多母线/多馈线；MV-03作为待确认的中压微网功能模板/特化分类。多个独立运行台区分别建LV-01；电气联络是拓扑属性而不是独立项目类别。

### 2.2 现场条件及额外输入

| 输入对象 | 必要字段 | 规则 |
|---|---|---|
| SiteCondition | 海拔/环境类别、室内外、温度范围、基础条件、消防约束 | 与设备安装适用条件匹配；超限需工程确认 |
| CountryRulePack | 国家/地区、适用法规版本、资格要求、标准验证项 | 不能以全球统一常数取代当地法规 |
| PersonnelAssignment | EPC、人员ID、角色、证书有效期、授权产品线 | 安全关键步骤验证人员资质 |
| WorkPermit | 许可编号、作业区域、有效期、批准人、危险类别 | 高风险作业许可过期自动阻塞 |
| SOPCatalog | 文档ID、产品/型号适用性、版本、审批状态、语言 | 只允许Published版本进入正式工作包 |
| ToolCalibration | 测试仪器ID、有效检定/校准期、测量范围 | 对要求仪器证据的步骤必检 |

### 2.3 启动检查（M2-G0）

- M1工程基线已Released，且至少存在一个合格的设备/拓扑配置。
- 适用SOP模板及国家规则包可以解析且均为有效发布版本。
- 施工EPC团队有项目授权，关键工种证书有效。
- 存在未闭合的关键设计偏差时，不得下发受影响工作包；其他不相关包可按依赖关系分批发布。

## 3. 工作包生成引擎

### 3.1 标准工作包（WP）

| 编号 | 工作包 | 主要任务 | 证据/输出 | 与M3边界 |
|---|---|---|---|---|
| WP01 | 施工准备 | 人员、PPE、图纸、风险评估、工作许可、工具校准 | 资格记录/许可/风险清单 | 仅作业准备 |
| WP02 | 机械安装 | 设备定位、固定、通道、散热、基础、环境检查 | 照片/尺寸/记录 | 无正式通电测试 |
| WP03 | 电气安装 | 接地、AC/DC接线、保护与隔离装置接线核验 | 检查单/仪表读数 | 不执行保护动作试验 |
| WP04 | 通信安装 | 通信线、端接、地址及拓扑映射 | 线缆记录/地址检查 | 在线通信联测由M3负责 |
| WP05 | 配置准备 | 产品与固件适用性、控制/保护参数版本引用、配置核对 | 配置快照/偏差 | 正式调参与验证由M3负责 |
| WP06 | 上电前检查 | 必要安全测试、极性、相序、隔离状态和工具回收 | 测量/双人签认 | G2电气准入证据 |
| WP07 | 受控上电交接 | 依据批准的具体设备SOP核对上电许可、就绪条件、交接人 | Energization Permit、交接记录 | 实际通电调试和SAT以M3为主；M2不自动驱动设备动作 |

### 3.2 分类派生规则

- LV-01：单台区工作包，以PCC/低压母线、储能、光伏及可选柴油机/EV充电设备为范围。
- LV-02：对每个台区复用LV-01作业模板，外加项目级EMS、跨台区通信/时钟同步/协调接口的安装检查包；联动功能测试保留给M3。
- MV-01：增加中压进线、变压器接口、中压设备、保护边界和合格人员许可检查。
- MV-02：在MV-01基础上按母线/馈线/分段/联络开关派生独立检查节点，严禁隐含默认联锁逻辑。
- MV-03：仅在厂家批准模板与项目合同明确时增加微网特有检查包；不能仅凭“微网”标签推导保护整定与并离网操作。
- 含柴油机或充电桩的项目只增加相应接口、机械/电气/通信安装作业；功能联动测试属于M3。

### 3.3 规则引擎与任务生成流程

1. 读取M1 Released snapshot并计算输入指纹（baseline_hash）。
2. 校验模板、产品兼容性和CountryRulePack有效性。
3. 按拓扑节点类型、设备能力、工作区域、能源组成匹配SOP模板。
4. 生成WP/Step实例、依赖有向无环图（DAG）、前置条件、风险级别与取证要求。
5. 对重复模板合并共享检查项，对不同台区/设备按实例展开，不可跨SN误合并。
6. 执行静态规则校验（缺失步骤、互相循环依赖、安全门禁缺漏、过期SOP）。
7. 输出计划预览及生成差异；EPC负责人核准后将Plan状态设为Published。

### 3.4 规则冲突优先级

适用强制法律/强制规范 → 项目已批准技术要求 → 厂家具体机型有效SOP → 经批准的工程模板 → 一般推荐模板。发现冲突必须生成Conflict记录要求工程审核，不得自动选择较宽松规则。需由法务/工程确认具体法律适用，不由AI自行作合规裁决。

## 4. 工作步骤数据结构及状态机

### 4.1 Step标准字段

| 字段 | 类型/示例 | 说明 |
|---|---|---|
| step_id / instance_id | UUID | 模板步骤ID与现场实例ID分开 |
| project_id / baseline_id | String / UUID | 必须指向M1发布基线 |
| work_package_id / topology_node_id | UUID | 工作包及物理工作范围 |
| asset_ids / sn_refs | UUID[] | 多设备步骤支持多个SN |
| sop_id / sop_version | String | 只引用批准发布的SOP |
| prerequisites | StepID[] | 上游依赖、许可、人员、仪表及安全状态 |
| risk_level / ppe | Enum / List | 一般、重要、安全关键及防护措施 |
| instruction / media_refs | Versioned links | 操作文档及小于30秒的指导视频 |
| acceptance_criteria | Typed rules | 上下限、枚举、图片、签名及人工检查标准 |
| evidence_schema | JSON schema ref | 类型、单位、精度、照片数量和定位 |
| assignee / reviewer | UserID | 执行/审核权分离 |
| started_at / finished_at | Datetime | 现场审计时间 |
| status / attempts | Enum / Integer | 状态与重测次数 |
| deviation_refs / support_case_refs | IDs[] | 关联偏差及技术协同 |

### 4.2 状态机

`Not Started → In Progress → Passed`；`In Progress → Failed / Blocked`；`Failed → Recheck → Passed/Failed`；`Blocked → In Progress`仅在阻塞条件解除并审计后允许。仅满足明确的“不适用”规则才可设为`Not Applicable`，该状态需审核并记录依据。关键步骤不允许普通用户Skip。

工作包状态由其子步骤计算：有安全关键Failed则Fail；存在Blocked则Blocked；所有必做步骤Passed（或合法N/A）才Passed。Plan状态：Draft / Review / Published / Executing / Suspended / Completed / Superseded。

## 5. 页面与交互详细设计

| 页面ID | 名称 | 主要区域及动作 | 必须提示 |
|---|---|---|---|
| UI-01 | Installation Dashboard | 项目、基线版本、WP完成率、阻塞项、未同步数、风险提示 | 当前拓扑和SOP版本 |
| UI-02 | Plan Generation | 输入摘要、适用SOP、生成WP预览、冲突审查、审批发布 | 未发布基线不得开始 |
| UI-03 | Work Package Board | 按区域/台区/设备/风险筛选，依赖顺序与指派 | 阻塞原因及前置任务 |
| UI-04 | Step Execution | 逐步说明、图示、<30s短视频、现场测量/照片、判据、求助 | 安全提示不可遮蔽 |
| UI-05 | Evidence Capture | 数据录入、单位校验、照片/视频、仪器编号、电子签认 | 数据真实性和完整性 |
| UI-06 | Deviation & Rework | Failed项、原因、整改单、复检、重新审批 | 原始失败记录不可删除 |
| UI-07 | Technical Help | 查SOP、FAQ、30秒视频、联系RSP、上传日志 | RSP回执与在线状态 |
| UI-08 | Gate & Release | G2检查、双人签认、解除阻塞、推送M3 | 不合格禁止放行 |

现场体验要求：大字体和戴手套场景可操作、照片断网保存、多语言/国家单位显示、二维码扫码定位当前设备、上一项/下一项导航；所有关键步骤均显示项目/设备SN和拓扑节点防止误操作。

## 6. 现场证据、验收与电子签署

### 6.1 证据类型

- NumericMeasurement：测量值、单位、测试方法、仪器ID、校准状态、期望范围及判定。
- PhotoEvidence：原始文件、拍摄时间、步骤/设备绑定、不可变更存储哈希；涉及客户隐私须受控。
- ChecklistEvidence：逐项确认及执行人；不能替代强制的实测。
- ConfigurationSnapshot：源系统、版本、采集时间、SN及关键设置引用。
- PermitSignature：签署人、授权范围、签署时间、文档版本及签署意图。
- Attachment：单线图/施工记录/厂家批准函，附文件校验和版本。

### 6.2 规则

照片上传不能自动视为安装合格；检测数值必须与明确限值和仪器要求比较；超限值不可绕过为Passed。关键检查必须双人签认时，执行人和复核人不得是同一身份。测量及签名可设为离线待提交，但要求在线服务许可/远程授权的步骤未取得确认前不得放行。

## 7. 安全门禁G2与受控上电交接

### 7.1 G2放行前提

1. 相关M1基线及关键设计差异已审批；无影响当前作业的未授权变更。
2. WP01–WP06适用的安全关键步骤全部Passed。
3. 对应设备、工作区域和实际施工人员的资质/许可有效。
4. 必要仪器记录与测量证据符合判据，涉及复核的步骤已双人签认。
5. 产品型号与SN映射一致；影响安全的现场设备替换已重新审批。
6. 必要现场安全隔离、状态交接与应急预案已确认。
7. 拟进行的上电/调试活动具有经批准的设备SOP及负责工程师。

### 7.2 G2输出

产生签名的`InstallationReadinessCertificate`（G2证书），包含Project ID、Topology Version、涉及设备SN、WP完成快照、关键证据哈希、批准人、有效时间和例外事项。M3只能引用有效G2；M1版本变更、重大返工或安全风险状态变更将触发失效评估，受影响范围需重新检查。

### 7.3 不允许的捷径

- App不能自行开启断路器或执行高压/储能电池带电操作。
- AI文本推荐不构成厂家批准的安全操作规程。
- 工程经理普通权限不能覆盖强制的国家法律资格或安全门禁。
- 现场检查通过不等于SAT通过，更不等于业主验收。

## 8. 异常、返工和设计变更

| 异常 | M2处理 | 跨模块处理 |
|---|---|---|
| 现场SN与M1资产表不符 | 阻塞相关步骤并现场记录证据 | M1启动设备替换/绑定审批，重新发布基线 |
| 拓扑与现场不符 | 记录Deviation，暂停受影响任务 | M1设计变更审核，M2重新生成增量任务 |
| 实测值未通过 | Failed、建立整改任务、保留原始读数 | 需要时升级M6/RSP |
| SOP无适用模板 | 停止自动发布，列为工程模板缺口 | 工程技术团队发布并审批SOP后再生成 |
| 安全证书过期 | Blocked；禁止相关危险作业 | 人员培训/认证系统更新后复核 |
| 短视频不可用 | 可继续查看正式SOP | 不得以媒体故障绕过安全说明 |
| 无网络 | 本地缓存证据与非需在线授权的检查 | 恢复后幂等同步；在线授权步骤仍Block |
| 项目配置更新 | 与baseline_hash比对，标识受影响任务 | 受影响WP重生成并审查已完成记录适用性 |

### 8.1 增量重生成

只对受变更影响的拓扑节点、资产及依赖下游重新计算；已执行步骤原始记录保持只读，必要时生成Reinspection任务。禁止直接重写旧Evidence来匹配新版本。

## 9. 远程帮助、视频与知识库

- 优先按Step ID + Model + Firmware + Country + Language检索厂家已批准指导资料，展示适用版本与注意事项。
- 短视频目标30秒以内，定位单一动作或常见问题；涉及高风险步骤仍需打开完整SOP。
- 一键求助RSP时自动携带Project ID、Topology Version、WP/Step、设备SN、报错及现场授权上传的证据。
- RSP返回Ticket ID、负责工程师、指导意见、附件和状态；回复属于技术协作记录，不自动放行安全门禁。
- 对复杂问题可采用文字、图片、视频通话/预约等方式，具体实现依现有RSP能力确定。

## 10. 数据库实体及字段设计

| 实体 | 核心字段 | 关键约束 |
|---|---|---|
| InstallationPlan | id, project_id, baseline_id, baseline_hash, status, generated_at, published_at | 一个基线可以多次生成，但Published版本不可覆盖 |
| WorkPackage | id, plan_id, code, zone_id, parent_wp_id, status, sequence | 允许LV-02台区子包 |
| StepTemplate | id, sop_id, version, applicability_rule, evidence_schema, risk_level | SOP Published才可生产实例 |
| StepInstance | id, wp_id, template_id, topo_node_id, asset_refs, status, assignee | 关键外键到M1基线及设备 |
| StepDependency | source_step_id, target_step_id, dependency_kind | 不允许有向环 |
| StepAttempt | id, step_id, attempt_no, result, started_at, finished_at | Failed与复测均永久留存 |
| Evidence | id, attempt_id, kind, value, unit, file_id, hash, device_sn, captured_at | 只追加，不可无痕修改 |
| WorkPermit | id, project_id, permit_no, scope, valid_from/to, approver | 有效性在线/离线按规则验证 |
| Deviation | id, project_id, step_id, origin_baseline, impact, status, approval_ref | 关键偏差须M1审查 |
| SupportTicketLink | id, step_id, rsp_case_id, status, last_sync_at | RSP ID必须可追溯 |
| GateDecision | id, gate_code, plan_id, outcome, blockers, approvers, evidence_hash | G2放行可审计 |
| InstallationAudit | id, entity, entity_id, actor, action, old/new_hash, timestamp | 审计日志不可被普通用户清除 |

## 11. API及事件契约建议（逻辑接口，需与既有平台核对）

| 接口 | 方法/路径（建议） | 功能 |
|---|---|---|
| M1基线查询 | GET /projects/{id}/baselines/{version} | 拉取拓扑、设备、参数快照 |
| 计划生成 | POST /installation/plans/generate | 输入baseline_id及rulepack_version，输出Draft计划 |
| 计划预览/发布 | GET /installation/plans/{id}; POST /installation/plans/{id}/publish | 查看差异、审核发布 |
| 步骤证据上传 | POST /installation/steps/{id}/attempts | 提交结构化测量及执行记录 |
| 附件上传 | POST /installation/evidence/uploads | 预签名/分块上传、校验哈希 |
| 整改单 | POST /installation/deviations | 创建Fail/设计偏差 |
| 技术求助 | POST /rsp/support-cases | 创建或关联RSP Case |
| G2校验 | POST /installation/plans/{id}/gate-check | 返回阻塞项与判定规则 |
| G2批准 | POST /installation/plans/{id}/release-to-m3 | 生成准入证书并发事件 |

幂等要求：生成计划、上传证据、审批及事件发送均使用idempotency_key；冲突响应不得静默覆盖。权限验证和关键门禁必须在服务端执行，客户端UI禁用按钮只是辅助。

### 11.1 事件

`InstallationPlanPublished`, `InstallationStepFailed`, `DeviationCreated`, `SupportRequested`, `InstallationReadinessGranted`, `InstallationReadinessRevoked`。事件携带event_id、project_id、baseline_id、version、occurred_at、correlation_id。采用重试+去重+死信队列机制，确保RSP及M3消费幂等。

## 12. 权限矩阵与数据保护

| 角色 | 主要权限 | 限制 |
|---|---|---|
| EPC现场工程师 | 执行获分配步骤、录入证据、发起求助 | 不能发布SOP及跳过安全门禁 |
| EPC责任工程师 | 发布普通安装计划、分配任务、审核一般偏差 | 重大设计变更需M1审批，关键门禁另授权 |
| 安全主管/授权见证人 | 复核安全检查、签署许可 | 不得代他人伪造测量或签名 |
| LIVOLTEK工程技术 | 维护批准SOP、专家技术审核、例外处理 | 不能绕过适用法律与强制许可 |
| 地区部/VAP协调人员 | 看进度、服务协调、授权的只读报告 | 不得修改EPC原始测试证据 |
| RSP工程师 | 查看项目证据、回复技术支持、发起升级 | 不自动获得现场高风险操作权 |

采用按项目及组织隔离的RBAC/ABAC；用户与设备访问留痕，敏感照片/个人联系方式按适用地区法律处理；离线数据加密，重要签章服务端验签。

## 13. 非功能需求及可靠性

- App应支持弱网/离线保存并提供同步队列可视化，重复上传不会生成重复记录。
- 现场拍照与测量表单必须支持断点恢复；文件写入带完整性校验。
- 不允许因App崩溃而丢失已确认提交的证据；审计追溯需保留操作人和版本。
- 正式SOP在设备离线时可缓存，但失效/撤回的SOP不可用于新生成计划；重新联网必须校验版本。
- 多语言、单位和时区呈现一致，原始记录统一单位/UTC保存并记录采集源时区。
- 可观测性包括计划生成失败率、任务同步延迟、G2阻塞原因、SOP覆盖率、离线冲突次数。

## 14. 验收用例（UAT）

| ID | 场景 | 预期结果 |
|---|---|---|
| M2-01 | M1未发布拓扑 | 计划生成被阻止，明确缺少Released baseline |
| M2-02 | LV-01光储 | 自动生成匹配设备的WP01–WP07及正确依赖 |
| M2-03 | LV-02三台区 | 各台区单独作业包，增加项目级EMS接口检查 |
| M2-04 | MV-02多馈线 | 派生母线/馈线/联络相关检查，不自动假设保护逻辑 |
| M2-05 | 柴油机/EV设备不存在 | 不生成无关安装步骤及联动测试 |
| M2-06 | SOP已撤回 | 禁止生成新发布计划，明确模板缺口 |
| M2-07 | 未完成前置检查 | 后续步骤Blocked并显示原因 |
| M2-08 | 许可证或人员证书过期 | 安全关键步骤不可开始/G2不可通过 |
| M2-09 | 实测值超限 | 自动Failed，保存原测量证据，整改复检保留历史 |
| M2-10 | 错误SN扫码 | 阻塞该设备步骤，要求走M1差异/替换流程 |
| M2-11 | 网络中断上传照片 | 本地安全暂存，恢复后去重同步并可确认回执 |
| M2-12 | 一键联系RSP | 自动附项目、SN、步骤、照片并返回Ticket ID |
| M2-13 | AI建议危险顺序 | 只能参考批准SOP，不能生成可执行危险动作 |
| M2-14 | M1配置变更 | 受影响步骤需重验证，旧证据不可被覆盖 |
| M2-15 | 非关键步骤合法N/A | 有规则依据和审核记录；不影响不相关工作包 |
| M2-16 | 缺少关键安全证据 | G2失败，明确阻塞项，M3无法开始受影响调试 |
| M2-17 | 全部条件满足 | G2证书含基线、SN、签署、证据哈希，M3可读取 |
| M2-18 | 同一提交重复发送 | 服务端幂等，无重复步骤或证据 |

## 15. 开发拆分及与M3交接

### 15.1 实施拆分（仅M2）

1. 数据契约及SOP模板目录：规则版本、设备适用性、证据字段；联调M1发布快照。
2. 生成引擎：设备/拓扑匹配、WP实例化、DAG排序、冲突与规则审查。
3. EPC现场UI：任务看板、步骤执行、扫码定位、证据录入、离线缓存。
4. 异常及RSP：Failed/Recheck、偏差、技术求助及回执。
5. 安全门禁与M3：服务端G2校验、签署证书、M3事件及撤销逻辑。
6. UAT与安全审计：以LV-01、LV-02、MV-02真实项目数据进行验证。

### 15.2 M2交付M3的最小数据集

`project_id, baseline_id, baseline_hash, installation_plan_id, completed_wp_ids, step_attempt_refs, required_evidence_refs, unresolved_deviations, gate_g2_result, readiness_certificate_id, reviewer_signatures, generated_at`。

M3须校验G2证书是否有效；如基线发生安全相关变更，先返回M2补检而不是沿用旧的合格记录。

## 16. 待评审及冻结的关键事项

| 项目 | 建议决策 | 责任团队 |
|---|---|---|
| G2与M3的上电边界 | M2仅提供安装就绪及许可，M3负责授权实际通电调试 | 研发/售后/EPC/EHS |
| SOP版本生命周期 | Draft–Approved–Published–Withdrawn | 产品研发/质量 |
| CountryRulePack来源 | 国家法规和工程规范由合规/工程负责人维护 | 法务/工程 |
| 工商业Installer App与RSP | 共用Project ID及Case ID，不独立造项目 | 平台架构 |
| 安全级双人签署范围 | 按设备与国家要求逐项确定 | EHS/技术 |
| 离线授权边界 | 高风险操作需在线或预先签发且有效的许可 | EHS/平台 |
| M1版本变更影响 | 影响分析及重生成增量任务机制 | M1/M2负责人 |
| 项目标准模板首批范围 | 优先LV-01光储、LV-02协同、MV-01储能 | 产品线/EPC |

**本文件定位：** M2详细设计建议稿，非已批准的电气施工技术规程。所有现场危险操作与验收阈值须引用具体产品/国家经审核的SOP及项目设计文件。
