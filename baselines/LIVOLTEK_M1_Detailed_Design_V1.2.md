# LIVOLTEK Project Engineer

## 修订总原则：完整相关系统建模与合同责任分离

**产品定位（修订后的权威定义）：** LIVOLTEK Project Engineer 是主设备厂家提供给EPC工程师的系统感知型安装调试辅助、现场故障排查及远程技术支持协同工具。它不取代EPC专业电气设计、施工管理、法定检验或合同验收工具。

**系统建模覆盖范围：** 凡是会实质影响LIVOLTEK设备的安装、控制、保护、并离网协同、自测、系统功能或故障定位的设备和接口，均须纳入相关系统模型；无论其品牌、供货商或是否由LIVOLTEK生产。包括第三方PV逆变器、柴油机、ATS/STS、变压器、电表、保护开关、充电桩及相关负载/电网边界。无需复制整座工厂或EPC的全部工程设计。

**模型深度独立于品牌：** L1为具备完整参数/遥测/控制资料的设备级模型；L2为支持关键指令、反馈、通信映射及接口验证的集成设备模型；L3为仅建模边界、额定参数、运行状态和关键测量的简化外部系统。第三方设备可以达到L1，LIVOLTEK设备也可因资料不全暂处待核验状态。

**权限与责任分离：** `manufacturer`描述设备品牌；`responsibility_owner`描述工程/合同责任；`control_capabilities`描述技术可用性；`authorization`单独约束谁在何种条件下有权读写、控制和执行测试。**可建模≠可远程控制≠厂家承担质保。**

**数据与安全：** 第三方设备接入须有协议/寄存器来源和兼容性验证；无有效数据不得模拟真实故障结论或显示实时能量流动；无授权不得写第三方参数、触发保护或远程启动设备。未知字段和未批准SOP允许形成待评审草案，不得自动发布生产作业。


## V1.2新增：系统相关设备建模与接口层

### M1.15 相关系统覆盖规则

EPC建模者在录入LIVOLTEK设备后，必须按功能依赖识别外围设备：供电/PCC/变压器、光伏逆变器、柴油机/ATS、第三方EMS/电表、充电桩、重要负载及开关保护。对每项关系记录`relationship_reason`（CONTROL_DEPENDENCY / ENERGY_PATH / PROTECTION / TEST_DEPENDENCY / DIAGNOSTIC_DEPENDENCY）；不相关的工厂内部设备不强制建模。

### M1.16 设备建模等级与可见能力

| 级别 | 最少字段 | M3/M5能力 |
| --- | --- | --- |
| L1完整模型 | 设备型号、SN或替代唯一ID、端口、规格、测点/命令、版本、验证来源 | 设备诊断、接口测试、授权功能联调 |
| L2接口模型 | 设备角色、连接点、协议/信号映射、额定限值、命令与反馈 | 接口级自测与链路故障定位 |
| L3边界模型 | 设备/系统角色、连接位置、容量/电压、必要运行状态 | 边界条件与外部因素排查 |

### M1.17 第三方设备建档工作流

设备库选择已验证的第三方型号 → 若无匹配选择通用设备类别并标记`UNVERIFIED` → 收集供应商手册/协议表及版本 → 创建端口/关键点表 → 定义遥测刷新阈值和符号方向 → 标注可调用的诊断能力、可执行测试和实际授权 → EPC/厂家接口工程师审核 → 生成可用于M3/M5的接口基线。未经验证的接口不允许自动执行或作为SAT通过证据。

### M1.18 接口能力与操作授权解耦

`read_permission`、`write_permission`、`test_execution_permission`、`approval_ref`和`operator_role`独立于`telemetry_capabilities` / `control_capabilities`。产品自有可操作并不意味着任何工程师均获授权；第三方控制必须经过合同/厂家授权、站点许可及安全评估。

### M1.19 分层拓扑与依赖完整度验证

图形保留Electrical、Communication、Control三类连接；新增`integration_dependency`。若配置了柴油机联动功能但没有柴油机接口或反馈状态，则报`BLOCKER_FOR_DIESEL_TEST`；若计量仅有总表而无分支电表，则相应分支能量流标为不可用，不得按额定功率推断。LV-02按多个LV-01台区子拓扑 + EMS协同关系建模；MV可纳入多个LV子结构。

### M1.20 交给M2-M6的输出

发布版模型应附：system_context_baseline、device_inventory（manufacturer/modeling_level/responsibility_owner）、接口信号映射及来源、测试/诊断能力矩阵、遥测质量约束、权限范围、未确认字段列表、版本摘要和审批记录。

### V1.2新增验收用例

- UAT-31：在LV-01添加第三方光伏逆变器并设L2，能够完成接入关系及接口测点映射。
- UAT-32：柴油机未定义反馈点时，对柴油机联动测试报告阻塞原因。
- UAT-33：第三方设备有支持写入命令但无授权时，界面只能显示受限状态，不提供可执行动作。
- UAT-34：L3工厂负载可参与拓扑及故障分析而无需SN。
- UAT-35：M5可以按设备来源、工程责任、测点可信度区别显示诊断信息。
- UAT-36：删除关键第三方设备后，受影响M2、M3、M5依赖标红并要求重新确认。


---

## 既有详细设计（未冲突条款继续适用）

## M1 项目建立与配置（Project Setup）详细设计说明书 V1.2

**文档性质：** 产品详细设计／研发实施基线（讨论稿）  
**上游依据：**《LIVOLTEK Project Engineer 工商业工程师App PRD V2.0》第3、4、10—14章  
**覆盖范围：** M1 项目分类、设备Icon及三层拓扑编辑、设备建档与参数、动态有功功率流向预览、设计差异、审批发布和RSP基础档案同步  
**不覆盖：** M2安装SOP执行、M3 SAT执行、M4正式移交、M5维修作业、M6远程会话（仅定义所需接口）  
**版本：** V1.2｜2026-11-06

**V1.2变更摘要：** 在V1.0分类、拓扑、SN、审批、M2/RSP接口的基础上，新增Icon/端口/电气线路建模、Design/Commissioning/Monitoring三种视图模式、实时功率方向数据契约、测量质量控制、LV-02/MV分层显示、开源选型与验收用例。工程图与实时遥测严格分离；动态箭头仅依据有效测量值。

