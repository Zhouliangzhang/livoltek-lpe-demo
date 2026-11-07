# LIVOLTEK Project Engineer

## 修订总原则：完整相关系统建模与合同责任分离

**产品定位（修订后的权威定义）：** LIVOLTEK Project Engineer 是主设备厂家提供给EPC工程师的系统感知型安装调试辅助、现场故障排查及远程技术支持协同工具。它不取代EPC专业电气设计、施工管理、法定检验或合同验收工具。

**系统建模覆盖范围：** 凡是会实质影响LIVOLTEK设备的安装、控制、保护、并离网协同、自测、系统功能或故障定位的设备和接口，均须纳入相关系统模型；无论其品牌、供货商或是否由LIVOLTEK生产。包括第三方PV逆变器、柴油机、ATS/STS、变压器、电表、保护开关、充电桩及相关负载/电网边界。无需复制整座工厂或EPC的全部工程设计。

**模型深度独立于品牌：** L1为具备完整参数/遥测/控制资料的设备级模型；L2为支持关键指令、反馈、通信映射及接口验证的集成设备模型；L3为仅建模边界、额定参数、运行状态和关键测量的简化外部系统。第三方设备可以达到L1，LIVOLTEK设备也可因资料不全暂处待核验状态。

**权限与责任分离：** `manufacturer`描述设备品牌；`responsibility_owner`描述工程/合同责任；`control_capabilities`描述技术可用性；`authorization`单独约束谁在何种条件下有权读写、控制和执行测试。**可建模≠可远程控制≠厂家承担质保。**

**数据与安全：** 第三方设备接入须有协议/寄存器来源和兼容性验证；无有效数据不得模拟真实故障结论或显示实时能量流动；无授权不得写第三方参数、触发保护或远程启动设备。未知字段和未批准SOP允许形成待评审草案，不得自动发布生产作业。


## 本版变更控制：V2.1 相对 V2.0

| 变更范围 | 变化与验收焦点 |
| --- | --- |
| 产品定位 | 定义为EPC的厂家辅助平台，不代替EPC专业工具；但覆盖全部相关系统设备 |
| M1 | 完整相关系统拓扑、第三方设备L1/L2/L3、外部系统边界、接口映射及信息来源 |
| M2 | 厂家设备安装辅助 + 与第三方设备的必要接口检查，避免擅自生成第三方内部施工SOP |
| M3 | 设备/接口/系统三级自测，明确测试执行权限、测点证据与第三方验证边界 |
| M4 | 输出厂家设备及约定接口的安装调试/系统功能记录；不冒充整个EPC的合同最终验收 |
| M5 | 基于完整拓扑诊断PCS/BMS/EMS/第三方设备/电网/负载全链路原因 |
| M6 | 工程师与厂家共享项目版本、遥测、诊断证据和授权操作日志，支持RMA升级 |

### 六模块贯穿的三项数据契约

1. `system_context_baseline`：M1发布的拓扑/资产/端口/测点/控制权限快照，M2-M6以同一版本引用。
2. `interface_contract`：协议、寄存器/信号定义、方向、单位、采样质量、授权范围和第三方资料依据；M3和M5不得使用未核实映射作通过判据。
3. `test_and_diagnostic_scope`：每个测试或故障排查规则声明适用设备、接口、执行方式（AUTO / ASSISTED / MANUAL_WITNESS）、厂家与EPC责任边界、所需证据与限制。

### M3系统自检范围的新增例子

| 子系统 | 相关外部设备 | 可以验证的内容 | 不等于验证的内容 |
| --- | --- | --- | --- |
| PV + BESS | 第三方光伏逆变器、电表 | 通信、功率值方向、EMS调度限制接口 | 第三方逆变器全部内部性能 |
| PV + BESS + Diesel | 第三方柴油机、启停控制器、ATS | 启停请求及反馈、允许条件、联动状态（按授权） | 柴油机整机安全和发电机出厂性能 |
| 储充 | 第三方充电桩、站级电表 | 功率分配指令、状态回传、功率限值效果 | 充电桩整机认证 |
| LV-02 | 多台区电表及EMS | 台区级和项目级协调、各PCC功率约束 | 不存在的台区物理电气联络 |

### M5故障链路（新增）

案例“BESS没有按EMS指令放电”：先读取EMS调度命令，再核查SOC/BMS许可、EMS→PCS通信反馈、PCS保护/降额、断路器与电表读数、外部电网/负载/第三方设备约束；每一步按可获取证据给出`CONFIRMED / SUSPECTED / UNKNOWN`，缺测不等于正常。RSP派发给EPC的现场检查任务必须带原项目/设备SN/拓扑版本及已完成检查项。


