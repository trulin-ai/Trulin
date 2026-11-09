"""
Predicate Registry Service.

Provides versioned, document-agnostic validation of predicates, role constraints,
default modalities, and risk levels loaded from the JSON taxonomy.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


class PredicateDefinition(BaseModel):
    predicate_id: str
    label: str
    action_category: str
    allowed_subject_roles: List[str] = Field(default_factory=lambda: ["ANY_PARTY"])
    allowed_object_roles: List[str] = Field(default_factory=lambda: ["ANY_OBJECT"])
    default_modality: str = "MUST"
    requires_condition: bool = False
    risk_level: str = "MEDIUM"


class PredicateRegistryService:
    """Singleton service accessing the versioned predicate taxonomy."""

    _instance: Optional["PredicateRegistryService"] = None
    _predicates: Dict[str, PredicateDefinition] = {}
    _banned: Set[str] = set()
    _version: str = "1.0.0"

    def __init__(self, json_path: Optional[Path] = None):
        if not json_path:
            json_path = Path(__file__).resolve().parent / "predicates.v1.json"
        self._load(json_path)

    def _load(self, json_path: Path) -> None:
        if not json_path.exists():
            return
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._version = data.get("version", "1.0.0")
        self._banned = set(p.lower() for p in data.get("banned_generic_predicates", []))
        self._predicates = {}
        for entry in data.get("predicates", []):
            defn = PredicateDefinition(**entry)
            self._predicates[defn.predicate_id.lower()] = defn

    @classmethod
    def get_instance(cls) -> "PredicateRegistryService":
        if cls._instance is None:
            cls._instance = PredicateRegistryService()
        return cls._instance

    @classmethod
    def get_predicate(cls, predicate_id: str) -> Optional[PredicateDefinition]:
        return cls.get_instance()._predicates.get((predicate_id or "").strip().lower())

    @classmethod
    def is_banned(cls, predicate_id: str) -> bool:
        pid = (predicate_id or "").strip().lower()
        inst = cls.get_instance()
        if pid in inst._banned:
            return True
        return any(b in pid for b in inst._banned)

    @classmethod
    def exists(cls, predicate_id: str) -> bool:
        pid = (predicate_id or "").strip().lower()
        if pid in cls.get_instance()._predicates:
            return True
        try:
            from app.extraction.predicate_registry import PredicateRegistry
            return PredicateRegistry.is_canonical(pid)
        except Exception:
            return False

    @classmethod
    def validate_roles(
        cls,
        predicate_id: str,
        subject_role: Optional[str] = None,
        object_role: Optional[str] = None,
    ) -> bool:
        """Verifies if subject and object roles are semantically allowed for this predicate."""
        defn = cls.get_predicate(predicate_id)
        if not defn:
            return False

        if subject_role:
            s_role = subject_role.upper()
            if "ANY_PARTY" not in defn.allowed_subject_roles and s_role not in defn.allowed_subject_roles:
                return False

        if object_role:
            o_role = object_role.upper()
            if "ANY_OBJECT" not in defn.allowed_object_roles and o_role not in defn.allowed_object_roles:
                return False

        return True
