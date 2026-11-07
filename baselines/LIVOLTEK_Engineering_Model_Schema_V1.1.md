# LIVOLTEK Engineering Model Schema V1.1

## 修订总原则：完整相关系统建模与合同责任分离

**产品定位（修订后的权威定义）：** LIVOLTEK Project Engineer 是主设备厂家提供给EPC工程师的系统感知型安装调试辅助、现场故障排查及远程技术支持协同工具。它不取代EPC专业电气设计、施工管理、法定检验或合同验收工具。

**系统建模覆盖范围：** 凡是会实质影响LIVOLTEK设备的安装、控制、保护、并离网协同、自测、系统功能或故障定位的设备和接口，均须纳入相关系统模型；无论其品牌、供货商或是否由LIVOLTEK生产。包括第三方PV逆变器、柴油机、ATS/STS、变压器、电表、保护开关、充电桩及相关负载/电网边界。无需复制整座工厂或EPC的全部工程设计。

**模型深度独立于品牌：** L1为具备完整参数/遥测/控制资料的设备级模型；L2为支持关键指令、反馈、通信映射及接口验证的集成设备模型；L3为仅建模边界、额定参数、运行状态和关键测量的简化外部系统。第三方设备可以达到L1，LIVOLTEK设备也可因资料不全暂处待核验状态。

**权限与责任分离：** `manufacturer`描述设备品牌；`responsibility_owner`描述工程/合同责任；`control_capabilities`描述技术可用性；`authorization`单独约束谁在何种条件下有权读写、控制和执行测试。**可建模≠可远程控制≠厂家承担质保。**

**数据与安全：** 第三方设备接入须有协议/寄存器来源和兼容性验证；无有效数据不得模拟真实故障结论或显示实时能量流动；无授权不得写第三方参数、触发保护或远程启动设备。未知字段和未批准SOP允许形成待评审草案，不得自动发布生产作业。


## V1.1新增：面向系统级自测与故障排查的数据能力

### 1. 设备范围与三级模型

所有与系统运行、控制、保护、通信、自测、故障排查有实质关联的设备均进入模型，无论LIVOLTEK或第三方。`modeling_level`为L1_FULL、L2_INTERFACE、L3_BOUNDARY。L1必须能够表达完整可验证接口，L2表达关键命令/反馈，L3只需表达系统边界。建模不代表厂家承担第三方质量责任。

### 2. V1.1新增Schema字段

- `device_models[].integration_role`、`interface_specifications`、`source_quality`及`document_refs`。
- `device_assets[].modeling_level`、`responsibility_owner`、`equipment_origin`、`telemetry_capabilities`、`control_capabilities`、`test_capabilities`、`diagnostic_capabilities`。
- `device_assets[].authorization`（读取、写入、测试权限；默认拒绝，须由有效审批授予）。
- `nodes[].relationship_reason`及`edges[].integration_dependency`（物理连接与功能依赖分离）。
- `interface_bindings[]`：设备接口与点位、信号意义、数据来源、质量和操作授权的显式绑定。
- `test_scopes[]`：M3可验证设备级、接口级、系统级功能以及自动/辅助/见证执行方式。
- `diagnostic_paths[]`：M5沿EMS→通信→PCS/BMS→电气边界→外部条件排查的路径，含必须测点和数据缺失处理。

### 3. 示例系统边界与验证

随包`lv01-mixed-vendors.engineering-model.json`在既有LV-01基础上增加一台第三方PV逆变器和接口定义，保持所有数据处于DEMO/DRAFT。`validate_demo.py`会验证旧样例的向后兼容及混合品牌模型；同时对第三方控制授权、测试目标、测点引用和兼容性实施语义验证。示例只用于软件开发，不代表某真实设备的已认证接口或真实接线。

### 4. SOP数据契约修订

