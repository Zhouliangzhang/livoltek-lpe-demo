# iEMS现场工作台系统设计文件

英文产品名 iEMS Site Engineering Workbench
文件编号 IEMS-SDD-001　版本 V1.1　日期 2026年11月9日

状态：V1.1 迭代评审稿。统一产品命名，并纳入2026年11月9日确认的分步拓扑与公共总览方案。保留V1.0及原始依据，不改变历史记录标识。配套需求文件：IEMS-PRD-001 V1.1。适用读者：Web、后端、iEMS、驱动、RSP、安全、数据和测试团队。本文给出完整目标系统及模块契约，区分现有Demo、拟实现设计与待厂家确认内容。

## 1 架构目标与约束

工作台是iEMS的工程功能，不是独立的施工管理系统。统一工程对象和版本贯穿建模、调试、交接与售后。工程师可在现场浏览器访问iEMS的本地服务，也可在离线环境编制草稿；云端RSP承担档案、工单及协同，不接管本地实时保护。

系统必须保证三项不变量：每个有物理影响的动作具有可信授权与明确退出策略；任何结果都能追溯到当时范围、配置和证据；模拟记录不能成为现场批准或验收事实。模块之间使用同一标识和引用链，不复制另一套设备表。

本设计采用模块化服务边界，不要求首期拆成多个微服务。React、TypeScript与AntV X6继续作为Web实现基础；FastAPI可承担工作台API和流程编排。SQLite用于本地单节点事务存储时必须验证实际硬件、并发和断电恢复。iEMS控制执行器的语言和实时实现由控制软件团队选定，不把Python Web请求循环作为实时控制闭环。

## 2 部署及组件设计

### 2.1 三层分工

| 层级 | 组件 | 权威数据与职责 |
| --- | --- | --- |
| 浏览器 | M1至M4页面、只读拓扑、证据查看、操作确认 | 展示和输入，不持有最终执行权、不直接访问设备寄存器 |
| iEMS本地 | 工作台API、工程库、身份授权、规则服务、配置执行器、测试执行器、驱动、证据库、同步器 | 本站现场任务状态及采集事实，离线可持久化，受控调度设备 |
| 厂家平台 | 认证及租户、主数据／驱动／测试包发布、档案服务、工单、协同和质量接口 | 受控产品资料、平台接收版本、服务派单及外部回执 |

浏览器经认证HTTPS调用本地API；本地执行器经内部受控接口调用驱动；驱动使用经批准的设备协议。RSP与本地通过连接器交换授权数据、任务及回执。设备现场总线和外部平台之间不形成浏览器可任意透传的控制隧道。

离线编辑器复用工程Schema与校验，不加载真实执行适配器。模拟环境使用独立执行适配器、数据库命名空间和合成时钟，不持有现场设备凭据。现场执行器在服务端禁止回退为模拟实现。

### 2.2 模块服务

| 服务边界 | 输入 | 输出及约束 |
| --- | --- | --- |
| ProjectContext | 项目、环境、主体与控制器身份 | 授权工作上下文，所有请求的边界 |
| EngineeringModel | 对象与参数变更、预期版本 | 工程修订、差异和依赖影响；M1主写入方 |
| ProductCatalog | 产品标识、型号、固件 | 受控主数据、端口和能力；普通工程用户只读 |
| RuleAndBasis | 规则包、项目范围、资料版本 | 格式／依赖／适用性／执行门槛结果和定位 |
| ConfigurationExecutor | 批准基线、任务授权及目标版本 | 逐参数写入、读回、失败和退出证据 |
| TestExecutor | 会话、测试包、设备能力和动作授权 | 按依赖执行的Run及原始观测；供M2和M4共用 |
| EvidenceService | 日志、曲线、照片、文件和来源 | 内容地址、完整性、访问控制及证据索引 |
| HandoverService | 一致的模型、报告、证据及限制 | 共同基线、EPC包、厂家包和各自版本 |
| FieldService | RSP／本地工单、基线和故障观测 | 假设、方案、复测、报告和质量协同 |
| RspConnector | 授权数据、平台协议和出站队列 | 入库／工单／协同回执、错误和同步状态 |

### 2.3 主事实归属

M1工程服务管理计划和批准配置；iEMS采集管理实际读回及运行事实；厂家发布服务管理产品适用性；授权主体管理项目批准与SAT签署；RSP管理平台接收和派单状态。没有任何一方通过复制JSON自动取得另一方的事实确认权。

RSP和本地冲突时比较版本及共同祖先。现场新读回是新增观测，不自动改为新批准配置。云端收到新包是接收事实，不自动激活设备策略。

## 3 标识与工程数据模型

### 3.1 标识及范围

所有业务记录至少包含tenant_id、project_id、environment、record_id、schema_version、created_at、created_by。现场执行另含site_id、controller_binding_id、control_domain_id、scope_id。主键采用不可复用标识，展示编号可以修改而不改变引用。

device_node_id表示系统逻辑位置；asset_instance_id表示物理实例；serial_number是实例属性。更换设备生成新实例和ReplacementRecord，保留旧实例在历史基线中的引用。controller_binding_id绑定站点与可信控制器身份，换机应撤销旧绑定，不能只改SN字符串。

### 3.2 工程层次