## 1. M1目标与交付边界

M1首先回答六个工程问题：项目在哪里、属于什么电气结构、设备如何电气连接、设备如何通信、由谁控制、实物与审定设计是否一致。M1不是简单建立项目名称和扫码列表，而是生成经过审核、可被后续五个模块复用的**项目数字工程基线**。

**M1主要成果：** 唯一Project ID；项目分类；批准拓扑版本；电气/通信/控制三类关系；设备与SN登记册；关键参数及版本；设计偏差清单；审批记录；RSP可读取的结构化项目草案及同步回执。

**边界约束：** App不代替CAD设计、保护计算和执业工程师签审；禁止AI自行生成保护定值或危险接线指令。正式As-built与最终Commissioning Baseline由M4交接后生成，M1输出仅为经审批的安装前工程基线，现场变更须保留版本。

### 1.1 上下游关系

| 来源/去向 | 输入或输出 | 管理原则 |
|---|---|---|
| 上游设计/EPC | 审定单线图、设计BOM、系统方案、合同编号、技术规范 | 来源文件记录版本、审批状态和上传者 |
| 厂家Device Master | 产品ID、型号、规格、支持协议、连接限制 | 只能引用已发布的主数据版本 |
| 厂家Topology Library | 标准拓扑模板、模板适用条件 | 模板实例化后形成项目专属拓扑 |
| M2 | 批准Topology Version、设备资产、前置条件、国家规范包引用 | 仅消费Approved版本，不能自行改M1基线 |
| M3 | 功能标签、设备映射、电气/控制边界、测试适用条件 | 测试用例依据拓扑及产品能力选择 |
| M4 | 项目及设计基线、偏差审批、资产清单 | 形成含安装实测和签署的正式移交基线 |
| M5/M6与RSP | Project ID、SN、历史版本、原始结构化资产 | 后续按同一ID追溯，不重建孤立项目 |

## 2. 项目分类：仅保留有业务意义的类型

### 2.1 分类层次与规则

**层1：电气接入层级**：LV低压 / MV中压，具体电压边界由项目国家标准及合同参数包定义，不在程序写死全球阈值。  
**层2：工程结构类型**：LV-01 / LV-02；MV-01 / MV-02 / MV-03（MV-03暂作为“中压微电网功能特化模板”，是否独立分类待批准）。  
**层3：能源配置（可多选或模板选择）**：ESS、PV+ESS、PV+ESS+Diesel、ESS+EV、PV+ESS+EV、自定义多能源。  
**层4：运行模式（多维能力）**：并网、经批准的并离网切换、独立离网；还应记录是否启用防逆流、需量控制、TOU、柴油机协调、充电负载协调等功能标签。

| 类型代码 | 中文名称 | 判断标准 | 新建方式 |
|---|---|---|---|
| LV-01 | 单台区 | 一个变压器低压侧的一个独立控制边界 | 建立1个项目，1个Transformer Zone根节点 |
| LV-02 | 多台区协同 | ≥2个台区由项目级EMS实施跨台区协调控制 | 建立1个项目＋N个台区子拓扑＋项目级协调关系 |
| MV-01 | 单中压母线 | 工程主接入/汇集边界为单中压母线 | 主拓扑以MV Bus为核心，包含下级变压器与LV子拓扑 |
| MV-02 | 多母线/多馈线 | 中压母线分段、联络或多馈线拓扑 | 建立多母线／馈线／开关及保护边界 |
| MV-03* | 中压微电网 | 项目具备已批准的中压级孤岛运行与控制能力 | 先按MV-01/02拓扑建模，再挂载Microgrid运行能力模板 |

**取消的原LV-02：** 多个台区若彼此独立运行，不设“多台区独立”类型，应分别建立多个LV-01项目，可在客户Portfolio视图汇总，但不能虚构项目级协调。  
**合并的原LV-03与LV-04：** 是否存在低压联络线/联络开关作为电气连接属性；是否统一调度作为控制属性。二者可并存，不另拆分类。  
**特别限制：** LV-02“协同”不代表台区间低压母线可以直接并联；没有审定物理连接和保护方案时，不得生成电气联络边。

### 2.2 项目分类校验

| 编号 | 校验规则 | 失败提示/处理 |
|---|---|---|
| CL-01 | LV-01必须仅有一个主Transformer Zone控制边界 | 提示拆分项目或调整类别 |
| CL-02 | LV-02台区数量≥2且存在项目级协调控制关系 | 缺少协调关系则建议分别创建LV-01 |
| CL-03 | MV项目必须至少有一个MV母线或中压接入节点 | 阻止提交审核 |
| CL-04 | MV内允许嵌套多个LV子系统 | 禁止因下级多台区而改判LV-02 |
| CL-05 | 每个PCC明确电压等级、计量及保护边界 | 缺失标为Critical |
| CL-06 | 并离网/离网能力须有批准的控制和保护设计引用 | 不满足则不可启用对应能力标签 |
| CL-07 | 同项目可同时存在Electrical、Communication、Control三种连线 | 必须明确边类型，禁止相互替代 |

## 3. 用户角色与权限

| 角色 | 创建编辑 | 扫码/参数 | 技术审核 | 发布/同步 | 说明 |
|---|---|---|---|---|---|
| EPC Project Admin | 创建项目、分配成员 | 查看 | 不替代技术审核 | 提交发布申请 | 管理项目成员及合同资料 |
| EPC Design Engineer | 编辑拓扑和设计参数 | 编辑设计计划值 | 提交自审 | 无权独立发布重大变更 | 承担设计数据责任 |
| EPC Site Engineer | 提交实物SN、现场参数 | 主操作 | 发起差异单 | 无权修改已批准设计 | 记录实物及现场条件 |
| EPC Responsible Engineer | 复核设计和差异 | 复核 | 普通工程技术批准 | 签署工程发布 | 必须具备项目所需授权 |
| LIVOLTEK Technical Reviewer | 浏览及提出修改 | 查看 | 厂家技术限制/关键变更复核 | 审批涉及厂家能力的变更 | 不代替EPC工程责任 |
| RSP Auditor | 只读 | 只读 | 审计 | 查看同步日志 | 历史资料追溯 |