M2规则应声明`scope_type`、`source_document_ref`、`task_owner`、`execution_authority`。厂商设备SOP/批准接口SOP/EPC资料核对分别管理；第三方未确认资料只能生成BLOCKED/DRAFT_ONLY，不得生成第三方设备内部操作步骤。

### 5. RSP及版本

`system_context_baseline`是M1-M6的统一快照；每个接口测点要有时间戳、质量和符号约定。M3/M5对遥测不可用必须给出UNKNOWN/NOT_TESTABLE，不得假定安全通过。控制需查阅设备能力与实际权限两层，不因接口模型存在而具备控制权。


---

## 既有详细设计（未冲突条款继续适用）

**性质：M1/M2 Demo结构化工程模型及接口建议稿；非施工设计批准文件。**

## 交付文件
- `engineering-model.schema.json` — M1工程模型JSON Schema (Draft 2020-12)
- `lv01-demo.engineering-model.json` — LV-01样板（模拟数据、全部DRAFT）
- `sop-rule-pack.schema.json` — M2 SOP规则包的数据校验
- `lv01-demo.sop-rules.json` — 示例SOP触发条件（DRAFT，禁止生产使用）
- `validate_demo.py` — 可运行的结构+跨对象校验

## 1. 文件目的与范围

本文件是LIVOLTEK Project Engineer M1（项目建立与配置）与M2（引导式安装）之间的结构化数据契约。其用途是从工程事实数据生成可审查的工作包，而不是直接依据单线图图片推导施工指令。
适用M1的LV-01单台区、LV-02多台区协调以及MV-01单母线、MV-02多母线/多馈线、MV-03中压微网（后者分类边界尚待评审）。多个独立台区分别作为LV-01项目；只有统一协调控制才用LV-02。
V1.0提供JSON Schema、LV-01示例、SOP规则示例、跨对象语义校验和M1→M2接口建议。暂不连接真实设备，所有样例均不构成批准施工资料。

## 2. 核心原则

①模型优先，图纸辅助：SLD/图形画布只是同一工程数据的呈现或录入方式。②事实源分离：Device Model是厂家设备主数据；Device Asset是项目实例；工程节点可以没有SN。③关系分离：Electrical、Communication、Control三类边不能混用。④版本不可变：发布后冻结结构化快照，变更产生新版本。⑤渐进式补全：资料不足时可生成草案SOP，但不可发布危险作业。⑥实时遥测独立于静态工程设计，缺测/过期不得显示真实功率流动画。⑦符合性仅是程序校验，电气设计和现场安全必须由具备资质人员审核。

## 3. 工程数据层次

L1 Project：国家、EPC、LV/MV、结构分类、能源组成与运行方式。
L2 Electrical Structure：PCC、Transformer Zone、MV/LV Bus、Feeder、Breaker等非SN对象。
L3 Device Model & Asset：产品型号、规格、厂家主数据版本、实例SN/固件/安装位置。
L4 Port & Connection：连接必须落到端口级；端口含AC/DC、以太网、RS485、CAN、逻辑控制等域。
L5 Configuration：计划值、现场实际值、批准值分列，记录来源、单位、风险等级和文档依据。
L6 Engineering Rules & Review：规则包、工程评审、偏差、审批及发布。
横切属性为Topology Baseline、数据来源、审计、视图布局、遥测映射。

## 4. 主要实体及字段

Project: project_id/name/country_code/voltage_level/structure_code/energy_features/operation_modes/epc_org_id。
Baseline: baseline_id/version/status/source_design_refs/country_profile_ref/device_master_version/rule_pack_version/approved_by/published_at/content_hash。
Node: node_id/logical_id/parent_node_id/node_type/zone_id/device_asset_id/icon_key。
Port: port_id/node_id/domain/role/approved_spec_ref。
Edge: edge_id/edge_type/from_port_id/to_port_id/design_ref/review_status。
Device Model: model_id/manufacturer/model_name/master_data_version/rated_parameters/sop_catalog_refs。
Device Asset: asset_id/model_id/serial_number/sn_status/firmware_version/lifecycle_status。
Parameter: scope/owner_id/name/planned/actual/approved/criticality/reference_doc。
Review/Deviation: target_id/decision/status/reviewer/approval_ref。
Telemetry binding: target_id/measurement/source_system/point_ref/positive_direction/max_age_seconds。

