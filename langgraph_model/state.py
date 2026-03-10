from typing import Dict, TypedDict, List, Tuple, Optional, Annotated
import operator
from langchain.messages import AnyMessage

# 定义状态类型
class AgentState(TypedDict):
    messages:Annotated[list[AnyMessage], operator.add]
    # selected_scenario: Optional[str]=None
    # selected_solution: Optional[str]=None
    # agent_responses: Dict[str, str]  # 存储每个agent的响应
    next_node:Optional[str]=None

class InputState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]