| 层次 | 实体 | 关键字段及关系 |
| --- | --- | --- |
| L1 | Project、Site、ControlDomain、PCC | 地区、时区、EPC、LV/MV、运行方式、能源组成、边界及图纸 |
| L2 | StructureNode、Circuit | PCC、变压器区、母线、汇流、馈线、开关；parent_id、circuit_id、来源 |
| L3 | DeviceModelVersion、AssetInstance、ReplacementRecord | 厂家、型号版本、SN、出厂／实际固件、位置、所属回路、服务接口 |
| L4 | Port、ElectricalConnection、CommunicationPath、ControlRelation、MeasurementRelation | 两端端口、域、用途、总线／网关、控制所有者、实物端子依据 |
| L5 | ParameterDefinition、ParameterValueSet、MeterMapping、OperatingPolicy | 适用条件、单位、计划／批准／实际值、时间质量、依据和风险 |
| 横切 | RulePack、BasisDocument、Issue、Review、AuditEvent、ViewLayout、TelemetryMapping | 版本、来源、责任、审计、布局和遥测映射；不增加独立L6页面 |

MeasurementRelation显式表达CT二次侧、电表输入和PCC覆盖关系，不将所有信号连线泛称RS485通信。非SN结构不强制生成资产。电气、通信、计量和逻辑控制边有独立类型及校验，不从图形颜色推断语义。

### 3.3 端口及连接约束

Port保存port_id、owner_id、logical_name、domain、role、physical_terminal_ref、rated_constraints、multiplicity和basis_refs。域包括AC、DC、PE、Ethernet、RS485、CAN、计量信号及逻辑控制。未知端口保存待确认状态，不自动补AC或RS485。

连接保存from_port_id、to_port_id、circuit_id或bus_id、类型、依据、确认状态和环境。后端校验端点存在、域相容、结构／回路归属及端口多连接能力。仅在兼容且可用端口数为1时自动选择；后端仍复核。允许模板声明的联络和环网，不用单一“禁止环路”覆盖所有电气结构。

### 3.4 参数值与依据

ParameterValueSet以target_id、parameter_key和环境为范围，保存四类值：planned、approved、observed及simulation_fixture。每类值带unit、source、timestamp、quality和basis_ref；approved还含approval_id及scope_hash；observed另保存raw_value、raw_unit、transform_version和source_timestamp。估算值使用单独source_kind，不与observed有效测量混合。

通信参数按bus_id公共设置与endpoint私有设置分开。RS485地址在总线／网关寻址域内判重，IP在声明网络范围判重；不得跨独立总线误报同地址。公共参数改变产生全部关联设备的影响清单。

BasisDocument记录发布者、文件版本、哈希、适用型号／固件／驱动范围、状态、有效期及核验记录。文件上传或填一个编号仅代表提交；适用性核验和现场采用批准是不同记录。撤销依据使后续依赖动作受阻，但不修改旧证据的原始评价。

### 3.5 业务实体

| 实体 | 必需字段 | 关系 |
| --- | --- | --- |
| EngineeringRevision | revision、parent_revision、model_hash、diff、actor | 保存工程草稿，不自动批准 |
| ConfigBaseline | scope、dependency_ids、model_hash、catalog／driver／rule_versions、approval_refs | 引用确定修订及批准范围 |
| ConfigTask／ParameterResult | baseline_id、request_id、before、ack、readback、status、exit_status | 一个任务含逐设备逐参数结果 |
| TestSession／Run | baseline_id、session_id、run_id、step_id、scope_hash、lease_id、test_package_version | Session冻结依据，Run保存一次执行 |
| Criterion | metric、unit、operator、threshold、window、sample_rule、basis_ref、applicability | 缺参数即待确认，不采用隐含阈值 |
| Observation／Evidence | source_kind、object_id、run_id、时间质量、原始与规范值、hash | 原始观测和派生评价分开 |
| SATReport／Signature | coverage、run_refs、limitations、report_hash、signer、authority | 签署绑定具体范围及版本 |
| HandoverBaseline／DeliveryPackage | baseline_id、manifest、audience、payload_hash、supersedes_id | 两种包共享同一语义基线 |
| PlatformReceipt／EPCReceipt | package_id、accepted_hash、receiver、status、remote_revision | 分别证明各自接收事实 |
| ServiceCase／Hypothesis | external_ticket_key、baseline_refs、symptom、hypotheses、risk_scope | 保留原报障和根因置信程度 |
| RemedyPlan／RetestLink | change_scope、approval、before_after、run_refs、exit_evidence | M4复用M2执行能力 |
| ServiceReport／ServiceBaseline | case_id、evidence_refs、open_items、closure、supersedes_id | 服务后基线不冒充初始交付 |

## 4 M1实现设计

### 4.1 模型生成与只读拓扑

步骤02形成项目与边界上下文，步骤03维护结构归属，步骤04维护设备，步骤05保存电气连接，步骤06保存通信与控制关系，步骤07至09补充参数与策略。图是这些数据的派生视图。当前草案可含已进入前端模型但尚未保存的修改，必须显示dirty状态；局部编辑表单尚未提交的输入不进入拓扑。冻结视图只由封存快照派生。

页面职责：ElectricalStructure呈现结构清单和StructureTree；ElectricalConnections呈现SingleLineTopology与连接编辑；NetworkRelations将通信控制图置于关系清单前；M1Start的公共区域挂载TopologyOverview，不依赖当前步骤是否已进入连接编辑。总览默认收起，版本选择与图层选择是查看操作，不能更改模型。