---

## 既有详细设计（未冲突条款继续适用）

工商业工程师App产品需求说明书（PRD） V2.1

System-Aware Installation, Commissioning & Field Troubleshooting Assistant

文件状态：讨论及研发评审稿  |  日期：2026-11-06  |  适用：工商业光储、光储柴、储充、光储充、微电网

定位：主设备厂家提供给EPC的系统级安装调试辅助、现场故障排查及远程技术支持协同工具，涵盖相关第三方设备但不取代EPC专业工程工具。

## 1. 设计目标与边界

- 以Project ID为贯穿主线，建立一次、全程复用；安装报告形成RSP可机器读取的原始项目服务档案。

- 先项目电气分类，后系统拓扑，最后能源配置与运行模式；不以“光储柴”等能源标签代替工程结构。

- 经批准的Topology + Device Master + SOP Library + SAT Test Library驱动任务生成；AI只作辅助，不自主编造危险操作。

- EPC承担现场工程与一线排障；LIVOLTEK通过RSP提供远程诊断、技术升级、产品保修和RMA支持。

- 支持离线执行与恢复同步、逐步门禁、证据留存、版本控制、权限审计。

非目标：App不是CAD/继电保护整定软件；不自动替代执业工程师批准的设计图和安全方案；不直接承诺项目整体性能或代替合同FAT/SAT；不将户用VAP补偿体系套用于EPC工程项目。

## 2. 六大产品模块总览

| 模块 | 英文名称 | 核心功能与产出 |
| --- | --- | --- |
| M1 项目建立与配置 | Project Setup | 项目分类、台区/母线/馈线、Topology、设备SN及关键参数、设计差异管理 |
| M2 引导式安装 | Guided Installation | 生成作业包、检查清单、SOP、短视频、质量/安全门禁和现场证据 |
| M3 调试与SAT | Commissioning & SAT | 单设备→子系统→系统测试、自动读取、半自动检查、异常整改 |
| M4 项目交接 | Project Handover | 自测报告、As-built及客户确认、数字签署、RSP交付基线 |
| M5 现场服务 | Field Service | RSP派发任务、原档案回显、测量/维修、换件、复测、记录回写 |
| M6 远程技术协同 | Remote Support | 与RSP Case协作、日志上传、远程专家指导、升级及RMA申请 |

## 3. 项目分类规则（定版建议）

第一层按电气接入层级分类：LV低压项目、MV中压项目。电压边界由所在国标准和合同确定，系统不写死全球单一阈值。

| 代码 | 分类 | 定义/边界 |
| --- | --- | --- |
| LV-01 | 单台区 Single Transformer Zone | 一个变压器低压侧供电边界内的项目；可包含多台PCS、储能柜、光伏、充电桩及柴油机。 |
| LV-02 | 多台区协同 Coordinated Multi-Transformer Zones | 两个及以上台区需要跨台区能源协调/统一控制，建立统一项目及台区级子拓扑。 |
| MV-01 | 单中压母线 Single MV Bus | 中压接入及单母线系统，包含下接变压器与LV子系统。 |
| MV-02 | 多母线/多馈线 Multi-Bus/Feeder | 多个母线分段、馈线与变压器，保存联络开关及保护边界。 |
| MV-03 | 中压微电网 MV Microgrid | 具备经批准的中压微网运行能力；作为MV的功能特化模板，必要时可与MV-01/02共享拓扑模型。 |

分类裁剪规则：原“多台区独立运行”LV-02取消；独立台区按多个LV-01分别管理。原“多台区协同”和“多台区可联络”合并为新的LV-02；电气联络关系作为Topology属性，EMS协调方式作为控制属性，不额外产生项目分类。

第二层选择电气结构参数：PCC数量与电压、变压器/台区数量、母线与馈线、开关及联络关系、保护边界、计量点。第三层选择能源构成：ESS、PV+ESS、PV+ESS+Diesel、ESS+EV、PV+ESS+EV、自定义；第四层选择运行模式：并网、可切换并离网、离网。

多台区协同并不表示台区低压母线可以任意并联。App必须区分物理电气连通、通信连通及EMS控制协调三种关系，并以审批图纸和实际保护条件约束。

## 4. M1 Project Setup：项目建立、拓扑与设备配置

### 4.1 EPC作业流程

- 新建项目：国家、客户、EPC、合同/设计编号、项目坐标或地址，生成唯一Project ID。

- 选择LV/MV、对应第二层分类、能源配置、运行模式；对LV-02设置台区数及每台区属性。