**RBAC＋项目作用域**：同一工程师只能操作被授权的项目；安全关键设备参数、接线关系、保护配置引用需要附加权限和批准流程。禁止以“管理员”身份绕过审计。

## 4. M1端到端状态机

### 4.1 主流程

1. **Create Draft**：选择客户／EPC／国家，建立唯一Project ID并录入合同与设计版本。  
2. **Classify**：LV/MV→子类型→能源配置→运行模式→能力标签。  
3. **Build Topology**：从批准模板实例化或按审定文件建模电气、通信、控制三套关系。  
4. **Register Assets**：设计计划设备清单→现场扫码SN绑定→第三方设备受控登记。  
5. **Configure Parameters**：计划值与现场实测/配置值分别记录，引用产品主数据及批准配置包。  
6. **Validate & Resolve Deviations**：自动校验，建立差异单，必要时回到设计变更。  
7. **Review & Approve**：EPC责任工程师审签，厂家按触发规则参与复核。  
8. **Publish Version**：冻结Topology Version及Asset/Parameter快照；生成M2可消费的工程基线。  
9. **Sync RSP**：结构化上传并取得回执；不把M1草案误标为M4正式移交档案。

### 4.2 项目与拓扑状态

| 对象 | 状态 | 允许行为 |
|---|---|---|
| Project | Draft / Active / Suspended / Archived | Draft可改基础信息；Archived只读 |
| Topology Version | Draft → In Review → Approved → Published → Superseded | Published不可原位覆盖，修改必须新建版本 |
| Asset Binding | Planned / Scanned / Verified / Rejected / Replaced | Replaced保留旧SN和替换原因 |
| Deviation | Open → Assessed → Approved/Rejected → Implemented → Verified → Closed | 未关闭的Critical偏差阻断发布 |
| RSP Sync | Not Sent / Pending / Accepted / Rejected / Retry | 只凭Accepted回执认定RSP收录成功 |

**版本语义：** 一次修改若涉及拓扑连接、设备型号、EMS控制边界或安全参数，应产生新候选拓扑版本；仅项目联系方式变更可形成元数据审计事件，不强制升级电气版本。

## 5. 六个页面的详细交互设计

### UI-01 项目列表与创建向导

入口：My Projects → New Project。字段：客户账户、项目名称、项目国家、时区、地址／位置、EPC组织、项目责任人、合同编号、设计包编号与版本、项目用途、预期投运日期。系统生成不可编辑的Project ID。保存草案支持断网，但服务器最终ID应由服务端核发；离线临时ID同步后映射正式ID。

**前端操作**：分四页显示工程分类；字段联动展示；国家规范包按国家自动选择但允许授权复核。不得要求工程师在第一页填完所有设备参数。  
**验收**：相同客户同名项目提示疑似重复但不强行合并；合同号可选但若企业规则要求则升为必填；项目创建操作记录操作者、时间、客户端版本。

### UI-02 项目分类向导

页面按LV/MV、LV-01/LV-02或MV类型、能源构成、运行能力四步。LV-02追加台区数量、每台区名称与主变压器、项目级协调器关联；独立台区给出“建立多个LV-01”的提示。MV-03显示“待确认的功能特化模板”而非假定已冻结产品编码。

**提交输出**：`classification_code`、`energy_features[]`、`operation_modes[]`、`country_standard_profile_id`、`topology_template_suggestions[]`。

### UI-03 拓扑编辑器

三区布局：左侧节点与模板库；中央拓扑画布；右侧属性和校验结果。可创建PCC、Transformer、Transformer Zone、Bus、Feeder、Breaker/Switch、Meter/CT、PCS、Battery Rack/BMS、PV Inverter、EMS、Diesel Gen、EV Charger、Load及第三方设备节点。

**边类型必须分层显示**：Electrical（物理电气连接，含方向/电压/相数/开关状态）；Communication（物理或逻辑通信链路，协议与网关）；Control（控制指令/反馈关系，EMS分层与授权域）。可单独开关图层，导入单线图只是设计参考附件，不能当作已解析且批准的可计算拓扑。

**操作**：节点属性、连线、复制台区子图、撤销、自动布局、对照设计图、校验、版本比较。所有电气连线变更必须生成Diff。若无法自动识别实际工程接线，则要求合格工程师手动确认。

### UI-03A Icon画布、分层显示与功率方向预览（V1.2新增）

顶部模式选择Design / Commissioning / Monitoring（后两种在M1仅只读预览或跳转对应模块）；左侧设备Icon库，中央SVG拓扑画布，右侧设备/线路属性编辑栏，底部校验问题清单。设计状态下展示设备、端口、电气线、通信线、控制线以及可选的SIMULATION功率方向；调试/运行状态必须由RSP遥测绑定和权限控制，缺测时停止箭头。大项目支持台区/馈线层级导航和局部展开。

### UI-04 设备清单与扫码绑定

视图按“台区／母线／馈线→设备节点”分组，展示计划设备与实物设备两栏。厂家设备扫描二维码并解析SN、型号、产品ID；设备型号与Device Master核对，固件版本通过可信设备连接读取或标记“人工输入待核验”。第三方设备选择兼容设备库条目；不在库中则申请新增受控设备类型。

**关键交互**：扫码→显示该设备将绑定的拓扑节点→比对计划型号→确认→检测SN冲突→保存。禁止把扫描到的SN在不同活跃项目中悄悄重复占用；允许合法退库或移装时通过审计迁移流程处理。

### UI-05 关键参数配置

参数按“额定设备参数／通信参数／控制功能／安全与保护配置引用／现场测量”分组。每个参数字段保存：计划值、实际值、单位、允许区间来源、设备对象、来源方式、证据、校验状态、配置版本。安全及保护整定值原则上只引用经批准的工程文件或厂家配置包；App不得自行计算建议值后自动下发。

**交互**：从设备主数据预填只读额定参数；现场可编辑字段按角色开放；重大差异生成Deviation；支持参数快照对比和批量导入预览，确认前不写入正式版本。

### UI-06 校验中心、差异审批与发布