当前草案构造由currentTopology合并基础连接与本环境electrical_drafts、network_drafts。已有连接按base_edge_id替换两端端口，新关系按独立ID加入。其它环境修订不进入当前图。电气图由electricalView检查端口和对象存在性、AC/DC域一致性后构造节点及连接；不合法引用保留问题提示，不绘制伪造连线。

结构树只使用parent_node_id，支持多根、上级缺失与循环提示。电气分组为主配电、光伏、储能和负载，按有效电气邻接布局；光伏／储能共享上级引用时分为可读支路图。节点布局和显示分组不能修改归属或端口关系。当前Demo以设备类型、名称、用途辅助分组；生产规则应优先采用受控功能分类及回路数据，歧义须明确待核实。PCC与CT的电气表示严格沿用来源模型，不能以视觉优化代替工程纠错。

冻结列表通过GET /api/projects/{project}/config-baselines?environment={environment}取得，选定版本通过GET /api/projects/{project}/config-baselines/{id}取得。frozenTopology仅映射snapshot.structure、ports、connections、models及project字段，不用当前草案补齐缺失对象。显示环境、控制域、范围类型、source_revision、created和content_hash；哈希不是批准签名。当前记录中的状态为FROZEN_DRAFT，冻结仍不代表批准、下发或现场生效。

异步读取采用取消标志，项目、环境或版本变化后丢弃旧响应。加载期间不显示旧图冒充新版本；读取失败显示错误。当前环境无冻结记录时给出步骤10入口说明，不伪造基线。部分范围只显示实际封存对象和依赖，不能将未包含对象判为被删除。若范围内本应有端口却缺失，按待补说明。

X6画布设置interacting=false、panning=false、mousewheel.enabled=false，端口不可发起连接。仅提供放大、缩小、适应按钮；滚轮用于页面滚动。画布缩放及布局不改变语义模型和配置哈希。通信路径与逻辑控制分别呈现，同一图中按node_id去重iEMS；图形可见不表示在线、通信已验证或控制权已取得。

### 4.2 主数据和扫码

扫码解析器限制编码长度、格式和允许的产品标识，拒绝执行二维码中的脚本或任意跳转。产品ID由厂家目录解析，响应具版本和完整性验证。离线包检查签发、适用范围和有效性。扫码不能授予现场写权限，可信目录也不能证明设备当前固件。

第三方模板与LIVOLTEK主数据使用相同适用性结构，但提供方不同。自定义模板默认DRAFT，审核后新版本发布；已有基线继续引用旧版本，直到明确变更。

### 4.3 校验层次

第一层校验Schema、枚举和引用完整性；第二层校验工程关系、寻址域、单位、策略依赖和约束；第三层校验厂家依据及批准适用性；第四层在执行前核验实时身份、权限和工况。前端可预览前两层，最终决策由后端及iEMS执行。

RuleResult统一包含rule_id、rule_version、severity、category、object_ids、parameter_keys、reason、required_evidence、owner_role、blocked_actions和locate_target。合并键由规则、根因、依据缺项及适用组组成；合并显示不能丢失逐对象实例。

### 4.4 冻结和配置任务

冻结事务检查expected_revision并生成确定范围依赖闭包；共同依赖包括PCC、电表、网关、总线、驱动和策略，不能仅按勾选设备计算。保存不可变快照后生成scope_hash和semantic_model_hash。

配置执行顺序为接收任务、执行前再核验、保存前值、按批准驱动计划写入、记录指令确认、独立读回、按单位和批准容差比较、处理退出、封存结果。设备支持暂存／激活时使用该能力，不假定全站原子提交。不能回退的设备明确显示不支持，不虚构恢复成功。

策略参数写入可能直接影响出力。若不能保持未激活状态，应按控制动作级别授权；无法具备条件的激活动作留待M2受控执行。M1-12只创建或更新M2入口引用，UI为“继续调试”，不生成内部接收单。

## 5 通用执行与门槛设计

### 5.1 命令契约

每个命令包含command_id、idempotency_key、project_id、environment、controller_binding_id、scope_hash、baseline_hash、authorization_id、lease_id、expected_device_state_version、expires_at、driver_version、payload和exit_plan_ref。真实命令必须在iEMS本地验签或核验可信会话，并检查租约代次。

命令请求先持久化为PREPARED，再由执行器领取。若设备不支持命令去重且提交后回执丢失，状态进入OUTCOME_UNKNOWN；通过实际读回和批准的对账方法恢复，不能承诺对所有设备实现网络层“恰好一次”。重复浏览器请求只返回原任务，不直接触发第二次物理下发。

### 5.2 控制权与门槛

共享PCC控制域使用带有效期和单调递增fencing_token的租约。每次功率动作同时检查租约、指令所有者、本地策略及上层EMS冲突。旧租约持有者恢复连接后不能执行新动作。不同控制域只有在无共享依赖且驱动支持时才允许并行。

REAL控制放行至少满足：身份可信、当前范围一致、批准及资料适用、控制租约有效、必要前置结果有效、现场工况成立、退出策略可用、证据可持久化。任何一项未知均不放行依赖动作。

SIMULATION采用相同流程依赖，但判据来自有版本的模拟夹具。厂家待确认不阻断独立演练，也不会改变现场依据状态。OFFLINE不实例化命令执行器。只读诊断按其必要条件独立计算，不能套用控制门槛一刀切阻断。

### 5.3 执行状态及结果分离

