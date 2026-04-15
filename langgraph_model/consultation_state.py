"""
九步咨询系统状态定义

定义 ConsultationState 和所有子类型，
对应 Phase 1 - ConsultationState 类型系统设计。
"""
from typing import Dict, TypedDict, List, Optional, Annotated, Literal, Any
from datetime import datetime
from operator import add as messages_add


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
    category: Literal["必备", "加强"]  # 证据分类
    tier: int                          # 1=最强 2=辅助 3=兜底
    status: Literal["A", "B", "C"]     # A=已有 B=可补充 C=无法取得
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
    priority: int                      # 显示优先级


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
    summary: str                       # 综合概述


# ============================================================================
# 文书
# ============================================================================

class DocumentDraft(TypedDict):
    """文书草稿"""
    template_type: Literal["仲裁申请书", "调解申请书"]
    content: str                       # 填充后的文书内容
    gaps: List[str]                    # 高亮标注的缺失字段
    created_at: str
    updated_at: str


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
    current_step: int  # 1-10, current step
    completed_steps: set[int]          # 已完成步骤集合
    step_data: Dict[str, StepData]      # 每步采集的数据
    dirty_steps: set[int]               # 需重算的脏步骤

    # --- 案件核心 ---
    case_category: Optional[str]        # 6大分类之一（欠薪/开除/工伤/调岗/社保/其他）
    case_types: List[str]               # 案由列表（单一或组合）
    case_facts: Optional[str]           # AI生成的案件事实描述
    rights_list: List[RightItem]         # 权益清单
    risk_assessment: Optional[RiskAssessment]  # 风险提示

    # --- 证据体系 ---
    evidence_items: List[EvidenceItem]  # 证据清单
    evidence_files: Dict[str, FileRef]  # 上传文件引用

    # --- 文书 ---
    document_draft: Optional[DocumentDraft]  # 文书草稿

    # --- 元数据 ---
    session_id: str
    started_at: str                      # ISO格式
    last_updated: str                   # ISO格式
    member_id: Optional[str]            # 会员ID（登录后填充）
    resume_token: Optional[str]         # 断点恢复token


class ConsultationInput(TypedDict):
    """九步咨询系统输入状态（初始状态）"""
    messages: Annotated[List[Any], messages_add]
    session_id: str
    member_id: Optional[str] = None


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
        "case_types": [],
        "case_facts": None,
        "rights_list": [],
        "risk_assessment": None,
        "evidence_items": [],
        "evidence_files": {},
        "document_draft": None,
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
