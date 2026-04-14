import yaml
from pathlib import Path
from typing import List, Dict, Any

class KnowledgeLoader:
    def __init__(self, data_dir: str = "backend/data"):
        self.data_dir = Path(data_dir)

    def load_causes(self) -> List[Dict[str, Any]]:
        """加载案由知识"""
        causes = []
        causes_dir = self.data_dir / "causes"
        for file in causes_dir.glob("*.yaml"):
            with open(file, encoding="utf-8") as f:
                causes.append(yaml.safe_load(f))
        return causes

    def load_templates(self) -> List[Dict[str, Any]]:
        """加载文书模板"""
        templates = []
        templates_dir = self.data_dir / "templates"
        for file in templates_dir.glob("*.yaml"):
            with open(file, encoding="utf-8") as f:
                templates.append(yaml.safe_load(f))
        return templates

    def load_evidence_knowledge(self) -> List[Dict[str, Any]]:
        """加载证据知识"""
        evidence = []
        evidence_dir = self.data_dir / "evidence"
        for file in evidence_dir.glob("*.yaml"):
            with open(file, encoding="utf-8") as f:
                evidence.append(yaml.safe_load(f))
        return evidence

    def load_risk_knowledge(self) -> List[Dict[str, Any]]:
        """加载风险知识"""
        risks = []
        risks_dir = self.data_dir / "risks"
        for file in risks_dir.glob("*.yaml"):
            with open(file, encoding="utf-8") as f:
                risks.append(yaml.safe_load(f))
        return risks