| 维度 | 状态示例 | 转移规则 |
| --- | --- | --- |
| 执行 | CREATED、BLOCKED、AWAITING_AUTH、READY、RUNNING、EXITING、ENDED、ABORTED、OUTCOME_UNKNOWN | READY前门槛齐备；RUNNING停止先EXITING，退出无法确认保留未知 |
| 结果 | NOT_TESTED、PASS、FAIL、INCONCLUSIVE、CONDITION_NOT_MET、NOT_APPLICABLE | PASS须必要观测和退出确认；不适用有范围理由 |
| 依据 | DRAFT、PENDING、VERIFIED、REVOKED、EXPIRED | 无有效依据不能产生正式现场通过 |
| 环境 | OFFLINE、SIMULATION、REAL | 不通过状态改名转换证据环境 |
| 退出 | NOT_REQUIRED、PENDING、CONFIRMED、FAILED、UNKNOWN | 退出失败不能以主测试通过掩盖 |

界面可显示“模拟满足判据”，底层仍保存environment=SIMULATION与result=PASS，现场统计必须按环境和来源过滤。测试组结果按必需实例逐项聚合，不取平均功率或完成百分比代替通过。

## 6 M2执行和计量设计

### 6.1 测试依赖

默认主路径为01→02→03→04→05→06→07→08→09→10→11→12→13→14。浏览后续页不等于执行放行。实际TestPackage以有向无环图描述依赖，允许不同设备独立只读任务限流并行，不允许未经批准跳过共享PCC或控制权依赖。

每个TestDefinition包含适用条件、对象选择、输入点、前置证据、动作序列、判据、采样时序、停止条件、退出动作和证据要求。实例化时冻结型号、固件、驱动和模板版本；同型号不同适用固件不得错误合组。

M2-06只校验实际读回与M1批准基线。必要修正调用M1变更服务；临时测试设置另存TemporaryOverride，包含到期、撤销和验证方法。M2-12检查所有覆盖值和临时权限已按方案撤销，不能仅清空前端表单。

### 6.2 计量语义

内部约定P_grid正值为购电、负值为馈网；P_bess正值为放电、负值为充电；P_pv及P_load使用正的发电／消耗量。示例平衡为P_grid≈P_load−P_pv−P_bess，损耗、覆盖边界和采样偏差必须单独说明。该式用于一致性检查和模拟，不代替有效PCC独立实测。

MeterMapping保存PCC覆盖、电表端口、寄存器／字段、数据类型、字节序、原单位、一次／二次侧、仪表倍率、驱动变换、内部单位、符号、时间来源、质量规则和依据。比例变换只在声明层执行一次。设备给一次侧功率时不再次乘CT/PT。

样本保存source_time、received_time、monotonic_sequence、clock_quality、raw_value、normalized_value和quality_flags。无源时间时使用采集时间并标明限制；时钟倒退、数据陈旧、缺测、冻结或质量无效不能计入连续窗口。独立方向参照必须注明仪表和来源，禁止用同源数据自证。

### 6.3 功率控制与能力

储能充电与放电分别计算有效边界：取批准项目限制、设备有效反馈、BMS允许、SOC和其他适用约束中的更严格边界。某必需输入未知则该方向能力为UNKNOWN；不可因铭牌125kW计入可用125kW。能力快照附时效和依据，命令前重新读取，不只在步骤05读取一次。

每次控制记录requested_setpoint、accepted_setpoint、command_ack、actual_power、quality、limitation_reason及restoration_result。指令收到、接受、参数生效和实际功率响应是不同事实。无光或SOC条件不足作为CONDITION_NOT_MET，不能自动标设备故障或PASS。

动态测试分别保存扰动起点定义、可观测起点、采样间隔、峰值、目标带、稳定判据和退出。响应时间仅在时间质量和工况满足时计算。所有功率容差、斜率、超时、观察时长来自Criterion，不写死在页面。

### 6.4 降级及恢复状态机

| 状态 | 进入条件 | 动作和退出条件 |
| --- | --- | --- |
| NORMAL | 必要反馈、能力及控制权有效 | 批准策略运行；异常转DEGRADED并锁存事件 |
| DEGRADED | 电表无效、拒令、能力或权限丢失 | 只执行批准降级；未知输出保留未知；两窗清零 |
| QUALIFYING | 所有必要测量及可验证执行能力恢复 | 保持降级，连续积累Tq；任一失效退回DEGRADED |
| LIMITED_RESTORE | Tq满足且具备恢复权限 | 按批准斜率恢复闭环，告警仍保持；连续积累Ts |
| RESTORED | Ts满足、PCC有效测量和响应均满足 | 解除运行告警，保留事件、复发次数及全链证据 |
| MANUAL_REVIEW | 达到批准复发升级条件或退出不可验证 | 保持限制并请求协同；不无限自动重试 |

QUALIFYING或LIMITED_RESTORE内再次缺测、拒令、越界、能力不明或控制权丢失，两个计时窗均归零。重启恢复时读取未闭合事件，重新取得资格，不沿用无法证明连续的时间。单调时钟用于本次持续时间，UTC用于跨系统索引；重启前后的连续性必须重新建立。

PCC反馈丢失时曲线断开或标为无效，估算轨道单独显示。“零馈无法保证”与“已测得馈网越限”分开记录。失联设备本地后备仅在适用能力包声明且有验证方法时使用，不以失联等于已降零。设备本地保护不可被测试覆盖。

### 6.5 SAT报告和复核

CoverageMatrix关联SAT条款、适用范围、所需步骤、实际Run和判据版本。签署前检查覆盖缺口、旧基线、未退出、无效证据及偏差权限。签署绑定report_hash、scope_hash、签署主体与权限依据；新证据或新配置产生新版本，不修改原签署内容。

