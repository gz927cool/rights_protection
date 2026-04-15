import { useState } from 'react'

export interface RoadmapStep {
  step_name: string
  step_title: string
  suitable_scenario: string
  operation_guide: string
  speaking_template?: string
  required_materials: string[]
  best_timing: string
  cost: string
  success_rate?: string
}

export interface RoadmapProps {
  caseCategory: string
  riskLevel?: string
}

const ROADMAP_STEPS: RoadmapStep[] = [
  {
    step_name: '协商',
    step_title: '第一步：与用人单位协商',
    suitable_scenario: '劳动关系清晰、争议金额较小、双方仍有沟通意愿的案件',
    operation_guide: '1. 整理好相关证据材料\n2. 书面提出您的诉求（可使用参考话术）\n3. 保持沟通记录\n4. 协商不成及时转向下一步',
    speaking_template: '您好，我是XX公司的员工XXX。本人于XXXX年XX月入职，现公司存在XXX行为，侵害了我的合法权益。请公司依法予以补偿/赔偿。如公司拒绝或无法达成一致，我将保留通过法律途径维护自身权益的权利。',
    required_materials: ['劳动合同', '工资流水/考勤记录', '违法事实证据', '诉求书面材料'],
    best_timing: '争议发生后30日内',
    cost: '无',
    success_rate: '约30%',
  },
  {
    step_name: '调解',
    step_title: '第二步：申请劳动调解',
    suitable_scenario: '协商不成或一方态度消极，需要第三方介入调停的案件',
    operation_guide: '1. 前往当地工会或街道调解中心申请\n2. 提交书面调解申请\n3. 配合调解员安排调解会议\n4. 达成调解协议后申请司法确认',
    speaking_template: '本人于XXXX年XX月就XXXXX事宜与公司协商未果，现申请调解。本人诉求如下：1.XXXX；2.XXXX。希望通过调解化解争议，维护双方合法权益。',
    required_materials: ['身份证复印件', '劳动合同', '证据材料清单', '调解申请书', '企业工商信息'],
    best_timing: '争议发生后1年内',
    cost: '无',
    success_rate: '约50%',
  },
  {
    step_name: '仲裁',
    step_title: '第三步：申请劳动仲裁',
    suitable_scenario: '调解不成或不愿意调解，需通过法律途径强制解决的案件',
    operation_guide: '1. 准备完整的证据材料\n2. 撰写仲裁申请书\n3. 向有管辖权的仲裁委提交申请\n4. 按时参加庭审\n5. 对裁决不服可在15日内提起诉讼',
    speaking_template: '申请人XXX，被申请人XXXX公司。请求事项：1.请求裁决被申请人支付XXXX；2.请求裁决被申请人赔偿XXXX。事实与理由：XXXX。',
    required_materials: ['仲裁申请书', '身份证复印件', '劳动合同', '全部证据材料', '企业工商信息', '授权委托书（如委托代理人）'],
    best_timing: '争议发生后1年内',
    cost: '无（劳动者申请免收）',
    success_rate: '约60-70%',
  },
]

const SUQIAN_CONTACTS = [
  {
    name: '宿迁市劳动人事争议仲裁委员会',
    address: '宿迁市宿城区洪泽湖路156号',
    phone: '0527-843XXXXX',
    note: '负责宿迁市直及宿城区、宿豫区的劳动争议仲裁案件',
  },
  {
    name: '宿迁市总工会法律维权部',
    address: '宿迁市宿城区太湖路99号',
    phone: '0527-843XXXXX',
    note: '提供免费法律咨询和劳动争议调解服务',
  },
]

function getRecommendedSteps(caseCategory: string, _riskLevel?: string): string[] {
  const cat = caseCategory.toLowerCase()
  if (cat.includes('欠薪') || cat.includes('工资') || cat.includes('拖欠')) {
    return ['调解', '仲裁']
  }
  if (cat.includes('开除') || cat.includes('解除') || cat.includes('辞退')) {
    return ['协商', '调解']
  }
  if (cat.includes('工伤')) {
    return ['调解', '仲裁']
  }
  if (cat.includes('社保') || cat.includes('保险') || cat.includes('公积金')) {
    return ['调解', '仲裁']
  }
  return ['协商', '调解', '仲裁']
}

