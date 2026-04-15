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