人工替代证据必须是规程允许的明确方法并注明批准范围。上传照片不能自动改变自动检测失败；厂家后续发布新判据只能触发可追溯复核或复测，不能重写历史为通过。

## 7 M3包与双路径接收设计

共同HandoverBaseline封存模型、配置任务、实际读回、M2会话和报告、完整证据目录、限制事项及版本。输入测试结果必须属于相同项目、环境、身份和对应配置范围。后续变更使旧包成为历史适用版本，不删除或覆盖。

### 7.1 包结构

| 文件或对象 | EPC包 | 厂家包 |
| --- | --- | --- |
| manifest.json | 文件名、类型、长度、哈希、包和共同基线ID | 同左，另含Schema、平台协议和裁剪配置版本 |
| technical-summary.pdf | 技术摘要、范围、限制及使用说明 | 可选阅读附件 |
| equipment.csv及参数表 | 人可读清单，含来源和状态 | 可附，结构化模型为主体 |
| engineering-model.json | 交付范围配置和端口关系 | 完整授权系统上下文及遥测映射 |
| sat-report及evidence目录 | 报告、条款覆盖、曲线、日志及授权附件 | 相同依据的授权子集和可解析证据索引 |
| followup.json | 稳定待办ID、责任、限制、复测要求 | 同时包含平台校验及技术建档待办 |

规范化JSON后计算semantic_model_hash，文件按实际字节计算SHA-256；包的payload_hash覆盖清单及受控元数据。哈希只证明内容一致，不证明现场真实性。签署或接收必须另有可信身份与权限记录。

导出采用字段允许清单及分类规则，不能只按password等关键词过滤。敏感附件先检查授权范围，照片位置等非必要信息去除或限制。凭据不写入工程模型，模型只保存凭据引用。所有附件必须有可持久化对象ID，不交付本地磁盘临时路径。

### 7.2 状态机

EPC路径：DRAFT → READY → RELEASED → RECEIVED；另含RETURNED、SUPERSEDED。下载只记DOWNLOAD事件，不改变为RECEIVED。接收绑定发布版本、接受范围和限制。

厂家路径：WAIT_AUTH → QUEUED → UPLOADING → RECEIVED → VALIDATING → INGESTED_PENDING_REVIEW → SERVICE_BASELINE_CONFIRMED；部分失败进入PARTIAL或NEEDS_INFORMATION。只有校验齐全、回执可验且技术确认完成才达到正式服务基线状态。

实时连接和远程控制权限为独立维度。档案可用时遥测仍可离线；远程控制未授权不阻止档案接收。两个接收方保存自己的latest_received_package_id，不设置无范围的全局“已交接最新版本”。

### 7.3 同步事务

生成包和出站Outbox任务在一个本地事务内完成。上传内容使用幂等键tenant／site／package／hash；服务器重复提交同包返回原任务，键相同而内容不同返回冲突。附件分块或逐件重试，最终manifest全部校验后提交入库。超时先查任务，不能重建站点。

平台回执必须核对目标站点、包ID、accepted_hash、远端版本、状态、未接收对象、时间和身份依据。收到HTTP 200但缺少有效回执只能保持传输层成功。冲突转人工差异处理，禁止自动最后写入覆盖。

## 8 RSP与M4服务设计

### 8.1 工单接入

TicketEnvelope包括provider、tenant_id、external_ticket_id、ticket_revision、event_id、site_id、controller_id、environment、device_refs、baseline_ref、symptom_original、occurred_at及time_zone、priority、assignment、authorization_refs、attachment_manifest和trace_id。

连接器先认证来源并校验签名／会话、重放窗口和租户，再通过Inbox去重。唯一关联键为provider＋tenant＋external_ticket_id；新ticket_revision追加事件而非建立新服务单。乱序事件暂存并查询缺失版本，旧事件不能覆盖新指派。

本地核对站点及资产映射。指定基线存在则引用；缺失时标为待同步并保留原引用，可开展独立允许的诊断，不能擅选另一项目。受理保存ServiceCase和来源映射后再返回受理回执。平台送达、工程师接单、开始诊断及完成各为独立状态。

### 8.2 诊断上下文和因果记录

ServiceContext冻结原M3交付基线、最近已核验服务后基线、后续批准变更、受理时工程修订和故障实际观测。四者分列；没有保存差异不代表现场没有改动。iEMS自身故障时允许独立设备日志及人工测量证据，注明来源和时序不确定性。

Hypothesis包含category、affected_objects、causal_path、support_evidence、counter_evidence、missing_evidence、proposed_test、expected_result、actual_result及confidence。诊断决策先共同依赖后单台，以事实逐步排除。规则建议不是质量责任自动判定，工程师确认须记录依据。

根因分类覆盖产品、配置、安装、第三方、运行条件、多因素和未确认。BMS禁止充电等保护行为须继续查触发条件，不能直接归责用户或电池。

### 8.3 修正和复测

RemedyPlan冻结前值、拟改值、目标实例、风险、适用文件、批准范围、退出／回退及复测计划。现场动作前重新检查基线、现场身份和授权。换机生成新资产实例及影响分析；固件升级按厂家专用包处理，不能视为普通参数写入。

复测调用TestExecutor，context_type=SERVICE，关联case_id、remedy_id和新的配置范围。复用M2判据定义与驱动，不复用历史运行结果。通信修正至少复核身份、数据质量和受影响计量；计量／策略变化可能扩展至联动、动态和降级测试。完整范围由依赖规则决定。

