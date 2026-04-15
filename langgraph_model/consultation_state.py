"""
九步咨询系统状态定义

定义 ConsultationState 和所有子类型，
对应 Phase 1 - ConsultationState 类型系统设计。
"""
from typing import Dict, TypedDict, List, Optional, Annotated, Literal, Any
from datetime import datetime
from operator import add as messages_add


def _merge_dicts(a: Dict, b: Dict) -> Dict:
    """Merge two dicts recursively - b values take precedence."""
    result = a.copy()
    for k, v in b.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _merge_dicts(result[k], v)
        else:
            result[k] = v
    return result


def _union_sets(a, b):
    """Union of two sets."""
    return list(set(a) | set(b))


def _last_writer(a, b):
    """Last writer wins - used for scalars and objects."""
    return b


def _replace_list(a, b):
    """Replace list with latest value (for evidence_items)."""
    return b if isinstance(b, list) else a


# ============================================================================
# 步骤状态
# ============================================================================

class StepData(TypedDict):
    """单个步骤采集的数据"""
    answers: Dict[str, Any]           # 问题ID → 回答
    status: Literal["in_progress", "completed", "dirty"]
    completed_at: Optional[str]         # ISO格式 datetime
    extra: Dict[str, Any]              # 步骤特有扩展数据


# ============================================================================
# 证据体系
# ============================================================================

class EvidenceItem(TypedDict):
    """单条证据项"""
    id: str                            # 唯一标识
    name: str                          # 证据名称
    description: str                   # 通俗解释
    category: Literal["必备", "加强", "兜底"]  # 证据分类
    tier: int                          # 1=最强 2=辅助 3=兜底
    suitability: List[str]             # 适用的案由
    guidance_template: Optional[str]   # 获取指引模板ID
    status: Literal["A", "B", "C", ""] # A=已有 B=可补充 C=无法取得 ""=未标记
    status_reason: Optional[str]       # 状态说明
    guidance: Optional[str]            # 获取指引（话术/操作指南）
    uploaded_file_refs: List[str]     # 上传文件ID列表


class FileRef(TypedDict):
    """上传文件引用"""
    file_id: str                       # 文件唯一ID
    filename: str                       # 原始文件名
    stored_path: str                   # 本地存储路径
    uploaded_at: str                   # 上传时间
    evidence_item_id: Optional[str]    # 关联的证据项ID


# ============================================================================
# 权益与赔偿
# ============================================================================

class RightItem(TypedDict):
    """权益清单项"""
    right_name: str                    # 权利名称
    amount: Optional[float]            # 金额
    calculation_basis: str              # 计算依据
    legal_basis: str                   # 法律依据
    priority: int                      # 显示优先级


# ============================================================================
# 案件定性
# ============================================================================

class CaseQualification(TypedDict):
    """案件定性结果"""
    case_facts: str                    # 规范化案件事实描述
    case_types: List[str]              # 三级案由编码列表
    rights_list: List[RightItem]        # 权益清单
    legal_basis: List[str]             # 法律依据索引


# ============================================================================
# 风险提示
# ============================================================================

class RiskPoint(TypedDict):
    """单个风险点"""
    risk_type: str                     # 时效过期/证据链断裂/诉求计算错误
    description: str                    # 风险描述
    is_high_risk: bool                # 是否高风险
    reason: str                        # 风险原因
    mitigation: str                   # 规避建议


class RiskAssessment(TypedDict):
    """风险评估结果"""
    level: Literal["高", "中", "低"]
    risk_points: List[RiskPoint]
    evidence_chain_evaluation: str     # 证据链评估
    recommendations: List[str]         # 总体建议


# ============================================================================
# 文书
# ============================================================================

class DocumentDraft(TypedDict):
    """文书草稿"""
    template_type: str                 # 文书模板类型
    content: str                       # 填充后的文书内容
    gaps: List[str]                    # 高亮标注的缺失字段
    created_at: str
    updated_at: str


# ============================================================================
# 路线图
# ============================================================================

class RoadmapStep(TypedDict):
    """路线图单个步骤"""
    step_name: str
    step_title: str
    suitable_scenario: str
    operation_guide: str
    speaking_template: Optional[str]
    required_materials: List[str]
    best_timing: str
    cost: str
    success_rate: Optional[str]


class Roadmap(TypedDict):
    """行动路线图"""
    recommended_path: List[str]
    steps: List[RoadmapStep]
    mediation_phone: Optional[str]