## 5. 唯一标识与版本规则

Project ID是生命周期主键，严禁以项目名称替代。node_id是单个拓扑版本中的节点主键，logical_id用于跨版本追踪同一工程概念。Device Asset ID用于实例身份，SN可在计划阶段为空；扫码后须核验不可重复绑定。Edge ID独立标识每一条关系。
Published基线须含审批和内容哈希；不得原位覆盖。图形布局的坐标/颜色/折线存在view_layout，不能影响电气语义。结构化工程变更形成候选新基线并标记受影响M2步骤。M2生成记录应锁定baseline_id、device_master_version、rule_pack_version以及对应SOP模板版本。

## 6. 电气、通信与控制关系

ELECTRICAL边只连接兼容电气端口，如AC-AC或DC-DC；连接前须检查电压等级、相数、端口能力、保护和项目设计依据。COMMUNICATION边引用实际物理/网络端口和协议；不代表可传输电能。CONTROL边表示EMS对设备的逻辑控制关系，可跨台区但不能推断存在电气联络。
一个Breaker、ATS、STS必须建为具有状态/额定参数的设备或开关节点，不能只画彩色线条。对多馈线、中压与跨变压器拓扑需记录电气边界和PCC位置。所有上述校验属于对已编码规则的检查，不能视为继保整定、潮流计算或施工许可。

## 7. 渐进式信息完整度与生成门槛

Level A：设备型号明确，可产生设备级SOP草案。Level B：端口和连接已建模，可产生连接级SOP草案。Level C：有设计文件、保护与现场参数，可产生待审批的系统SOP草案。Level D：已满足资质、文档、审批、安全门禁及SOP Published状态，才允许生产任务发布。
每条任务必须返回readiness=READY/DRAFT_ONLY/BLOCKED、missing_inputs、blocking_rules、source_sop_ref与risk_level。遇到未知型号、缺少电缆规格、未确认保护设置，不能编造数值，必须生成待补资料。

## 8. M1→M2生成机制

M1发布不可变工程快照→后端JSON Schema检查→跨实体语义规则校验→M2解析设备及拓扑特征→匹配已发布SOP→依赖图排序→冲突/覆盖率检查→出具草案或正式安装工作包。
M2默认工作包：WP01施工准备、WP02机械安装、WP03电气安装、WP04通信安装、WP05配置准备、WP06上电前安全检查、WP07受控上电交接。M2与M3边界：M2只完成安装就绪及授权交接，M3负责调试、自动自测和正式SAT。
工作包应该保存生成时所用的基线版本，后续变更以diff标记受影响步骤，不覆盖历史执行和签名记录。

## 9. 动态能量流与图形画布

建议使用AntV X6作为第一候选画布，图形节点、SVG Icon、端口及路线坐标仅为视图适配数据。域模型在数据库/JSON Schema中保存；不把X6 JSON作为唯一事实源。
Design模式允许带明显“SIMULATION”标志的示例功率；Commissioning与Monitoring模式仅使用具有质量GOOD、时间戳不超过max_age_seconds且设备有效在线的遥测测点决定箭头方向。没有足够分支功率测量时该线路停止动画并标注Unavailable，不通过拓扑猜测能量流向。负功率符号需根据positive_direction解释，绝不把额定功率当实时功率。

## 10. 数据存储与接口建议