处置失败、复测失败或观察复发追加新Run和Issue，保留旧假设与修正记录。退出状态未知时不得关闭服务单。临时措施记录期限和限制，不能自动成为长期服务基线。

### 8.4 待办与服务关闭

Issue状态为OPEN、IN_PROGRESS、SUBMITTED、VERIFIED、RETEST_REQUIRED、RESOLVED或REOPENED；另记录mandatory、owner_role、required_evidence_types及approved_exception_ref。模拟处理只形成模拟解决记录，不改变厂家正式依据状态。

关单谓词为：本范围必需事项均已满足，必要复测有效，正常配置和退出已确认，观察符合批准方案，基线未失效，关单者有权。若根因未确认且仍是必需调查项，保持打开。非必需质量改进可转关联事项，记录批准与承接关系，不让原必需事项凭文字消失。

ServiceReport不可覆盖，包含原工单、症状、根因及不确定性、方案、批准、执行、复测、未完成项和来源。关单前后各保存快照。真实关闭回传RSP还需平台确认，界面区分本地已关闭与平台待回执。模拟关闭永不调用生产平台关闭接口。

### 8.5 服务后基线

通过批准、执行和复测的实际变更形成新ServiceBaseline，关联原M3基线和服务单，再按接收方范围生成更新包。RSP已接收服务后版本不代表EPC已接收更新文件。保留原始交付基线、最新确认基线和待确认变更三种查询入口。

## 9 接口契约

以下为目标逻辑接口示例，用于团队联调；不是声明现有RSP已提供这些路径。生产协议、认证和字段需平台团队确认。现有Demo接口可通过适配层演进，不要求按示例机械改名。

### 9.1 公共约定

API路径使用/api/v1。请求上下文包含项目及环境，身份来自认证令牌而非body.role。修改请求含expected_revision或If-Match；异步写入及测试返回202和task_id。幂等键绑定认证主体、项目、环境、动作和内容哈希；同键不同内容返回409。

错误体包含code、message、reason、object_ids、parameter_keys、owner_role、blocked_action、required_evidence、locate_target、retryable和trace_id。401／403表示身份／权限，409表示版本／幂等冲突，422表示数据／范围错误，503表示实际适配器不可用。不能以200加一个模糊失败字段作为所有错误。

| 接口域 | 示例操作 | 关键输入与输出 |
| --- | --- | --- |
| 工程 | GET／PATCH projects/{id}/revisions | revision、差异、校验、预期版本；返回新修订 |
| 主数据 | POST catalog/resolve-product | 产品标识及固件；返回受控型号版本和来源 |
| 规则 | POST projects/{id}/validate | scope和action；返回该动作必需阻断和定位 |
| 基线 | POST projects/{id}/baselines | revision、scope、approval_refs；返回不可变baseline_id |
| 配置 | POST baselines/{id}/config-tasks | 授权、目标版本、幂等键；返回task_id及状态 |
| 会话 | POST projects/{id}/test-sessions | M1引用、测试范围、规程及授权；返回session_id |
| 执行 | POST sessions/{id}/runs | step、scope、授权、幂等键；返回run_id |
| 停止 | POST runs/{id}/stop | reason、主体及任务版本；返回受控退出请求状态 |
| 查询 | GET tasks/{id}及events | 当前状态、last_event_seq；断线续传事件 |
| 交接 | POST handovers及packages | 共同基线、报告、audience；返回包与manifest |
| 接收 | POST packages/{id}/receipts | 可信接收身份、hash、范围及限制 |
| 服务 | POST service-cases／hypotheses／remedies | 工单、上下文、假设、方案与授权 |
| 复测 | POST service-cases/{id}/retests | remedy_id及受影响范围；返回M2执行run_id |
| 报告 | POST service-cases/{id}/reports及close | 证据版本及预期状态；返回不可变报告与关闭状态 |

### 9.2 RSP适配契约

连接器至少支持能力／Schema版本协商、站点身份核对、包提交、任务查询、附件补传、回执获取、已接收基线检索、工单拉取或事件接收、接单／进度回执、协同附件及报告同步。平台不支持某能力时返回明确“不支持”，不能在本地伪造平台完成。

每条平台消息包含event_id、aggregate_id、revision、occurred_at、environment、tenant_id、payload_hash和correlation_id。接收后先持久化Inbox，再执行业务；处理结果持久化后发布回执。消息重试采用有上限的退避和死信待办，不无限重试真实控制命令。

回执最小字段包括provider、remote_site_id、external_task_id、package_id、baseline_id、accepted_hash、remote_revision、status、validation_errors及received_at。工单与包都必须校验相同租户、项目和环境；模拟目标为隔离服务，不接收生产凭据。

## 10 证据存储与版本完整性

工程修订、任务、命令日志、审批、状态转换和Outbox／Inbox用事务库保存。大曲线和附件写入本地内容寻址文件区或对象存储，以hash、长度和类型索引。先写临时对象、校验并原子发布，再在事务中提交引用，避免数据库显示成功而文件尚未落盘。

本地SQLite启用适合硬件的事务及日志策略，验证掉电、磁盘满和并发写入；数据库与附件一致备份。生产RSP数据库和对象存储由平台团队选型，不能共享本地SQLite文件作为跨站点云数据库。

