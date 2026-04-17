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
def select_option(runtime: ToolRuntime, options: List[str], question: str) -> Dict:
    """
    请求用户从选项列表中选择。

    重要：调用此工具后，你必须立即停止生成，不要替用户做选择。
    工具返回的是"等待用户输入"的状态标记，不是用户的选择结果。

    - options: 可选列表，如 ["劳动合同", "劳务合同", "实习合同"]
    - question: 向用户展示的问题文字

    返回值说明：
    - type: "awaiting_user_input" 表示正在等待用户选择
    - display: 前端渲染用的格式化字符串
    """
    import json as _json

    # 返回结构化数据，明确标记为"等待用户输入"
    return {
        "type": "awaiting_user_input",
        "component": "select_option",
        "question": question,
        "options": options,
        "instruction": "⚠️ 等待用户选择中，请勿继续生成内容或替用户做决定。"
    }


@tool
def text_input(
    runtime: ToolRuntime,
    question: str,
    placeholder: str = "",
    multiline: bool = False,
) -> Dict:
    """
    请求用户输入文本。

    重要：调用此工具后，你必须立即停止生成，等待用户输入。

    - question: 向用户展示的问题文字
    - placeholder: 输入框占位提示
    - multiline: 是否允许多行输入
    """
    return {
        "type": "awaiting_user_input",
        "component": "text_input",
        "question": question,
        "placeholder": placeholder,
        "multiline": multiline,
        "instruction": "⚠️ 等待用户输入文本中，请勿继续生成内容或替用户回答。"
    }


@tool
def date_picker(runtime: ToolRuntime, question: str) -> Dict:
    """
    请求用户选择日期。

    重要：调用此工具后，你必须立即停止生成，等待用户选择日期。

    - question: 向用户展示的问题文字
    """
    return {
        "type": "awaiting_user_input",
        "component": "date_picker",
        "question": question,
        "instruction": "⚠️ 等待用户选择日期中，请勿继续生成内容或替用户填写。"
    }


@tool
def number_input(
    runtime: ToolRuntime,
    question: str,
    min_value: float = 0,
    max_value: float = 999999999,
    unit: str = "",
) -> Dict:
    """
    请求用户输入数字。

    重要：调用此工具后，你必须立即停止生成，等待用户输入。

    - question: 向用户展示的问题文字
    - min_value: 最小值
    - max_value: 最大值
    - unit: 单位，如 "元"、"天" 等
    """
    return {
        "type": "awaiting_user_input",
        "component": "number_input",
        "question": question,
        "min": min_value,
        "max": max_value,
        "unit": unit,
        "instruction": "⚠️ 等待用户输入数字中，请勿继续生成内容或替用户填写。"
    }