集中呈现Critical / Major / Minor / Warning问题，点击问题直接定位拓扑节点或参数。对每一项差异填写原设计、实际情况、原因、影响、安全风险、证据、建议处置、审批人与结果。审核页同时显示设计版本、完整设备清单、PCC/保护边界、控制关系、未关闭项与发布清单。

**发布门禁**：Critical必须为0；Major需要有经审批的处置和允许发布的依据；Minor可形成保留事项，但不得隐瞒。签署后生成不可改版本快照、文件哈希、审计轨迹、RSP同步事件。

## 6. 拓扑对象与领域模型

### 6.1 实体及关联

`Customer 1—N Project`；`Project 1—N TopologyVersion`；`TopologyVersion 1—N Node`；`TopologyVersion 1—N Edge`；`Node 0..1—N DeviceAssetBinding（按版本和时段约束）`；`DeviceAsset 1—N ParameterSet`；`TopologyVersion 1—N Deviation`；`PublishedTopologyVersion 1—N RSPArchiveReceipt`。

**树与图同时保留**：Project → MV Network / Transformer Zone → Bus/Feeder → Device用于层级浏览；Node＋Edge图用于表达多点连接与电气/通信/控制关系。不能只用树形结构表达联络开关、双向供电和多EMS控制。

### 6.2 核心数据字典（建议）

| 实体 | 主要字段（必填*） | 约束或说明 |
|---|---|---|
| Project | project_id*、name*、country*、epc_org_id*、owner_org_id、design_package_ref、state* | project_id为服务端不可变UUID或可读业务号映射 |
| ProjectClassification | project_id*、voltage_level*、structure_code*、energy_features*、operation_modes*、country_profile_id* | 代码受版本化分类主数据约束 |
| TopologyVersion | topology_version_id*、project_id*、version_no*、source_design_ref*、status*、content_hash | Published后只读 |
| TopologyNode | node_id*、topology_version_id*、node_type*、parent_node_id、name*、rated_voltage、zone_id | node_id在版本之间有stable logical id映射 |
| TopologyEdge | edge_id*、from_node_id*、to_node_id*、edge_type*、attributes、source_ref | Electrical/Communication/Control分类，不跨项目 |
| DeviceAsset | asset_id*、manufacturer*、model*、sn、product_id、firmware_version、ownership | SN未扫可Planned，但不可标记Verified |
| AssetBinding | binding_id*、asset_id*、node_id*、binding_status*、effective_from、effective_to、evidence_ref | 同SN活跃绑定冲突必须拦截 |
| ParameterSet | parameter_set_id*、asset_id*、schema_version*、planned_values、actual_values、evidence_ref、approval_ref | 存单位及参数来源，不以自由文本代替数值字段 |
| Deviation | deviation_id*、project_id*、topology_version_id*、severity*、category*、design_value、actual_value、impact、status* | 冻结后仍可作为新版本变更的追踪链 |
| Approval | approval_id*、object_type*、object_version*、reviewer*、decision*、timestamp*、signature_ref | 审批前后对象不可被静默替换 |
| SyncOutbox | event_id*、aggregate_id*、schema_version*、payload_hash*、idempotency_key*、status* | 网络重试防重；保留失败原因 |

### 6.3 不应混淆的三个编号

- **Project ID**：项目生命周期唯一，跨M1—M6不变。
- **Topology Version ID**：每次经批准的工程拓扑修订唯一；历史版本不覆盖。
- **Asset ID / SN**：Asset ID是系统内部资产主键，SN是实物设备序列号；不可假设第三方SN全局规范或永久不变。

另建议保存Template ID、Design Package ID、Customer/Owner Account ID、PCC ID及Transformer Zone ID作为可检索引用。

## 7. 类型化拓扑节点与工程规则

| 节点类型 | 必备属性 | 主要验证 |
|---|---|---|
| PCC | 编号、电压、相数、计量/保护边界、并网约束引用 | 同一PCC连接和计量映射完整 |
| Transformer | 高/低压侧、额定容量、接线组别（如适用）、序列号或编号 | 两端电压一致性及台区归属 |
| Bus/Feeder | 母线/馈线编号、电压等级、所属区段 | 不允许无设计依据跨不同电压等级直接电气连接 |
| Breaker/Tie Switch | 型号、位置、额定参数、状态反馈、保护引用 | 联络开关必须带控制与保护约束 |
| PCS/BESS/BMS | 额定功率/容量、通信标识、所属台区、控制关系 | PCS-BMS设备关联与兼容性 |
| PV inverter | 额定容量、接入母线、通信映射 | 额定电气参数及PCC关系 |
| EMS/Gateway | 控制范围、下级设备、冗余或主从属性 | 每个受控对象有清楚的控制归属 |
| Meter/CT | 测量点、CT/PT、方向、相序、通信地址 | 关键功率策略必须关联正确测量点 |
| Diesel/EV/Load | 第三方品牌、连接点、接口、设备能力 | 接口支持及计划功能关联 |

**联络关系**：`edge_type=Electrical`同时拥有`switch_ref`、`interlock_ref`、`protection_boundary_ref`等属性；“统一EMS协调”只在Control边表达，不应被系统自动转换成Electrical边。  
**容量检查**：使用设备数据和拓扑做提示性容量/电压一致性检查，不替代正式负荷流、短路或继保设计计算。


### 7.1 图形编辑引擎及架构选型（V1.2新增）

M1图形交互层推荐使用 **AntV X6**（开源MIT；正式采用前由法务复核依赖与许可），React Flow作为对照PoC。ELK.js可选作布局组件，其许可与分发义务单独核查。禁止直接以X6画布JSON作为唯一工程事实源：所有画布对象必须映射到厂商无关的`LIVOLTEK Topology Schema`。

| 逻辑层 | 职责 | 建议实现 |
|---|---|---|
| 图形视图（Topology Canvas） | SVG设备Icon、端口、线路、标签、动态箭头、分层展开 | X6适配器；React Flow保留可替换性 |
| 工程模型（Domain Graph） | Project、Zone、Bus、Node、Port、Edge、资产、版本 | 自定义JSON Schema及服务端实体 |
| 校验引擎（Validation） | 端口兼容、电压、设备归属、保护/联络边界 | 版本化规则；设计审核门禁 |
| 遥测适配器（Telemetry） | 按测点关联实时P、有功方向、质量及时间戳 | RSP/EMS读接口；WebSocket可选 |
| 视图状态（Presentation） | 编辑、调试、运行模式、缩放、图层、动画 | 与工程模型分离，允许个人视图偏好 |