关系型建议表：projects、topology_versions、nodes、ports、edges、device_models、device_assets、parameters、rule_packs、review_records、deviations、telemetry_bindings、sop_plans。主数据、版本和执行记录应分表；Demo可采用SQLite。
建议API（拟议接口，非既有系统确认）：POST /projects、POST /projects/{id}/baselines、PUT /baselines/{id}/draft、POST /baselines/{id}/validate、POST /baselines/{id}/submit-review、POST /baselines/{id}/publish、GET /baselines/{id}/snapshot、POST /installation/plans/preview、POST /installation/plans/publish、GET /projects/{id}/diff。
发布API必须进行幂等、防重复、RBAC、审计；跨服务同步采用事件+回执。RSP接口仍需与现有平台产品接口对表。

## 11. Schema校验以外的业务校验

JSON Schema只能检查字段类型、枚举及必填约束；以下须自定义语义校验：
SEM-01 Node/Port/Edge引用均存在；SEM-02所有ID在各自范围唯一；SEM-03边两侧端口必须兼容，且属于合法类型；SEM-04Asset引用存在Model，SN核验后唯一；SEM-05 parent/zone无非法循环且同项目；SEM-06 LV-01/02、MV分类与层级结构一致；SEM-07 PMS/EMS控制关系不被误画成电气边；SEM-08发布必须有对应审批及来源文件；SEM-09高风险参数必须有批准值；SEM-10图形与工程模型节点ID可相互映射；SEM-11所有引用的已发布SOP在版本内可用；SEM-12动态流向测点有效、方向定义明确。
错误级别INFO/WARNING/BLOCKER/SAFETY_CRITICAL，危险作业遇未批准或缺资料必须BLOCKED。

## 12. 初始SOP规则包实例

随附lv01-demo.sop-rules.json仅用于说明设备存在或连接存在如何触发WP草案。示例规则全部DRAFT，不得用于正式施工。生产规则必须引用经过技术/安全审查的正式厂家SOP文档及版本，关联设备型号、国家合规包和适用条件。规则支持依赖、证据要求、风险等级、优先级与撤回状态。冲突应提交工程审核，不允许AI自动裁决危险步骤。

## 13. 工程评审与差异闭环

对象变更状态：Draft→Under Review→Approved→Published；Rejected返回修订。工程师可在Icon、端口、线路、参数、SOP任务上逐项评论、提交证据和审批。审查必须保存原值、新值、原因、审批人、来源文件及时间。
样板项目初始设置为DRAFT：SN待扫码、断路器参数/电缆规格待核定、文档未批准，因此应允许渲染和草案计划，不允许发布真实安装执行计划。

## 14. Demo测试及验收清单

UAT-01加载LV-01示例并通过JSON结构校验；UAT-02拖放BESS及EMS Icon能保持稳定节点ID；UAT-03电气、通信、控制边分别显示；UAT-04不兼容端口被拦截；UAT-05节点选择可查看产品型号与设备实例；UAT-06未录SN可创建草案但不得错误标记已验证；UAT-07缺电缆规格产生缺失项；UAT-08现有BESS触发设备安装SOP草案；UAT-09通信边触发通信检查草案；UAT-10未批准SOP阻止正式计划发布；UAT-11变更拓扑时重算受影响SOP；UAT-12视图坐标变化不改变工程语义；UAT-13设计模拟流向显示SIMULATION；UAT-14遥测过期箭头停止；UAT-15历史发布版本不被覆盖；UAT-16跨对象悬空引用校验失败；UAT-17 LV-02各台区复用LV-01流程并增加协调检查；UAT-18 M2生成计划保留所有来源版本ID。

## 15. 决策待评审事项

（1）MV-03是独立类别还是运行能力标签；（2）设备主数据编码、合法SN格式及唯一性范围；（3）国家profile与工程电气规范包维护主体；（4）拓扑关键参数的审批矩阵；（5）各SOP正式文档来源、适用型号和发布日期；（6）第三方设备的端口/协议能力数据可信度；（7）RSP实际数据接口/权限模型；（8）计量方向和实际功率测点标准。以上不影响本版Demo以模拟数据启动。