- 选择已批准的标准拓扑模板，或导入审定的单线图及设计清单；人工确认PCC、变压器、母线、馈线、设备、通信及控制关系。

- 扫码设备二维码，录入SN、型号、固件、PCS/BMS/EMS关系；无法扫码的第三方设备选择兼容型号或受控录入。

- 录入现场关键参数、控制约束及设计版本；App自动执行型号兼容性、设备遗漏、SN重复、拓扑不闭合及变更差异检查。

- EPC责任工程师审核拓扑；涉及设备替代、保护与接线重大变化的提交设计变更审批，形成Topology Version。

### 4.2 数据对象

| 对象 | 关键字段 |
| --- | --- |
| Project | Project ID、客户、国家、地点、合同、EPC、运行模式、状态 |
| Electrical Node | PCC、TransformerZone、Bus、Feeder、Breaker/Switch、Load、Asset |
| Topology Edge | from/to节点、连接种类（Electrical/Communication/Control）、状态、设计版本 |
| Device Asset | Asset ID、SN、Model、Product ID、Firmware、Topology Node ID、Owner/Installer |
| Parameter Set | 额定参数、通信地址、控制模式、保护配置引用、版本及审批记录 |
| Deviation | 设计值/实测值、照片、影响评估、审批人、关闭状态 |

G1门禁：拓扑经EPC责任人审核，关键设备和接口有定义，严重设计差异未解决时不得下发相关安装任务。

## 5. M2 Guided Installation：引导式安装

SOP生成输入：Topology Version + Device Asset Register + 国家规范包 + 机型安装手册 + 已批准的SOP模板 + 现场条件；产出依赖关系明确的动态工作包（Work Package）。

| 作业包 | 典型工作 | 数字化证据 |
| --- | --- | --- |
| WP01 施工准备 | 人员资格、PPE、许可、图纸、工具、工作环境 | 人员认证、风险检查、许可编号 |
| WP02 机械安装 | 基础、固定、散热空间、环境 | 照片、测量值及检查签署 |
| WP03 电气安装 | 接地、AC/DC连接、隔离保护装置 | 接线检查、仪表读数及检验记录 |
| WP04 通信安装 | 设备地址、线路、协议、EMS映射 | 在线状态、通信诊断结果 |
| WP05 设备配置 | 固件、并网制式、BMS/PCS/EMS参数 | 配置快照及版本 |
| WP06 上电前检查 | 极性、相序、绝缘及安全条件 | 必填测试记录与合格判据 |
| WP07 受控上电/设备调试 | 按经批准的厂商步骤分设备调试 | 调试结果及异常记录 |

每一步须有：任务ID、前置条件、SOP版本、适用设备、操作要点、风险与PPE、验收判据、现场照片/测量值、执行人、时间、失败原因、重测历史。可弹出30秒以内教学短视频，但高风险作业以完整官方SOP为准。

状态：Not Started / In Progress / Passed / Failed / Blocked / Recheck。关键步骤不允许普通用户跳过；安全敏感操作不得由AI自由生成操作顺序或保护定值。

G2门禁：全部适用的安全关键检查通过，相关人员资格有效，必要审批完成后才开放相应受控调试。

## 6. M3 Commissioning & SAT：调试、自测及系统验收

按三层测试生成计划：T1设备级（自检、固件、通信、告警）；T2子系统级（PCS-BMS、EMS、计量、保护与通信）；T3系统级（运行策略及跨设备协同）。测试用例选择以实际Topology和功能许可为条件。

| 测试场景 | 最低验证范围 | 适用条件 |
| --- | --- | --- |
| PCS/BMS | SOC、充放电许可、告警、限值与通信一致性 | 含BESS |
| EMS设备映射 | 设备在线、测量方向、命令/反馈、异常告警 | 含EMS |
| 防逆流/需量控制 | 计量点、设定值、控制响应及失效安全 | 已配置功能 |
| TOU策略 | 时间表、策略切换与实际执行结果 | 已配置功能 |
| 并离网能力 | 切换条件、保护、许可和状态恢复 | 经批准支持并离网 |
| 柴油机联动 | 接口、启停条件、功率协调及安全机制 | 光储柴 |
| 储充协调 | 充电功率分配及负载限制 | 储充/光储充 |
| LV-02跨台区协调 | 各台区自测后验证项目级EMS聚合控制 | LV-02 |
| MV保护与控制 | 分段/馈线监控、保护及联锁测试证据 | 中压项目 |

测试执行分类：Auto（控制器自动采集）；Assisted（App引导并采集工程师数据）；Manual Witness（持证人员实施，App仅记录证据）。电气动作、保护测试、带载切换不得因测试引擎自动生成而未经授权执行。

