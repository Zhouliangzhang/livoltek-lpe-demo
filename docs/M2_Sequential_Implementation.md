# M2 顺序调试第一阶段

按 iEMS_M2_Commissioning_SAT_Design_V1.0 组织14步；本阶段实现01会话、02模拟自检及03零馈表六项验证。04至14仅展示要求，不复用旧版模拟结果作为新流程通过依据。

运行方式保持不变：构建前端后，由 FastAPI 的 localhost:8000 提供页面。在 CI-20 项目进入 M2，建立模拟会话、自检，然后依次执行通信路径、身份、质量、独立参照、连续窗口和封存。各项可注入适用异常；失败阻断后续，重做前置使下游记录失效。SQLite保存原始记录、前置证据ID与模型哈希，刷新后恢复，重测不覆盖旧记录。

接口：GET/POST /api/plans/{id}/meter-workflow；POST /api/plans/{id}/meter-workflow/{session_id}/run。服务端校验会话归属、模型一致、环境与前置依赖。

明确边界：真实iEMS适配器尚未接入，现场模式只能保存准备范围，不执行硬件命令、不生成现场通过。实物接线、实际SN、独立现场参照和厂家判据不会被合成值补齐。模拟功率、倍率、误差及时间均为独立夹具，不写回M1。模拟参数不是厂家默认值。

检查：pytest tests/test_meter_workflow.py；npm --prefix frontend run test:e2e -- meter-workflow.spec.ts；npm --prefix frontend run build。旧版M2页面测试描述原布局，不能作为本阶段新顺序页面的验收；旧后端功能仍保留且执行完整后端回归。