开源组件只解决绘图和交互，不提供经验证的电力工程设计、保护定值或现场安全控制能力。PoC必须分别验证LV-01、LV-02、MV-02的节点、端口、图层、性能和移动端触屏操作。

### 7.2 标准设备Icon库（Icon Library）

每类设备采用具有语义的SVG矢量图标，统一定义`icon_type`、`device_type`、`node_type`、`symbol_version`、`display_label`及标准端口布局。图标应能在深浅色、移动端和离线环境下显示；用图形形状与文字同时表示状态，不仅依赖颜色。

| Icon类型 | 默认端口 | 主要可见标签 | 数据来源 |
|---|---|---|---|
| Grid / PCC | AC入口/出口、计量、状态 | PCC、kV、电网状态 | 项目设计、计量遥测 |
| MV/LV Transformer | MV、LV | 容量、变比、编号 | 设计/资产库 |
| MV/LV Busbar & Feeder | 母线连接、支路 | 编号、电压、馈线 | 设计拓扑 |
| Breaker / ATS / STS / Tie | IN、OUT、DI/DO | 开合状态、额定参数 | 设备主数据、遥测 |
| PV Inverter | DC、AC、COM | 型号、SN、kW | 设备资产/遥测 |
| PCS & BESS | AC、DC、COM/BMS | 功率、容量、SOC | 设备资产/遥测 |
| Battery Rack / BMS | DC、COM | 电池包、SOC、告警 | 主数据/遥测 |
| EMS / Gateway | ETH/RS485、CTRL | 控制域、状态 | 控制关系/遥测 |
| Meter / CT / PT | 电气测量点、COM | 安装点、正方向 | 测量点配置 |
| Diesel Generator | AC、CTRL/COM | 额定功率、状态 | 第三方设备配置 |
| EV Charger / Load | AC、COM | 功率、设备编号 | 设计及测量数据 |

图标变更仅更新显示资源版本，不得改变设备ID、SN或已经批准的工程拓扑；图标缺失应回退到通用类型符号且保持节点可编辑。

### 7.3 端口与线路数据模型（Electrical / Communication / Control）

**线路不允许只凭屏幕坐标自由连接。** 每个节点至少定义`node_id`、`node_type`、`zone_id`、`ports[]`。每个端口定义`port_id`、`port_type`、`medium`（AC/DC/ETH/RS485/IO等）、`nominal_voltage`、`phase`、`direction_capability`、`rating`、`terminal_ref`与`manufacturer_rule_ref`。

三类边必须分离：

- `ELECTRICAL`：实际的功率线路，记录`from_port/to_port`、AC/DC、电压级、额定容量、开关/联络引用、保护边界及设计文件引用。
- `COMMUNICATION`：RS485、Modbus TCP、CAN、Ethernet等通信连接，记录协议、链路和地址，不暗示能量传递。
- `CONTROL`：EMS到PCS/BMS/柴油机/充电桩的控制权限、优先级及策略引用，不暗示物理电气并联。

每条边赋予稳定`edge_id`。线路在画布上的拐点、曲线、箭头样式保存在`view_layout`，不写入工程电气连接主数据。对于有开关的连接，必须建开关对象及状态；不能以线路颜色代替保护设计。

### 7.4 三种工作模式与权限边界

| 模式 | 数据与画面 | 允许操作 | 严禁推断 |
|---|---|---|---|
| Design Mode（M1） | 静态工程拓扑，支持编辑与设计场景示例 | 拖拽Icon、连接端口、配置、版本审批 | 示例箭头不能标为真实现场功率 |
| Commissioning Mode（M3） | 发布的工程拓扑＋授权调试遥测 | 只读拓扑、查看状态与测试步骤；变更走M1差异审批 | 可视化不能替代调试安全门禁 |
| Monitoring Mode（RSP） | 已移交As-built版本＋实时遥测 | 只读监控、历史回放、故障定位 | 数据离线时不能显示假定能量流向 |

M1负责**拓扑视图组件与数据契约**，不在M1实现M3的调试动作或RSP的时序数据库。未经批准的Design草案不得进入生产Monitoring；调试中的现场拓扑差异需重新审批并产生新版本。

### 7.5 能量流向的定义、方向与功率守恒

动态图仅表示**有功功率P（kW）的方向**，术语优先使用“功率流向”；累计“能量流量”应以kWh及明确统计时窗单独显示。每个可观测电气分支建立`measurement_binding`，包含`edge_id`、`meter_or_device_id`、`point_id`、`reference_direction`、`unit`、`sign_rule`、`source_system`、`sample_time`、`quality`、`max_age_seconds`。

- 从测点标定正方向读取`P_signed_kW`；`P>deadband`沿参考方向，`P<-deadband`逆向，绝对值≤阈值显示无流动；**不使用未经标定的厂家正负号直接驱动箭头**。
- 电网PCC：约定正值为**电网流入项目（Import）**，负值为**项目馈向电网（Export）**；设备供电/吸收方向通过各设备测点映射统一转换。
- BESS：约定正值为**放电向交流母线输出**，负值为**充电从母线吸收**；SOC仅作设备状态，不决定瞬时功率方向。
- 无有效测量的支路显示“Unknown / Not Measured”，不凭相邻节点和线路画面假定其流向；若利用平衡估算，则明确显示“Estimated”、公式、误差范围并默认不用于工程验收。
- 母线功率平衡仅用于诊断提示：`ΣP_in-ΣP_out≈损耗＋测量误差`。当多点时钟不同步或CT/PT方向错误，显示校验告警而非静默纠正数据。

示例工况（非现场数据）：PV=120kW、Grid Import=20kW、BESS Charge=40kW、Load=100kW，功率平衡为120+20=40+100。系统不得直接将此示例保存成现场遥测。

### 7.6 箭头动画与数据质量门禁

