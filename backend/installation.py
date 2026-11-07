"""Draft installation workflow, without unverified manufacturer values."""
PHASES = [
 ('POSITION','WP03','设备就位与固定',[],
  ['核对到货型号、设备标识与 L3 安装位置，记录外观和运输异常。','由 EPC 按批准的搬运及吊装方案组织设备就位。','核对基础、安装方向、固定和维护空间，逐台记录安装结果。'],
  '设备重量与重心、允许吊装点、搬运限制、基础载荷、安装间距、固定方式及紧固扭矩',
  '就位方案、基础验收、位置与固定检查记录'),
 ('EARTH','WP03G','保护接地与等电位连接',['INSTALL-POSITION'],
  ['核对 EPC 接地设计和设备指定接地点。','按批准设计完成保护接地及等电位连接，并记录连接位置。','由合格人员按批准方法核验连接连续性，记录结果与仪器信息。'],
  '接地点标识、端子要求、导体连接限制和紧固扭矩；检测方法与判据需结合 EPC 设计确认',
  '接地设计引用、接地连接照片、连续性检查记录'),
 ('POWER','WP03P','电气接线',['INSTALL-EARTH'],
  ['确认现场作业许可与隔离条件，由合格人员组织接线。','按 EPC 批准接线图及 L4 端口关系核对回路、线缆标识与端子。','完成电气连接后记录相序或极性核对、端接检查与异常项。'],
  '允许线缆范围、端子定义、压接方式、剥线要求和紧固扭矩；线缆选型及保护配合由 EPC 核定',
  '作业许可、批准接线图、回路端接与相序或极性检查记录'),
 ('COMMS','WP05','通信与控制接线',['INSTALL-POWER'],
  ['按 L4 核对零馈表、iEMS、光伏和储能设备的连接关系；数量以本项目模型为准。','按批准接口文件完成通信与控制线缆连接、标识和屏蔽处理。','核对 L5 计划地址及通信设置，记录端口映射；通信测试所需供电条件另行批准。'],
  '各型号引脚定义、线缆与屏蔽要求、总线终端和拓扑限制、协议及兼容版本',
  '通信接线图、设备端口映射、线缆标识及检查记录'),
 ('PREPOWER','WP06','上电前现场检查',['INSTALL-COMMS'],
  ['汇总设备固定、接地、电气与通信接线记录，逐项核对未关闭问题。','由 EPC 按批准检查方案组织必要检查或试验，记录仪器、结果与判据来源。','核对保护设置、开关状态、安全措施和作业许可，提交有权限人员确认；本工作包不执行上电。'],
  '厂家上电前检查清单、允许测试方法及限制、保护设置依据和启动前提；缺少依据不得自行试验或上电',
  '签署检查表、试验记录、缺陷关闭记录及 EPC 作业许可'),
]
def installation_templates():
    result=[]
    for key,wp,title,deps,steps,vendor,epc in PHASES:
        rule={'rule_id':'INSTALL-'+key,'status':'DRAFT','sop_template_id':'SOP-INSTALL-'+key,
              'sop_version':'0.1','work_package':wp,'when':{},'depends_on':deps,
              'risk':'SAFETY_CRITICAL','source_doc_ref':None,
              'evidence_requirements':['installation_record','vendor_document','signed_checklist']}
        result.append({'template_id':rule['sop_template_id'],'version':1,'status':'DRAFT',
                       'title':title,'instructions':'由 EPC 按批准设计与厂家受控指导组织实施；本页为待确认的安装流程草案。',
                       'scope_type':'EPC_DOCUMENT_CHECK','source_document_ref':None,'rule':rule,'demo_only':True,
                       'installation_steps':steps,'vendor_pending':vendor,'epc_pending':epc})
    return result