原始证据追加保存，纠正通过新记录说明，不修改原时间和值。派生结果记录算法／判据版本及输入证据ID。审计日志含主体、权限依据、动作、前后版本、原因、关联任务及时间；哈希链可帮助发现改动，但需要访问控制与外部保全才能增强防篡改能力，不能将单纯哈希宣称为不可抵赖签名。

对外证据下载校验访问范围和短期授权，不暴露磁盘路径；导出清单包含全部文件的长度、哈希和来源。保留期、删除审批、法律保留及跨区存储策略为部署配置，未确定前不能自动清理关键未闭合服务证据。

## 11 变更影响和一致性

影响图由对象引用、通信路径、计量映射、控制域、参数依赖和测试依赖构成。变更时从变化键出发计算传递影响，记录为什么某结果失效。旧Run和签署不改动，新增ValidityAssessment指向其适用性变化。

| 变化 | 最小复核范围 | 可能扩展 |
| --- | --- | --- |
| 设备位置文字或图布局 | 文件显示及资料一致性 | 不自动使控制证据失效；若回路归属变化另判 |
| SN／型号／固件／驱动 | 身份、适用性和参数读回 | 对应控制、系统联动及退出能力 |
| 总线参数／地址／端口 | 关联总线设备通信、身份和数据质量 | PCC链变化影响全部依赖零馈测试 |
| CT/PT／符号／单位／PCC范围 | 计量及独立参照 | 零馈联动、动态、降级及观察 |
| BMS或储能限制 | 充放电能力和受影响方向 | 共享功率分配、联动和恢复 |
| 策略／权限／控制所有者 | 控制权、配置和相关动作 | 整个控制域的动态、降级和观察 |

M2进行中变更M1产生新修订；会话继续保留旧快照，禁止自动切到新版本执行。必要时结束原运行、生成新会话或批准的新批次。M4处理后新基线同样不覆盖原M3包。最新记录必须按范围、环境和有效性选择，不能只按时间选最后一条。

## 12 安全与权限设计

授权采用角色与项目／控制域／动作范围组合。EPC编制、项目批准、厂家适用性审核、现场执行、SAT签署、EPC接收、平台建档和服务关闭分别定义能力。角色名称本身不代表具备合同权限；真实身份和授权关系由可信身份服务提供。

现场登录不自动取得控制租约，工单派发不自动授权写入，厂家建档不自动开远程控制。高影响动作需要绑定对象、参数、范围、版本和有效期的授权；新增对象或修改基线后旧授权失效或需重新确认。

TLS、证书／凭据生命周期、会话过期、撤销和最小权限由正式接入实现。离线现场允许在已批准时限和范围内使用可核验本地权限；到期或无法验证必要授权时拒绝新的高影响动作。浏览器本地存储不保存设备口令，日志与导出不泄露凭据。

附件限制类型和大小，校验内容类型及恶意内容，文件名不作为路径。二维码和厂家文档属于外部输入，不能执行其中命令。跨租户／项目／环境访问在API、存储索引和连接器三层校验，不仅靠前端筛选。

## 13 故障与恢复设计

| 故障 | 确定行为 | 恢复条件 |
| --- | --- | --- |
| 浏览器关闭或网络断开 | 本地执行器继续批准范围或按退出策略处理；页面不宣称停止 | 重新认证并按原task／run查询，不自动重发 |
| 云端离线 | 本地获准作业继续，资料及回执队列保留 | 同步去重、版本核验及冲突处理 |
| iEMS重启 | 停止新动作，恢复日志并标明未知命令；重新核对实态 | 重新取得控制权、身份、条件及退出／恢复资格 |
| 存储不足或日志写入失败 | 不发出无法留痕的新测试动作，进入批准退出 | 存储恢复且日志连续性明确；缺口保留 |
| 配置部分成功 | 保存每台每参数状态，不把全站称为回退成功 | 对账、批准补救及重新读回 |
| 控制租约丢失 | 拒绝后续动作并执行批准退出，不覆盖新所有者 | 新授权及租约，复核运行上下文 |
| 证据哈希不符 | 隔离损坏附件，不作为通过或签署证据 | 从可信备份恢复或重取证 |
| RSP部分接收或乱序 | 显示未接收对象，保留任务及Inbox状态 | 补传／查询版本后完整确认 |

数据恢复目标建议为已确认事务RPO=0、未同步事件以本地持久化队列恢复；这些是设计目标，需掉电测试证明。站点备份周期、恢复时间RTO、存储配额及证据保留天数在D05／D06评审后固化，不编造统一值。

## 14 观测与性能

日志统一使用trace_id、task_id、run_id、command_id、case_id及package_id。监控任务等待／执行／退出时间、驱动超时、样本陈旧率、时钟质量、证据写失败、Outbox积压、上传重试、权限拒绝和未闭合故障。日志不能记录秘密值或完整认证令牌。

工作台状态使用按序事件流或轮询，包含event_seq和恢复游标；UI重连从最近序号补齐，不能只显示最后一个“完成”事件而漏掉退出失败。过期数据显式灰化并标时间，不持续冒充实时。

对PRD的1000对象／10000参数验收基准，前端分组和按需展开，长结果分页或虚拟化；拓扑布局与交互分离。控制周期、轮询并发及功率响应要求属于设备与算法能力包，不能为了满足页面2秒目标提高现场控制频率。

## 15 测试策略与追踪

单元测试覆盖规则、单位换算、组聚合和状态机；契约测试覆盖驱动、iEMS和RSP边界；集成测试覆盖事务、幂等、证据及版本；故障注入覆盖断网、重启、丢回执、陈旧数据与复发；现场试点按批准规程执行。模拟测试不替代实际协议与设备验证。