# ============================================================================
# 步骤定义
# ============================================================================

STEP_NAMES: List[str] = [
    "step1_selector",       # 1: 模式选择
    "step2_initial",        # 2: 问题初判
    "step3_common",        # 3: 通用12问
    "step4_special",        # 4: 特殊问题
    "step5_qualification", # 5: 案件定性
    "step6_evidence",       # 6: 证据攻略
    "step7_risk",          # 7: 风险提示
    "step8_documents",      # 8: 文书生成
    "step9_roadmap",       # 9: 行动路线图
    "step10_review",       # 10: 求助复核
]

STEP_DISPLAY_NAMES: Dict[str, str] = {
    "step1_selector": "模式选择",
    "step2_initial": "问题初判",
    "step3_common": "通用问题",
    "step4_special": "特殊问题",
    "step5_qualification": "案件定性",
    "step6_evidence": "证据攻略",
    "step7_risk": "风险提示",
    "step8_documents": "文书生成",
    "step9_roadmap": "行动路线图",
    "step10_review": "求助复核",
}


def get_step_number(step_name: str) -> int:
    """从步骤名获取步骤编号（1-10）"""
    return STEP_NAMES.index(step_name) + 1


def get_step_name(step_number: int) -> str:
    """从步骤编号获取步骤名"""
    return STEP_NAMES[step_number - 1]


def get_dirty_range(from_step: int) -> set[int]:
    """获取从指定步骤开始的脏步骤范围（包含from_step）"""
    return set(range(from_step, 11))


# ============================================================================
# 主状态
# ============================================================================

class ConsultationState(TypedDict):
    """
    九步咨询系统主状态

    消息累积 + 九步流程追踪 + 案件核心数据 + 证据体系 + 文书
    """
    # --- 消息累积（不变）---
    messages: Annotated[List[Any], messages_add]

    # --- 九步核心 ---
    current_step: Annotated[int, _last_writer]  # 1-10, current step
    completed_steps: Annotated[set[int], _union_sets]  # 已完成步骤集合
    step_data: Annotated[Dict[str, StepData], _merge_dicts]  # 每步采集的数据
    dirty_steps: Annotated[set[int], _union_sets]  # 需重算的脏步骤

    # --- 案件核心 ---
    case_category: Optional[str]        # 6大分类之一（欠薪/开除/工伤/调岗/社保/其他）
    qualification: Optional[CaseQualification]  # 案件定性结果
    risk_assessment: Optional[RiskAssessment]  # 风险提示
    roadmap: Optional[Roadmap]          # 行动路线图

    # --- 证据体系 ---
    evidence_items: Annotated[List[EvidenceItem], _replace_list]  # 证据清单
    evidence_files: Annotated[Dict[str, FileRef], _merge_dicts]  # 上传文件引用

    # --- 文书 ---
    document_draft: Optional[DocumentDraft]  # 文书草稿

    # --- 律师求助 ---
    lawyer_help_status: Optional[Literal["pending", "sent", "replied"]]  # 律师求助状态

    # --- 元数据 ---
    session_id: str
    started_at: str                      # ISO格式
    last_updated: Annotated[str, _last_writer]  # ISO格式
    member_id: Optional[str]            # 会员ID（登录后填充）
    resume_token: Optional[str]         # 断点恢复token


class ConsultationInput(TypedDict):
    """九步咨询系统输入状态（初始状态）"""
    messages: Annotated[List[Any], messages_add]
    session_id: str
    member_id: Optional[str] = None
    resume_token: Optional[str] = None
    current_step: Optional[int] = 1
    completed_steps: Optional[set] = None
    step_data: Optional[Dict[str, StepData]] = None
    dirty_steps: Optional[set] = None
    case_category: Optional[str] = None
    qualification: Optional[Any] = None
    risk_assessment: Optional[Any] = None
    roadmap: Optional[Any] = None
    evidence_items: Optional[List[EvidenceItem]] = None
    evidence_files: Optional[Dict[str, FileRef]] = None
    document_draft: Optional[Any] = None
    lawyer_help_status: Optional[str] = None


# ============================================================================
# 状态初始化
# ============================================================================