| 遥测状态 | 显示规则 | 动画 |
|---|---|---|
| Valid且新鲜，绝对功率超过deadband | 线路带方向箭头、kW、数据时间 | 可启用，节奏有上限，不用动画速度代表经校准的kW |
| Valid且接近0kW | 显示0kW/Standby | 停止 |
| Stale、Offline、Invalid、Uncertain | 灰色或虚线、标注数据不可用及时间 | 必须停止 |
| 未安装测点 | 显示Not Measured，不生成箭头 | 禁止 |
| Estimated（受控可选） | 显式估算标识及依据，与实测不同样式 | 默认停止 |
| Breaker/Open且回路已隔离 | 按已确认开关状态显示断开 | 停止；状态不确定则显示Unknown |

数据质量判定须配置`max_age_seconds`，包括通信质量、采样时刻、服务器接收时刻和设备在线状态；延迟、跳变与失序事件应按时间戳丢弃或标记。动画可以关闭以适应无障碍、低功耗和性能场景。交互不得通过动画触发任何设备操作。

### 7.7 LV-02与MV分层显示

- LV-01：默认显示PCC→变压器→LV母线→PCS/PV/Load/EMS；点击设备Icon查看参数、SN、监控状态及设计/运行数值来源。
- LV-02：首页显示N个Transformer Zone卡片，每台区呈现聚合功率与数据完整性；进入台区展开其LV-01子图；项目级EMS用Control边而非Electrical边连接台区。
- MV-01/MV-02：默认MV母线与馈线视图，变压器节点可下钻进入LV子系统；多馈线必须保存开关、PCC和保护边界，避免为排版而改变电气结构。
- 同一拓扑支持Electrical、Communication、Control三层显隐；隐藏只影响显示，不改变工程主数据。控制关系可以交叉台区，跨电气边界的功率流则必须基于实际线路及测量。

### 7.8 拓扑编辑与遥测性能、安全要求

1. 对LV-02、MV使用分层加载、局部布局和画布虚拟化，避免一次性展示上千节点动画；建议在目标Windows浏览器和移动设备上实测。
2. 节点点击弹层必须显示数据源、采样时间和质量。设计额定kW与实时kW不能使用同一无标识字段。
3. 只读模式禁止拖拽影响已批准拓扑；仅允许缩放、筛选、查看历史。
4. 数据源连接失败不应阻断查看静态拓扑；离线应清晰显示“监控不可用”。
5. 拓扑版本、Icon库版本、测量点映射规则版本均需记录，且可对历史事件进行同版本回放。
6. 设计模式的模拟数据必须明确显示`SIMULATION`，不允许与RSP遥测和保修证据混用。


## 8. 模板库与兼容性规则引擎

### 8.1 模板选择

模板必须具备`template_id/version/applicable_country_or_standard/voltage_level/structure_code/energy_features/min_required_nodes/required_protection_refs/required_control_edges`。实例化模板时生成项目专属节点ID，而非共享可变的模板节点。允许从标准LV-01复制多个台区到LV-02，但项目级EMS和跨台区控制关系须单独定义。

### 8.2 校验规则分级

| 编号 | 规则 | 等级 | 处理 |
|---|---|---|---|
| VAL-01 | 结构分类与主拓扑不一致 | Critical | 阻断审批 |
| VAL-02 | 关键PCC／变压器／母线缺失 | Critical | 阻断审批 |
| VAL-03 | SN在同一活跃安装资产关系重复 | Critical | 阻断确认 |
| VAL-04 | PCS/BMS/电池型号组合不在已批准兼容清单 | Critical或Major（按厂家规则） | 技术审核 |
| VAL-05 | 电气连接跨电压级且无适用变压器或转换设备 | Critical | 阻断发布 |
| VAL-06 | LV-02缺项目级协调控制器/控制关系 | Critical | 补齐或改成多个LV-01 |
| VAL-07 | 相同通信总线地址冲突 | Major | 纠正并复核 |
| VAL-08 | 计量点未定义方向/CT倍率 | Major | 禁止相关控制功能启用 |
| VAL-09 | 计划设备与实际型号不符 | Major | 形成设计差异审批 |
| VAL-10 | 部分非关键标签缺失 | Minor | 警告和待办 |
| VAL-11 | 原始设计图审批版本失效或缺失 | Critical | 不允许正式发布 |
| VAL-12 | 并离网标签缺批准控制/保护设计 | Critical | 不允许启用该功能 |

**规则可配置**：`rule_id/version/severity/condition/affected_objects/message/remediation/approval_override_policy`，每次校验保存规则版本和结果。关键安全规则不可由普通项目管理员覆盖。

## 9. 设计差异与变更管理

差异来源：型号替代、SN与计划不符、设备数量调整、现场电气连接偏离、通信网络变化、EMS控制归属变化、参数改变、现场条件不满足设计等。

**标准处理路径**：Detect → Log Deviation → Classify Safety/Functional/Commercial Impact → Assign Approver → Approve/Reject → Implement → Re-validate → Close。涉及合同变更或第三方设计责任的，App只记录审批证据，不替代合同变更流程。

**审批记录**至少包含：对照设计值/现场值、照片/文件、影响台区及设备、是否影响M2 SOP/M3 SAT、整改或接受理由、批准文件编号与签署时间。任何已发布版本的修改都要以新版本申请实现，禁止直接覆盖历史设计。

## 10. RSP同步与集成设计

### 10.1 数据归属（建议，待与RSP现有接口对表）

| 数据 | 事实源 | M1读写方式 |
|---|---|---|
| 厂家设备主数据/兼容性 | LIVOLTEK主数据服务 | 下载已发布只读版本 |
| 项目草案与拓扑 | Project Engineer工作区 | 创建/审核/版本发布 |
| 设备实物绑定及现场证据 | Project Engineer操作记录 | 提交有签名/操作审计的事件 |
| 设备运行遥测 | Monitoring/RSP | M1仅按权限读取，不复制全量时序数据 |
| RSP Case/RMA | RSP | M1不创建故障工单 |
| 项目正式竣工服务档案 | RSP在M4验收后归档 | M1只提供工程基线及同步预登记 |

### 10.2 建议API（逻辑契约，非已冻结接口）