export default function RoadmapView({ caseCategory, riskLevel }: RoadmapProps) {
  const [expandedStep, setExpandedStep] = useState<string | null>(null)
  const [showContacts, setShowContacts] = useState(false)

  const recommended = getRecommendedSteps(caseCategory, riskLevel)

  const toggleStep = (stepName: string) => {
    setExpandedStep(prev => (prev === stepName ? null : stepName))
  }

  return (
    <div className="w-full max-w-6xl mx-auto p-4">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">
          维权行动路线图
        </h2>
        <p className="text-gray-600">
          根据您的案件类型（<span className="font-semibold text-blue-700">{caseCategory}</span>
          {riskLevel && `，风险等级：${riskLevel}`}），推荐以下维权路径：
        </p>
        <div className="flex gap-2 mt-2 flex-wrap">
          {recommended.map(step => (
            <span
              key={step}
              className="px-3 py-1 bg-green-100 text-green-800 text-sm font-medium rounded-full"
            >
              推荐：{step}
            </span>
          ))}
        </div>
      </div>

      {/* Three Step Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {ROADMAP_STEPS.map((step) => {
          const isRecommended = recommended.includes(step.step_name)
          const isExpanded = expandedStep === step.step_name

          return (
            <div
              key={step.step_name}
              className={`
                border-2 rounded-xl cursor-pointer transition-all duration-300
                ${isExpanded ? 'ring-2 ring-blue-400 shadow-lg' : 'shadow-sm hover:shadow-md'}
                ${isRecommended ? 'border-green-400 bg-green-50' : 'border-gray-200 bg-white'}
              `}
              onClick={() => toggleStep(step.step_name)}
            >
              {/* Card Header */}
              <div className="p-4 border-b border-gray-100">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className={`
                        w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-lg
                        ${step.step_name === '协商' ? 'bg-blue-500' : step.step_name === '调解' ? 'bg-orange-500' : 'bg-red-500'}
                      `}
                    >
                      {step.step_name === '协商' ? '1' : step.step_name === '调解' ? '2' : '3'}
                    </div>
                    <div>
                      <h3 className="font-bold text-gray-800">{step.step_name}</h3>
                      <p className="text-xs text-gray-500">
                        {isRecommended ? '推荐路径' : '可选路径'}
                      </p>
                    </div>
                  </div>
                  <span className="text-gray-400 text-xl">{isExpanded ? '−' : '+'}</span>
                </div>
              </div>

              {/* Quick Info */}
              <div className="p-4 space-y-3">
                <div>
                  <p className="text-xs text-gray-500 mb-1">适用场景</p>
                  <p className="text-sm text-gray-700">{step.suitable_scenario}</p>
                </div>

                <div className="flex gap-4">
                  <div>
                    <p className="text-xs text-gray-500 mb-1">成本</p>
                    <p className="text-sm font-medium text-green-600">{step.cost}</p>
                  </div>
                  {step.success_rate && (
                    <div>
                      <p className="text-xs text-gray-500 mb-1">成功率</p>
                      <p className="text-sm font-medium text-blue-600">{step.success_rate}</p>
                    </div>
                  )}
                  <div>
                    <p className="text-xs text-gray-500 mb-1">最佳时机</p>
                    <p className="text-sm font-medium text-gray-700">{step.best_timing}</p>
                  </div>
                </div>
              </div>

              {/* Expanded Details */}
              {isExpanded && (
                <div className="px-4 pb-4 space-y-4 border-t border-gray-100 pt-4">
                  <div>
                    <p className="text-xs text-gray-500 mb-1 font-semibold">操作指南</p>
                    <div className="text-sm text-gray-700 whitespace-pre-line bg-gray-50 rounded-lg p-3">
                      {step.operation_guide}
                    </div>
                  </div>

                  {step.speaking_template && (
                    <div>
                      <p className="text-xs text-gray-500 mb-1 font-semibold">参考话术</p>
                      <div className="text-sm text-gray-700 whitespace-pre-line bg-blue-50 rounded-lg p-3 border border-blue-100">
                        {step.speaking_template}
                      </div>
                    </div>
                  )}

                  <div>
                    <p className="text-xs text-gray-500 mb-1 font-semibold">所需材料</p>
                    <div className="flex flex-wrap gap-2">
                      {step.required_materials.map((mat, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded border border-gray-200"
                        >
                          {mat}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Suqian Contacts */}
      <div className="mt-6">
        <button
          onClick={() => setShowContacts(!showContacts)}
          className="w-full flex items-center justify-between p-4 bg-amber-50 border border-amber-200 rounded-xl hover:bg-amber-100 transition-colors"
        >
          <div className="flex items-center gap-3">
            <span className="text-2xl">📍</span>
            <div className="text-left">
              <p className="font-semibold text-amber-800">宿迁市办理地点及联系方式</p>
              <p className="text-sm text-amber-600">点击查看宿迁本地劳动维权服务网点</p>
            </div>
          </div>
          <span className="text-amber-600 text-xl">{showContacts ? '▲' : '▼'}</span>
        </button>

        {showContacts && (
          <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-4">
            {SUQIAN_CONTACTS.map((contact, idx) => (
              <div
                key={idx}
                className="p-4 bg-white border border-amber-200 rounded-xl shadow-sm"
              >
                <h4 className="font-semibold text-gray-800 mb-2">{contact.name}</h4>
                <div className="space-y-1 text-sm text-gray-600">
                  <p className="flex items-start gap-2">
                    <span className="text-gray-400">📍</span>
                    <span>{contact.address}</span>
                  </p>
                  <p className="flex items-center gap-2">
                    <span className="text-gray-400">📞</span>
                    <span className="text-blue-600 font-medium">{contact.phone}</span>
                  </p>
                  <p className="flex items-start gap-2">
                    <span className="text-gray-400">💡</span>
                    <span>{contact.note}</span>
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Flow Arrow Hint */}
      <div className="mt-6 flex items-center justify-center gap-2 text-gray-500 text-sm">
        <span>协商</span>
        <span className="text-gray-400">→</span>
        <span>调解</span>
        <span className="text-gray-400">→</span>
        <span>仲裁</span>
        <span className="mx-2 text-gray-300">|</span>
        <span className="text-green-600">绿色边框 = 推荐路径</span>
        <span className="mx-2 text-gray-300">|</span>
        <span className="text-blue-600">点击卡片展开详情</span>
      </div>
    </div>
  )
}
