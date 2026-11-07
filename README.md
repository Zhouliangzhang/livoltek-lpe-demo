# LIVOLTEK Project Engineer — M1 + M2 Demo

本地目录：`D:\Projects\livoltek-lpe-demo`  
GitHub 私有仓库：https://github.com/Zhouliangzhang/livoltek-lpe-demo

这是可操作的本地工程评审 Demo，使用 React、TypeScript、AntV X6、FastAPI 和 SQLite。仅模拟设备数据，不连接现场设备。

## 启动

首次安装（Python 3.14 与 Node 24 已验证）：

```powershell
cd D:\Projects\livoltek-lpe-demo
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

启动应用（先构建前端，再启动同源后端）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start.ps1
```

浏览器打开 http://127.0.0.1:8000 。API 文档：http://127.0.0.1:8000/docs 。Ctrl+C 停止服务。

开发时可分别运行：

```powershell
.venv/Scripts/python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
# 第二个终端
npm.cmd --prefix frontend run dev
```

开发前端地址为 http://127.0.0.1:5173 ，自动代理 /api 到后端。

## 操作路径

1. M1：载入 LV-01 或复制为新项目；拖动设备，编辑图标、型号、SN、厂家、L1/L2/L3 和责任主体。
2. 添加设备与端口；从端口拖线或用“精确连接”选择来源/目标；分别显示电气、通信、控制关系。通信端口域必须匹配，跨协议需显式网关。
3. “完整模型编辑”支持参数 planned / actual / approved、端口属性、接口协议/信号、遥测绑定、能力与授权字段。点击校验并应用，再保存版本。
4. “校验模型”区分结构错误与缺少批准资料；每次保存产生不可变版本。旧版本可载入为新草案；并发保存冲突会要求重新加载。
5. 模拟遥测可切换正常、反向、过期、缺测、质量异常。只有样例中有测点映射的 E01 显示模拟流；无分支测点不会虚构分支功率。
6. M2：保存拓扑后生成安装计划，查看任务范围、责任、模板版本、缺失输入及依赖。第三方只生成接口资料核对，负载/PCC 生成边界资料核对。
7. SOP 模板库：修改指导内容、规则 JSON、依赖、文档引用和模拟评审状态。保存为新版本；已有计划保留原模板快照。
8. 工程评审：对节点、连接、模板、任务提交意见与模拟结论，保存评审人、时间、模型版本与摘要。
9. 安装计划可记录模拟 PASS/FAIL/BLOCKED 与证据引用。阻塞任务不能通过；缺证据或前置任务未通过不能通过；工程模型变化后必须重新生成计划。历史执行记录不会覆盖。

## 数据与边界

- `baselines/` 原样保留最新版 15 个文件，包括 PRD V2.1、M1 V1.2、M2 V1.1、Schema V1.1、两个样例、规则包和验证器。`docs/BASELINE_MANIFEST.json` 保存原始 SHA256。
- 修订章节优先。原始 Schema V1.1 仍要求 `schema_version: 1.0.0`，本项目遵守这一兼容定义。
- LV-01 从原始 mixed-vendors 样例初始化；补充布局、设备来源、等级和默认拒绝授权。BESS 为 125 kW / 261 kWh 示例；原样例包含第二台第三方 PV，不宣称系统总光伏容量是 100 kW。
- SQLite 在 `demo.db`，路径可通过 `LPE_DB` 修改。模型以完整 Schema JSON 快照保存，而非仅保存 X6 图形；评审、模板、计划和执行记录独立保存。
- 制造商、工程责任、技术能力和操作授权分开记录。EPC 承担工程设计、施工、集成和合同验收；LIVOLTEK 提供其产品及约定接口的技术支持。
- 原始 SOP 全为 DRAFT。新增指导文案仅作资料核对。界面中的 APPROVED 是本地模拟评审，未接入身份认证、厂家签发、现场许可或资格审核，永远不能发布正式生产计划。`/publish` 明确返回 403。
- 未实现：真实设备/RSP 接入、M3–M6 作业、LV-02/MV 专项规则、真实照片上传、离线同步、正式安全/电气工程认证。当前证据为文本或文档引用；参数与复杂接口使用完整模型编辑器。
- 仅绑定本机 127.0.0.1。此 Demo 没有身份认证，不应直接暴露为公网服务。

