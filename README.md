# LIVOLTEK Project Engineer — M1 + M2 Demo

独立本地开发仓库。当前为环境与基线准备阶段，Demo 应用尚未完成。

## 最新基线

`baselines/` 保留从用户 Downloads 原始 ZIP 提取的全部 15 个文件：

- LIVOLTEK_LPE_PRD_V2.1（Word / Markdown）
- LIVOLTEK_M1_Detailed_Design_V1.2（Word / Markdown）
- LIVOLTEK_M2_Detailed_Design_V1.1（Word / Markdown）
- LIVOLTEK_Engineering_Model_Schema_V1.1（Word / Markdown）
- JSON Schema、两份 LV-01 样例、SOP 规则包、验证程序及变更记录

原件保持不变，修订章节优先于旧章节。Schema V1.1 的 schema_version 仍为原始定义的 1.0.0，不能擅自改为 1.1。样例均为待评审数据，不能作为施工许可。

## 开发环境

在 Codex 或编辑器中打开本文件所在的整个文件夹。无需新建聊天即可访问文件；需要独立开发聊天时，将此目录作为项目目录。

技术栈：React + TypeScript + AntV X6；FastAPI + SQLite。

联网后，在仓库根目录的 PowerShell 执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
.venv/Scripts/python.exe baselines/validate_demo.py
```

setup 使用项目内 .venv 和 frontend/node_modules，不安装全局依赖。安装完成后应生成并提交前端 package-lock.json，后续使用 npm ci。当前尚未生成依赖锁文件，版本范围需在安装验证后冻结。

## GitHub

目标：Zhouliangzhang/livoltek-lpe-demo，私有仓库。
当前尚未创建或推送：本机 GitHub CLI 登录凭据失效，需要重新登录。

```powershell
gh auth login -h github.com
powershell -ExecutionPolicy Bypass -File scripts/sync-github.ps1
```

同步脚本核对登录账号；若同名仓库已存在则停止，避免误接已有项目。创建后推送 main，并在本地创建 develop 分支用于后续增量开发。

## 目录

- baselines：原始设计与数据契约，清单见 docs/BASELINE_MANIFEST.json
- backend：后端与依赖声明
- frontend：前端依赖声明与源码目录
- tests：后续自动化测试
- docs：实施计划与验证记录
- scripts：环境准备和 GitHub 同步

## 当前验证结果

两份原始工程样例及规则包的 Schema / 语义校验通过。9 份下载 ZIP 的 SHA256 完全相同，无版本冲突。开发机可用 Python 3.14.5、Node 24.16.0、npm 11.13.0。

当前执行环境无法解析 pypi.org，依赖安装未完成；.venv 仅建立了 Python 隔离目录。尚未实现应用启动入口，不能宣称 Demo 已可运行。后续按 docs/IMPLEMENTATION.md 分阶段完成应用及验证。