结果：Pass / Fail / Blocked / Not Applicable，附判据、实测值、设备及拓扑版本、证据及执行人。故障进入整改清单，复测保留原失败记录。

G3门禁：全部必须的测试通过；关键安全/功能失败不得生成合格报告。允许带遗留项交接的，应符合项目合同和授权流程。

## 7. M4 Project Handover：报告、业主确认与RSP归档

自动生成《Installation, Commissioning & Self-Test Report》：项目及各方信息、As-built拓扑、设备SN、安装步骤记录、全部适用SAT、测试实测值、异常与整改、EPC签字、业主接收/验收/异议记录。

交接应区分：Receipt of Documents（资料接收）、Site Acceptance（现场验收）与Final Contractual Acceptance（合同最终验收）；不能因单次App电子签署自动等同于全部合同验收。

- EPC复核全部记录并签署；App生成可读PDF和不可变更的机器结构化归档包。

- 向业主提供设备清单、系统功能、检测结论、遗留项、服务联系人及使用注意事项。

- 记录业主确认或异议；对不满足交接门禁的项目标记待整改。

- 推送Project、Topology、Assets、Parameters、SOP execution、Test results、Signatures、Attachments至RSP。

- RSP核对关联键、报告版本和完整性；回执Archive ID与同步状态；建立Commissioning Baseline供后续故障诊断复用。

G4门禁：只有收到RSP成功归档回执，App才可显示“Cloud Handover Completed”；断网时可本地加密待同步，不得伪报成功。保修开始日期按正式保修政策计算，不能因App归档时间擅自更改。

## 8. M5 Field Service：EPC现场售后服务

现场服务入口从RSP派发的Case/Technical Task进入，而非为售后重建项目。EPC可读取原Project ID、设备SN、原As-built版本、初始参数、SAT记录、后续配置变更、维修与RMA历史。

- 工程师接任务并核验项目和设备；阅读RSP远程诊断结论和定向检查清单。

- 到场执行安全检查、测量及授权排障；记录实测与预期差异，必要时请求厂家远程支持。

- 如需换件，提交/关联RMA，执行获批准的设备更换，保留旧/新SN与版本谱系。

- 测试设备与相关系统功能恢复，上传前后证据，取得业主/现场运维代表确认。

- RSP复核运行告警及关键数据，技术关闭；费用责任与合同结算独立审核。

项目级工单关联建议：Project ID → Case ID → Technical Task/Work Order ID ↔ Equipment SN（多对多）→ RMA ID（可选）。避免单个系统级故障只能绑定一个SN的设计缺陷。

## 9. M6 Remote Support：与RSP远程专家协同

支持现场工程师在任务步骤内一键“Request Support”，自动发送Project ID、拓扑版本、设备SN、当前测试步骤、设备日志、截图、测量值和已执行步骤，减少重复问询。

| 功能 | 要求 |
| --- | --- |
| 技术会话 | 与RSP Case关联的消息/语音或视频链接、附件、责任人及审计记录 |
| 远程诊断 | 厂家查看授权运行数据、告警趋势及配置版本差异 |
| 专家升级 | L1 EPC→L2厂家支持→L3研发/控制专家，保留升级与反馈记录 |
| 远程指导 | 厂家给出批准的测试步骤、检查清单及预计风险，EPC现场执行与回传 |
| 远程参数操作 | 基于RBAC、用户授权、审批、二次确认和操作审计；安全关键参数须专门授权 |
| RMA协同 | 工单内提出换件申请、审核、备件、旧/新SN关联和恢复测试 |
| 知识库 | 依据产品、告警码、拓扑类型推送匹配的FAQ/SOP/短视频 |

RSP为Case与技术支持事实源；Project Engineer是EPC工程师操作端。监控平台保留设备数据事实源；两端不得产生互不关联的平行工单。

## 10. 六模块统一数据与系统接口

| 对象/接口 | 主数据归属 | 关键同步与规则 |
| --- | --- | --- |
| Project/Topology/Assets | Project Engineer提交、RSP归档 | 项目ID唯一；拓扑版本不可覆盖；SN去重 |
| Device Master/SOP/SAT | 厂家批准的主数据及内容服务 | 版本化下发；兼容性及适用范围受控 |
| Telemetry/Alarm | 设备网关/Monitoring/RSP | 按授权引用时间序列，不将全量数据存于手机 |
| Case/Technical Task/RMA | RSP | RSP主键与状态；App接任务与回写 |
| Commissioning Baseline | Installer App产生、RSP验收 | 结构化数据+PDF+签名与证据，记录哈希与回执 |
| EPC Identity/Certification | 身份与培训认证服务 | 资质有效性、岗位/设备权限和国家资质 |
| Audit/Notification | 各服务按事件推送与归档 | 幂等事件ID、重试队列、可追踪错误 |

