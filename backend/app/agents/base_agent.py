from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseAgent(ABC):
    def __init__(self, llm):
        self.llm = llm

    @abstractmethod
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Agent"""
        pass

    def _format_output(self, result: str) -> Dict[str, Any]:
        """格式化输出"""
        return {"result": result, "status": "success"}