| API | 主要字段 | 核心行为 |
|---|---|---|
| POST /projects | client_request_id、name、country、epc_org | 返回Project ID；幂等创建 |
| GET /projects/{id} | id | 按权限取项目及当前版本引用 |
| POST /projects/{id}/topology-versions | source_version、classification、nodes、edges | 创建Draft新版本 |
| POST /projects/{id}/assets/bind | node_id、asset_id、SN、model、proof | 校验SN、机型及节点 |
| PUT /projects/{id}/parameter-sets/{id} | schema_version、values、evidence | 乐观锁，拒绝覆盖已发布版本 |
| POST /projects/{id}/validate | version_id、ruleset_version | 输出逐条Issue与严重度 |
| POST /projects/{id}/deviations | changed_fields、reason、evidence | 形成偏差审批链 |
| POST /projects/{id}/topologies/{version}/submit-review | snapshot_hash、reviewers | 冻结待审快照 |
| POST /projects/{id}/topologies/{version}/approve | decision、signature、approved_hash | 审核后发布或拒绝 |
| POST /integrations/rsp/project-baselines | event_id、project_id、topology_version、assets、parameters、refs | 推送工程基线，返回回执 |

### 10.3 集成事件及错误处理

事件：`ProjectCreated`、`ClassificationUpdated`、`TopologyVersionSubmitted`、`TopologyApproved`、`AssetBound`、`DeviationOpened`、`DeviationClosed`、`BaselinePublished`、`RSPBaselineAccepted/Rejected`。

- 每个事件具有`event_id`、`project_id`、`object_version`、`schema_version`、`occurred_at`、`actor_id`、`idempotency_key`、`payload_hash`。
- 弱网先存本地加密操作队列；服务端按幂等键识别重复；冲突不做静默last-write-wins，必须显示差异比较。
- RSP拒收时保存错误码、字段路径和重试记录；修正后重推同版本或按规则生成新版本。
- 只有`Accepted`意味着RSP已收到该工程基线；不等同M4竣工验收完成。


### 10.4 新增图形视图与遥测接口（V1.2建议契约）

| API / 通道 | 关键字段 | 责任边界 |
|---|---|---|
| GET /topology-symbols?version= | symbol_id、svg_ref、port_templates、version | Icon库版本化只读分发 |
| GET /projects/{id}/topologies/{version}/graph | nodes、ports、electrical_edges、communication_edges、control_edges | 返回规范化工程模型，不返回仅限某前端库的私有JSON |
| PUT /projects/{id}/topologies/{version}/view-layout | node_positions、edge_waypoints、layer_visibility、etag | 保存视图布局；不得改变工程连接 |
| POST /projects/{id}/topologies/{version}/validate-connections | proposed_from_port、proposed_to_port、edge_type | 连接前校验端口、电压及授权规则 |
| GET /projects/{id}/measurement-bindings | edge_id、point_id、reference_direction、sign_rule、ruleset_version | 获取已批准测点绑定与符号约定 |
| GET /projects/{id}/power-snapshot | readings、quality、sample_time、source_id | 受权读取当前有功功率快照；不作为历史事实源 |
| WS /projects/{id}/power-stream | point_id、p_kw、quality、timestamp、sequence | 可选实时订阅；断线后降级为不可用 |

典型测点示例（数据结构仅为建议）：

```json
{
  "project_id": "PRJ-EXAMPLE",
  "topology_version": "3",
  "edge_id": "EDGE-PCC-LVBUS",
  "point_id": "METER-PCC.P_ACTIVE",
  "reference_direction": "GRID_TO_LV_BUS",
  "signed_power_kw": -25.3,
  "quality": "VALID",
  "sample_time_utc": "2026-11-06T02:00:00Z",
  "max_age_seconds": 15,
  "source": "RSP"
}
```

平台应从`reference_direction`和正负号计算显示方向，禁止直接采用画布几何线条的箭头方向作为实际功率定义。所有示例接口路径在研发对接前需与RSP真实API核对。


## 11. 非功能、安全与审计要求

**离线**：可离线读取最近一次批准模板、查看工程档案、扫码采集与草案编辑；首次服务器项目号、远端SN全局冲突、审批发布及RSP回执需联网完成。离线识别为“本地待同步”，不得假冒已批准。  
**性能建议值（待验证）**：典型LV-01包含≤100节点、≤300边时常规编辑响应目标≤1秒；LV-02 ≤1000节点/≤3000边时支持按台区分层加载，避免一次渲染全部连线；上传/同步以批量与断点续传方式执行。  
**审计**：记录谁在何时以何版本修改何字段，保存旧值与新值、批准对象哈希、位置（依法可收集时）、设备标识和操作原因。  
**安全**：TLS通信、端侧加密缓存、基于项目的最小权限、敏感资料权限和保留策略；不允许通过图片OCR自动写入安全关键整定值而不经人工核验。  
**国际化**：多语言、国家标准包、时区、UTC审计时间、SI单位与本地展示单位转换，保留原始单位与数值。  
**可靠性**：SN扫码重试、网络断点恢复、重复消息去重和版本冲突提示。

## 12. M1验收用例与退出门禁

| 用例 | 具体操作 | 预期结果 |
|---|---|---|
| M1-U01 | 创建单台区光储LV-01项目 | 生成唯一Project ID、1个台区、对应拓扑草案 |
| M1-U02 | 创建2台区统一EMS项目 | 归LV-02；各台区有独立子图，存在项目级控制关系 |
| M1-U03 | 创建2个互不协调台区 | 系统提示分别建立LV-01，不错误识别成LV-02 |
| M1-U04 | LV-02设置“有联络开关” | 保存Electrical边及开关属性，不新增类别 |
| M1-U05 | LV-02仅统一监控，无协调调度 | 要求重新确认业务定义；不以监控等同协调控制 |
| M1-U06 | MV-02项目含多个下级LV子图 | 支持MV层级及下级变压器/台区建模 |
| M1-U07 | 扫描已绑定在另一活跃项目的SN | 阻断或发起合法资产迁移，不悄悄重复绑定 |
| M1-U08 | 现场设备型号与设计BOM不符 | 自动创建Major/Critical差异并触发审批 |
| M1-U09 | 缺PCC或保护边界 | Critical问题阻断Topology发布 |
| M1-U10 | 修改已发布EMS控制关系 | 必须新建版本，原Published版本保持不变 |
| M1-U11 | 离线采集后两人编辑同节点 | 显示冲突与对比，不静默覆盖 |
| M1-U12 | 模拟RSP收录失败再重试 | 不产生重复项目；失败记录可追踪，成功后Received/Accepted |
| M1-U13 | 选择并离网但无批准保护设计 | 阻断相关能力发布并显示缺失文件 |
| M1-U14 | 审核后输出M2输入包 | 包含拓扑版本、节点边、资产、关键参数、国家规则和审批证据 |