建议关键API：POST /projects; POST /projects/{id}/topology-versions; POST /assets/bind; POST /work-packages/generate; POST /steps/{id}/results; POST /sat-runs; POST /handover-packages; GET /rsp/tasks; POST /rsp/tasks/{id}/field-reports; POST /rsp/cases/{id}/support-requests。具体路径为设计提案，需与现有RSP PRD核对后冻结。

建议验收事件：ProjectCreated、TopologyApproved、DeviceBound、SOPGenerated、StepVerified、SATCompleted、HandoverSigned、RSPArchiveAccepted、FieldTaskCompleted、RMAClosed。采用版本号、事件ID和幂等键，支持弱网补传。

## 11. 核心权限、安全及离线管理

- 角色：EPC Admin、Project Engineer、Certified Electrician、Commissioning Lead、Owner Reviewer、LIVOLTEK Remote Expert、RSP Approver、Auditor；使用最小权限。

- 危险参数调整及设备远程控制采取设备白名单、厂家批准的操作包、审批、二次确认、操作日志与应急回退。

- 项目、业主、位置和运行数据按国家隐私及跨境规则授权；照片与报告分项目访问控制。

- 离线可查看已缓存的批准作业包并采集证据；未经实时验证的安全关键操作不得简单解除门禁。

- 文档和设备配置采用版本锁定、审计日志与变更链；缺失数据标记待核验，不伪造设备状态。

## 12. 端到端流程与关键验收点

Project Classification → Topology Approved → Assets Bound → SOP Generated → Guided Installation → Commissioning & SAT → EPC Review → Owner Confirmation → RSP Archive Accepted → Operational Support → RSP Case → Field Service / Remote Support → Closed with Audit Trail

| 门禁 | 要求 | 失败处理 |
| --- | --- | --- |
| G1 拓扑审批 | 结构与设计一致，关键节点/设备齐全 | 变更单及工程师审批 |
| G2 安装合格 | 关键安全安装步骤通过 | 阻断受影响上电/调试 |
| G3 SAT通过 | 适用用例与实测证据满足判据 | 整改及复测 |
| G4 交接归档 | 签署、结构化包、RSP回执齐全 | 待交接/待同步，明确缺失原因 |
| G5 售后关闭 | 恢复验证、现场证据、客户确认及审计 | 继续工单/人工审批例外 |

## 13. 主要验收用例（UAT）

| 用例 | 验收结果 |
| --- | --- |
| U01 单台区光储 | 创建LV-01并生成对应SOP/SAT；可完整交付RSP |
| U02 多台区协调 | 创建LV-02，两台区独立完成设备测试后生成跨台区联调用例 |
| U03 多独立台区 | 提示分别建立LV-01，不错误强制归入LV-02 |
| U04 多台区电气联络 | 联络作为拓扑边属性，不额外生成项目分类 |
| U05 中压与下级LV | MV内可配置多个变压器和LV子拓扑 |
| U06 SN重复与设计不符 | 系统标记异常并阻止相关门禁通过 |
| U07 关键测试失败 | 不能生成合格验收结论，记录整改和重测历史 |
| U08 无网络交接 | 离线保存；恢复后幂等同步；回执前不宣称归档成功 |
| U09 后续故障服务 | RSP按原项目读取拓扑、SN、初次SAT和维修历史 |
| U10 EPC远程求助 | 请求携带项目和步骤上下文，并关联RSP Case |

## 14. 分阶段研发建议及待定事项

P0：冻结分类及统一Project/Topology/Asset数据模型，完成LV-01模板与RSP档案接口。

P1：扩展LV-02、MV拓扑模板，建设SOP驱动和安装作业门禁。

P2：建设T1/T2/T3 SAT、报告、业主签署和RSP正式归档。

P3：建设RSP派工现场服务与远程专家协作、RMA及故障数据闭环。

待定事项：MV-03是否作为正式类别或运行能力标签；各国家电压边界及法规包；具体机型SOP、SAT测试判据；EPC签署与业主合同验收法律文本；RSP现有接口、主数据归属和权限体系。上述事项需产品/研发/售后/法务联合确认。

结论：以“项目电气分类→拓扑与设备→受控作业→分层SAT→业主交接→RSP原始档案→现场服务/远程协同”为主线，六模块共用同一项目及设备资产底座，实现EPC工程作业标准化和全球远程售后支持。