| PRD验收 | 主要设计章节 | 必须保存的验证证据 |
| --- | --- | --- |
| AT01至AT03 | 3、4 | 身份／端口／总线规则及UI定位结果 |
| AT04至AT06 | 4、5、6、11 | 计量转换、权限拒绝、读回差异、继承和失效记录 |
| AT07至AT10 | 5、6、10 | 逐台及方向结果、复发状态轨迹、SAT覆盖与环境隔离 |
| AT11至AT12 | 7、8、9、12 | 包哈希、双路径回执、重试去重及跨域拒绝 |
| AT13至AT15 | 8、10、11 | 假设证据、批准方案、复测、关单门槛及版本链 |
| AT16及N01至N08 | 5、10、12至14 | 重启／断网／磁盘故障、权限、性能和滚动验收 |

恢复状态机必须包含电表先恢复、PV先恢复、两者恢复、资格窗复发、受限恢复窗复发、BESS能力丢失和时钟异常。每个场景验证旧告警仍保留、两窗重置、未知功率未被补零及退出结果。现场故障注入必须符合批准方法，不自行物理断开设备制造风险。

## 16 当前Demo与目标系统的差距

截至2026年11月9日，本地仓库D:\Projects\livoltek-lpe-demo的已知实现基线为c907063。当前具备React／FastAPI／SQLite演示、M1顺序配置、M2模拟执行、M3双路径模拟回执及模拟RSP工单到M4的诊断复测报告。89项相关自动测试和页面走查是演示回归证据，不证明真实接口或生产安全性。

| 领域 | 已知Demo状态 | 生产目标差距 |
| --- | --- | --- |
| 身份与权限 | 环境与流程门槛、演练角色输入 | 可信身份、站点绑定、签名授权、撤销和真实控制租约 |
| 产品资料 | 示例型号、模板与待确认标记 | 受控厂家目录、签发包及完整固件／驱动适用性 |
| iEMS执行 | 合成读数、命令和故障 | 真实驱动、现场采集、硬件持久化与受控退出验证 |
| M2配置读回 | 现有项目仍有依据缺项和差异 | 有效批准值、真实逐台读回及范围化放行 |
| M3交付 | ZIP、阅读摘要及模拟EPC／RSP回执 | 正式接收认证、平台协议、技术建档和服务可用性验证 |
| RSP工单 | 本地生成零馈表失联模拟工单，幂等接单 | 真实派单认证、租户、事件版本、附件及回传 |
| M4处置 | 地址不匹配正常恢复演练、报告版本与待办 | 真实处置授权、更多根因、处置失败／复发分支和生产回传 |
| 数据与运维 | 本地演示持久化和不可覆盖记录 | 正式备份、访问控制、保留期、灾难恢复及平台监控 |

本次整合不修改Demo的设备配置，不将演练值转成批准参数。实施应按PRD的P0、P1、P2阶段分批收敛；P1必须先完成身份、退出和证据底座，再接现场有功率影响的动作。

## 17 来源及设计决策记录

S01为M1系统建模与设置设计V1.0；S02为M2调试与SAT设计V1.0；S03为M3双向项目交接设计V1.0；S04为M4产品售后诊断与现场服务流程V1.0原对话归档。补充依据为用户后续关于连续作业、模拟／现场分离、双向交接、必需事项关单门槛的要求，以及2026年11月9日全流程走查记录。

| 决策 | 整合结果 | 理由及影响 |
| --- | --- | --- |
| ADR01 | 同一工作台共享工程对象与引用链 | 避免四模块形成四套设备数据 |
| ADR02 | M1到M2使用内部引用，取消人工handover | 同软件同人连续工作，不降低执行前再核验 |
| ADR03 | M2配置以读回为主，修正复用M1 | 避免两套长期配置真源和重复写入 |
| ADR04 | 规则为横切服务，无独立L6入口 | 在必要步骤就地提示，不把校验等同运行保证 |
| ADR05 | 双接收路径共享不可变语义基线 | EPC与RSP状态独立，差异可追溯 |
| ADR06 | M4复用M2测试定义，产生新Run | 不另造判据，也不冒用历史通过 |
| ADR07 | 必需待办未完成不能关闭服务单 | 采用最新用户约束，功能恢复可早于最终关单 |
| ADR08 | 真实执行、模拟执行和离线编制隔离 | 保留完整演练能力，同时阻止现场证据污染 |

生产未决项沿用PRD D01至D06。接口路径、数据库扩展方案和软件性能指标为本稿拟定设计；具体产品寄存器、功率阈值、超时和恢复常数必须通过厂家及项目批准依据提供，本文不予臆定。

## 18 V1.1实现与回归范围

产品显示名集中更新为iEMS现场工作台及iEMS Site Engineering Workbench，不改项目ID、数据库对象ID、基线ID、API路径或历史证据哈希。原版文件作为历史依据保留，不能因更名重写原始证据。

本次回归覆盖：有效端口连接唯一绘制、无连接时不凭归属造线、缺失端口显式提示、环境修订隔离、支路拆分不丢失或重复边、冻结快照不混入草案；页面核对步骤03无电气主图、步骤05电气图、步骤06通信控制图以及R17草案与R16历史冻结视图。构建验证与浏览器验证记录随迭代说明保存。冻结图层及名称迭代不增加真实设备执行能力。