## 验证与复现

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check.ps1
```

检查包括原始样例验证、19 项后端测试、TypeScript/生产构建，以及 Edge 浏览器端到端流程。浏览器测试使用独立 `.e2e-*.db`，不修改 `demo.db`；需安装 Microsoft Edge。前端由 package-lock.json 固定依赖，后端由 backend/requirements.lock.txt 固定本次验证版本。

目录：`backend/` 后端、`frontend/` 前端与浏览器测试、`tests/` API/规则测试、`docs/` 计划/截图/验证记录、`scripts/` 启动与安装。

## Git 工作流

main 保存已验证快照；develop 用于增量开发。首次同步已完成，远程为私有。常用命令：

```powershell
git switch develop
git pull --ff-only origin develop
# 编辑和验证后提交
git push origin develop
```

本次自动提交使用 Codex <codex@localhost>，未修改您的全局 Git 身份配置。后续人工提交可在仓库内设置自己的 user.name / user.email。

## M1 engineering workspace (2026-11-07)

The independent React app now opens directly to the six-layer engineering workspace. WordPress/Elementor login is not required, and dev.livoltek.com has not been modified by this stage.

- Three intake paths: LIVOLTEK scan input, third-party manual entry, and non-SN electrical structures.
- Scan demo: open scan intake, fill demo code, parse, then confirm location and add. Input format: `LIVOLTEK:DEMO-BESS-125:<serial>`. This uses an explicitly illustrative local catalogue, not a manufacturer production lookup. Camera decoding is not implemented; keyboard-wedge scanners and pasted decoded payloads work.
- Manual entry includes manufacturer/model, optional SN, firmware, location, document reference, parent structure and port domains. Entries remain unverified. Scan status never implies engineering approval.
- Tree, typed port topology, asset/source inspector, planned/actual/approved comparison, validation/review, audit and telemetry mapping views are available. The configuration comparison is read-only in this stage.
- Added objects and provenance are persisted through Save Version, validated by the existing schema and semantic rules. The demo does not dispatch device commands or authorize production work.
- Validation: TypeScript/Vite build, 19 backend tests, browser workflows covering malformed scan input, duplicate SN rejection, both intake paths, invalid electrical connections, persistence, telemetry states and M2 regression.

Preview: http://127.0.0.1:8000/ . Start with the existing `scripts/start.ps1` instructions above.

### M1 layout revision: layered workflow and read-only generated topology

The top project layout is retained. The former three-column editor and standalone intake strip have been replaced by a full-width system overview followed by L2-L6 workflow tabs.

- L2 embeds Add Electrical Structure. L3 embeds LIVOLTEK scan intake and third-party manual intake. L4 contains recorded ports/connections; L5 shows configuration comparison; L6 contains rule checks, review, provenance and telemetry settings.
- Topology geometry is automatically derived from the recorded electrical graph, rooted at PCC objects. Objects without a recorded electrical path are displayed separately. It does not infer or invent connections.
- The X6 canvas has no mutation callbacks, selection editing, node dragging, port dragging or panning. Only zooming/fit-to-view is enabled. Zoom does not dirty the engineering model. Existing saved manual layout coordinates are ignored by this view.
- Browser regression checks cover a failed node-drag attempt leaving geometry unchanged, zoom changing the viewport without enabling Save, both intake workflows, SN rejection, connection validation, persistence and M2 regression.

### On-demand asset details and intake ownership

Device details are hidden by default and after adding an asset. Clicking a device name, row, or View/Supplement opens that device's details; Close Details hides them again. Switching layers or projects resets the detail view.

LIVOLTEK identity/master data is read-only in the UI: manufacturer/model, scanned SN, catalogue document and port template. Users supplement the site label, installed location, observed firmware and structure assignment. Scan intake still uses the explicitly marked demo catalogue; live manufacturer lookup and camera decoding remain unconnected. Third-party manufacturer/model/document and SN can be manually entered or corrected; corrections remain unverified and copy shared model records before changing them.

Validated via production build and both browser workflows: default-hidden details, opening/closing, scanner-owned read-only fields, editable third-party data, persistence, domain validation and the existing read-only topology/M2 regressions.

### L1-driven progressive topology

Topology now starts from an explicit `L1-FRAMEWORK-DEMO-1` presentation template based on project structure, voltage, energy composition and operating mode (M1 V1.2 classification and layered-view requirements). It exists even when L2-L6 records are empty. Missing structural/device types appear as labelled dashed placeholders; supplied objects replace matching placeholders. Country and EPC remain explicit project context, not implied country-specific approved design.

Placeholders are display-only: they create no persisted assets, ports, assignments or electrical edges. Existing engineering records are never discarded when the project definition changes. Type coverage is not proof of per-zone engineering correctness; LV-02 shows minimum zone requirements without inventing interties, and MV-03 remains a provisional specialization. Physical/communication/control edges are rendered only from recorded port-level connections.

The overview reports L2 template coverage, L3 SN/model-version coverage, L4 recorded connections, L5 planned/actual/approved presence, and L6 current-revision review/baseline state. These are evidence counts, not approval or complete-design claims. The original baselines and manufacturer approval boundaries are unchanged.

Validated: production build and five tests (three framework cases plus both browser regression workflows).

### L4 device-first connections

L4 now starts with source device/structure, source port, target device/structure and target port. It lists recorded L2/L3 objects and filters ports by selected object and connection kind, direction, matching domain and known electrical voltage/phase values. Exactly one available port is automatically selected; multiple options require explicit selection. Self-connections and already-recorded pairs are excluded from target choices. Changing source or connection kind clears dependent choices.

Save Connection validates through the existing project-save endpoint and persists a new optimistic-concurrency-checked engineering revision, including other current project changes (stated beside the action). On success the returned model refreshes the connection table and generated read-only topology. Failure keeps the form and shows the server error. Connections remain DRAFT; compatibility checks do not constitute engineering approval.

Validated: production build and seven tests, including automatic single-port selection, multi-port choice, incompatible endpoints, control direction, duplicate/voltage filtering, immediate topology update and reload persistence.

### System settings and operating-condition review

See `docs/PRODUCT_SCOPE.md` for the clarified product definition. L5 now records existing numeric planned/site system settings and preserves approved reference values read-only. L6 checks the L1-L5 input conditions and exposes missing data, discrepancies and on-site verification requirements; it does not certify normal operation. Technical collaboration is labelled separately from formal EPC engineering approval, legal inspection and acceptance. Changes invalidate prior displayed check results.

Validated: production build and eight tests, including setting persistence and invalidation of prior L6 checks. Manufacturer-specific complete setting catalogues and field-operation verification are not implemented by this stage.
