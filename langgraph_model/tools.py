from langchain.tools import tool, ToolRuntime
from typing import List, Dict
# ============================================================================
# 权益计算工具
# ============================================================================

def calculate_unpaid_wage(months: int, monthly_wage: float) -> Dict:
    """计算欠薪金额"""
    amount = months * monthly_wage
    return {
        "right_name": "欠发工资",
        "amount": amount,
        "calculation_basis": f"{months}个月 × {monthly_wage}元/月",
        "legal_basis": "《劳动合同法》第30条",
        "priority": 1,
    }


def calculate_illegal_dismissal_n(months_employed: int, avg_monthly_wage: float) -> Dict:
    """计算违法解除劳动合同赔偿金 2N"""
    # 工作年限不足半年按0.5年计算，超过半年不足一年按1年计算
    years = months_employed / 12
    n = years
    if n > 12:
        n = 12  # 最高不超过12年
    amount = n * 2 * avg_monthly_wage
    return {
        "right_name": "违法解除劳动合同赔偿金（2N）",
        "amount": amount,
        "calculation_basis": f"工作年限{n:.1f}年 × 2 × {avg_monthly_wage}元",
        "legal_basis": "《劳动合同法》第87条",
        "priority": 1,
    }


def calculate_economic_compensation(months_employed: int, avg_monthly_wage: float) -> Dict:
    """计算经济补偿金 N"""
    years = months_employed / 12
    n = years
    if n > 12:
        n = 12
    amount = n * avg_monthly_wage
    return {
        "right_name": "经济补偿金（N）",
        "amount": amount,
        "calculation_basis": f"工作年限{n:.1f}年 × {avg_monthly_wage}元",
        "legal_basis": "《劳动合同法》第47条",
        "priority": 1,
    }




# ============================================================================
# 交互类工具（generate-ui 组件生成）
# ============================================================================

@tool
def select_option(runtime: ToolRuntime, options: List[str], question: str) -> str:
    """
    请求用户从选项列表中选择。
    - options: 可选列表，如 ["劳动合同", "劳务合同", "实习合同"]
    - question: 向用户展示的问题文字
    返回格式化的选择提示，供前端渲染为选择按钮组件。
    """
    import json as _json
    payload = _json.dumps({
        "component": "select_option",
        "question": question,
        "options": options,
    })
    return f"[SELECT_OPTION]{payload}[/SELECT_OPTION]"


@tool
def text_input(
    runtime: ToolRuntime,
    question: str,
    placeholder: str = "",
    multiline: bool = False,
) -> str:
    """
    请求用户输入文本。
    - question: 向用户展示的问题文字
    - placeholder: 输入框占位提示
    - multiline: 是否允许多行输入
    返回格式化的文本输入提示，供前端渲染为文本输入组件。
    """
    import json as _json
    payload = _json.dumps({
        "component": "text_input",
        "question": question,
        "placeholder": placeholder,
        "multiline": multiline,
    })
    return f"[TEXT_INPUT]{payload}[/TEXT_INPUT]"


@tool
def date_picker(runtime: ToolRuntime, question: str) -> str:
    """
    请求用户选择日期。
    - question: 向用户展示的问题文字
    返回格式化的日期选择提示，供前端渲染为日期选择器组件。
    """
    import json as _json
    payload = _json.dumps({
        "component": "date_picker",
        "question": question,
    })
    return f"[DATE_PICKER]{payload}[/DATE_PICKER]"


@tool
def number_input(
    runtime: ToolRuntime,
    question: str,
    min_value: float = 0,
    max_value: float = 999999999,
    unit: str = "",
) -> str:
    """
    请求用户输入数字。
    - question: 向用户展示的问题文字
    - min_value: 最小值
    - max_value: 最大值
    - unit: 单位，如 "元"、"天" 等
    返回格式化的数字输入提示，供前端渲染为数字输入组件。
    """
    import json as _json
    payload = _json.dumps({
        "component": "number_input",
        "question": question,
        "min": min_value,
        "max": max_value,
        "unit": unit,
    })
    return f"[NUMBER_INPUT]{payload}[/NUMBER_INPUT]"