**M1完成定义（Definition of Done）**：上述UAT全部通过；LV-01与LV-02代表性项目可演示；MV模型至少通过可视化建模及数据校验；G1审批门禁有效；M2可读取不可变发布快照；RSP能接收工程基线并返回可靠回执；高风险安全/设计参数不可越权更改。


### 12.1 V1.2新增图形与功率流向验收用例

| 用例 | 操作 | 预期结果 |
|---|---|---|
| M1-U15 | 在LV-01画布拖拽PV、PCS、BESS、变压器和EMS的SVG Icon | 节点有独立ID和标准端口，保存后可重开 |
| M1-U16 | 用电气端口连接AC母线和设备 | 建立Electrical Edge，记录端口/电压/额定参数 |
| M1-U17 | 尝试直接把不同电压等级端口接入同一线路 | 显示Critical，阻断连接发布 |
| M1-U18 | 画EMS至PCS的控制关系 | 形成Control Edge，绝不生成电气联络 |
| M1-U19 | 为同一项目切换电气/通信/控制图层 | 显示变化但图模型和批准哈希不变 |
| M1-U20 | 设计模式载入模拟PV/Grid/BESS/Load功率 | 必须显著标记SIMULATION，不误写RSP实时值 |
| M1-U21 | 给PCC绑定有效正负功率遥测 | 正值指向项目、负值指向电网；显示来源/时间 |
| M1-U22 | 给BESS绑定放电/充电遥测 | 放电箭头指向交流母线，充电反向 |
| M1-U23 | 将功率设置为接近零或遥测过期 | 箭头停动，数据显示0或Unavailable |
| M1-U24 | 未绑定有效测点但存在电气连接 | 显示Not Measured，不凭拓扑推断流向 |
| M1-U25 | 将LV-02展开成多个台区 | 台区汇总与子图可切换，协同Control边保留 |
| M1-U26 | 在MV母线下钻至低压台区 | 层级清晰、设备SN与版本不丢失 |
| M1-U27 | 将X6画布导出再导入标准Schema | 节点ID、端口、边和资产一致；不依赖X6内部ID |
| M1-U28 | 模拟RSP断线/乱序/无效遥测 | 无效数据不显示实时箭头，不影响静态拓扑 |
| M1-U29 | 修改已批准节点连线并保存 | 必须生成待审新版本，旧批准版本不变 |
| M1-U30 | 关闭动画或在移动端查看大型拓扑 | 文字与状态仍可读，按层级加载、交互可用 |

新增退出门禁：图形视图必须与工程模型相互解耦；实时显示须可靠判断测量质量；未完成测点方向标定的支路不得上线功率动画。


## 13. 开发拆分建议（仅M1）

| 工作包 | 内容 | 输出及测试 |
|---|---|---|
| M1-A | 分类主数据、Project创建、权限 | Project API、分类向导、U01—U03 |
| M1-B | X6/React Flow PoC、设备SVG Icon、端口与三类连接、LV-01模板 | 标准Schema、U15—U19及U27 |
| M1-C | LV-02、MV层级与联络/控制关系、下钻及自动布局 | 子拓扑、项目级EMS、U05—U06、U25—U26 |
| M1-D | Device Master引用、扫码SN、参数集 | Asset Register、U07—U08 |
| M1-E | 规则引擎、偏差、技术审批、版本冻结 | G1审批与U09—U10、U13 |
| M1-F | 离线同步、RSP事件及基线接口 | 冲突处理、U11—U12、U14 |
| M1-G | RSP测点映射、功率方向可视化、质量门禁 | U20—U24、U28、U30；M3/RSP复用的只读组件 |

建议每个工作包按“设计评审→开发→自动测试→EPC实操验收→偏差修正→冻结”执行；阶段验收通过后再进入下一包。单独保留完整的`sample_project_lv01`、`sample_project_lv02`、`sample_project_mv02`测试数据集。

## 14. 需要在M1评审会上定案的事项

1. MV-03采用正式项目类型还是MV-01/02下的“中压微电网功能标签”（本设计推荐后者作为工程模型，保留UI可选模板）。
2. 国家电压等级和电网接入规范包的维护责任与版本发布流程。
3. EPC签署人、厂家技术复核人的授权条件，以及哪些差异需厂家共同审批。
4. Project ID由RSP共享主数据服务还是Project Engineer服务端产生，如何确保全链路唯一。
5. 第三方设备数据模型与兼容认证范围；不兼容设备如何申请评估。
6. 现有RSP接口能否接收M1工程基线，后续M4正式竣工基线与其如何版本关联。
7. 保护参数/并离网设置的工程审签及责任边界。
8. 首选X6、对照React Flow的PoC准入标准、第三方依赖许可及离线发布方式。
9. RSP现有实时功率测点、方向约定、采样周期和质量代码映射责任。
10. M1拓扑组件如何嵌入M3、RSP，以及项目工程基线与已验收As-built版本的切换机制。

**V1.2补充结论：** “图形绘制≠电气工程模型≠实时测量”。M1以标准Schema保存可追溯工程拓扑，X6仅承担可替换视图；功率箭头仅来自有效、已标定方向的遥测。Design Mode可演示模拟数据但必须标识；真正实时运行数据由M3/RSP按各自权限提供。

**本文件结论：** M1应首先冻结“Project＋TopologyVersion＋Node/Edge＋AssetBinding＋ParameterSet＋Deviation＋Approval”的统一数据模型和G1发布门禁。LV-01与LV-02共享台区子拓扑；中压项目可嵌套台区；独立台区不强行组成一个项目。M1经发布的工程基线将成为M2的唯一合法安装任务输入，并在M4经实测验收后沉淀为RSP正式售后原始档案。