def create_initial_state(
    session_id: str,
    member_id: Optional[str] = None,
    resume_data: Optional[Dict] = None,
) -> Dict:
    """
    创建九步咨询系统的初始状态或从断点恢复状态

    Args:
        session_id: 会话ID
        member_id: 会员ID（可选）
        resume_data: 断点保存的数据（可选，用于resume_token恢复）

    Returns:
        完整的初始状态字典
    """
    now = datetime.now().isoformat()

    if resume_data is not None:
        # 从断点恢复：resume_data 包含完整状态快照
        state = resume_data.copy()
        state["last_updated"] = now
        state["resume_token"] = None  # 恢复后清除token
        return state

    # 全新状态
    return {
        "messages": [],
        "current_step": 1,
        "completed_steps": set(),
        "step_data": {},
        "dirty_steps": set(),
        "case_category": None,
        "qualification": None,
        "risk_assessment": None,
        "roadmap": None,
        "evidence_items": [],
        "evidence_files": {},
        "document_draft": None,
        "lawyer_help_status": None,
        "session_id": session_id,
        "started_at": now,
        "last_updated": now,
        "member_id": member_id,
        "resume_token": None,
    }


def serialize_state(state: Dict) -> str:
    """
    将状态序列化为JSON字符串（用于resume_token）
    注意：set 类型需要特殊处理
    """
    import json

    def set_default(obj):
        if isinstance(obj, set):
            return {"__type__": "set", "values": list(obj)}
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    return json.dumps(state, default=set_default, ensure_ascii=False)


def deserialize_state(state_json: str) -> Dict:
    """
    从JSON字符串反序列化状态（用于resume_token恢复）
    """
    import json

    def parse_object(obj):
        if isinstance(obj, dict) and obj.get("__type__") == "set":
            return set(obj["values"])
        return obj

    state = json.loads(state_json)
    return _recursive_parse(state)


def _recursive_parse(obj):
    """递归解析 JSON 对象，转换 set 类型"""
    if isinstance(obj, dict):
        if obj.get("__type__") == "set":
            return set(obj["values"])
        return {k: _recursive_parse(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_recursive_parse(item) for item in obj]
    return obj


# ============================================================================
# 证据数据加载工具
# ============================================================================

def get_evidence_checklist(case_category: str) -> List[EvidenceItem]:
    """
    根据案由加载对应的证据清单

    Args:
        case_category: 案由分类（欠薪/开除/工伤/调岗/社保/其他）

    Returns:
        证据项列表，每个证据项包含完整字段
    """
    try:
        from data.consultation.evidence_data import EVIDENCE_CHECKLIST
    except ImportError:
        return []

    items = EVIDENCE_CHECKLIST.get(case_category, [])
    result = []
    for item in items:
        evidence_item: EvidenceItem = {
            "id": item["id"],
            "name": item["name"],
            "description": item["description"],
            "category": item["category"],
            "tier": item["tier"],
            "suitability": item.get("suitability", [case_category]),
            "guidance_template": item.get("guidance_template"),
            "status": "",
            "status_reason": None,
            "guidance": None,
            "uploaded_file_refs": [],
        }
        result.append(evidence_item)
    return result


def get_evidence_guidance(template_key: str) -> Optional[Dict]:
    """
    获取证据收集指引

    Args:
        template_key: 指引模板的key

    Returns:
        指引内容字典，包含 title, steps, tips, alternative
    """
    try:
        from data.consultation.evidence_guidance_templates import EVIDENCE_GUIDANCE_TEMPLATES
        return EVIDENCE_GUIDANCE_TEMPLATES.get(template_key)
    except ImportError:
        return None


def evaluate_evidence_completeness(evidence_items: List[EvidenceItem]) -> str:
    """
    评估证据完整度

    Args:
        evidence_items: 证据清单

    Returns:
        评级：充分/基本完整/不完整/严重缺乏
    """
    if not evidence_items:
        return "严重缺乏"

    total = len(evidence_items)
    a_count = sum(1 for e in evidence_items if e.get("status") == "A")
    b_count = sum(1 for e in evidence_items if e.get("status") == "B")
    c_count = sum(1 for e in evidence_items if e.get("status") == "C")
    unmarked = sum(1 for e in evidence_items if not e.get("status"))

    # A类证据数量判断
    if a_count == 0 and total > 0:
        return "严重缺乏"
    if a_count >= 3 and (a_count + b_count) / total >= 0.8:
        return "充分"
    if a_count >= 2 or (a_count + b_count) / total >= 0.6:
        return "基本完整"
    return "不完整"


