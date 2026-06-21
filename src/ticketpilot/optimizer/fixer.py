"""Fixer — applies targeted fixes based on diagnostic findings.

Supports:
- Confidence threshold adjustments (L1)
- Intent keyword additions (L2)
- Risk keyword additions (L2)

All modifications are backed up before writing and can be rolled back.
Dry-run mode logs intended changes without writing files.
"""

from __future__ import annotations

import importlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ticketpilot.optimizer.config import PROJECT_ROOT


# ---------------------------------------------------------------------------
# Fix result
# ---------------------------------------------------------------------------


@dataclass
class FixResult:
    """Outcome of applying a single fix."""

    success: bool
    fix_type: str  # key from FIX_PRIORITY
    description: str
    files_modified: list[str] = field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# File paths for rules (absolute, resolved at import time)
# ---------------------------------------------------------------------------

_CONFIG_INIT_PATH = PROJECT_ROOT / "src" / "ticketpilot" / "config" / "__init__.py"
_CLASSIFICATION_RULES_PATH = (
    PROJECT_ROOT / "src" / "ticketpilot" / "classification" / "rules.py"
)
_RISK_RULES_PATH = PROJECT_ROOT / "src" / "ticketpilot" / "risk" / "rules.py"


# ---------------------------------------------------------------------------
# Helper: find the source file for a runtime module
# ---------------------------------------------------------------------------


def _module_path(module_name: str) -> Path:
    """Return the __file__ path of a loaded module."""
    mod = importlib.import_module(module_name)
    return Path(mod.__file__).resolve()


# ---------------------------------------------------------------------------
# Fixer
# ---------------------------------------------------------------------------


class Fixer:
    """Applies targeted fixes with backup and rollback support."""

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self._original_contents: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply_fix(self, diagnosis: Any) -> FixResult:
        """Apply the fix implied by *diagnosis*.

        Routes to the specific fix method based on ``diagnosis.suggested_fix_type``.
        """
        fix_type = getattr(diagnosis, "suggested_fix_type", None)
        if fix_type is None:
            return FixResult(
                success=False,
                fix_type="unknown",
                description="Diagnosis has no suggested_fix_type",
                error="missing suggested_fix_type",
            )

        dispatch = {
            "confidence_threshold": self._fix_confidence_threshold,
            "confidence_weight": self._fix_confidence_threshold,
            "intent_keyword": self._fix_intent_keywords,
            "risk_keyword": self._fix_risk_keywords,
            "exclusion_rule": self._fix_exclusion_rule,  # NEW
        }

        handler = dispatch.get(fix_type)
        if handler is None:
            return FixResult(
                success=False,
                fix_type=fix_type,
                description=f"No handler for fix type '{fix_type}'",
                error=f"unsupported fix type: {fix_type}",
            )

        try:
            return handler(diagnosis)
        except Exception as exc:  # noqa: BLE001
            return FixResult(
                success=False,
                fix_type=fix_type,
                description=f"Exception while applying {fix_type}",
                error=str(exc),
            )

    def apply_fix_keyword(self, intent: str, keyword: str) -> FixResult:
        """Directly add a keyword to an intent rule without a full Diagnosis object.

        Uses a duck-type mini-diagnosis to reuse the existing _fix_intent_keywords method.
        """

        class _MiniDiagnosis:
            expected_values = {"intent": intent}
            suggested_keywords = [keyword]
            suggested_fix_type = "intent_keyword"
            type = "intent_keyword"

        return self._fix_intent_keywords(_MiniDiagnosis())

    def rollback(self) -> None:
        """Restore all previously modified files to their original content."""
        for path, content in self._original_contents.items():
            p = Path(path)
            if p.exists():
                p.write_text(content, encoding="utf-8")
        self._original_contents.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _backup_file(self, path: str) -> None:
        """Read and store the original content of *path* before modification."""
        if path not in self._original_contents:
            p = Path(path)
            if p.is_file():
                self._original_contents[path] = p.read_text(encoding="utf-8")

    def _write_file(self, path: str, content: str) -> None:
        """Write *content* to *path*, respecting dry_run."""
        if self.dry_run:
            return  # dry-run: do not touch disk
        Path(path).write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------
    # L1: Confidence threshold fix
    # ------------------------------------------------------------------

    def _fix_confidence_threshold(self, diagnosis: Any) -> FixResult:
        """Adjust a confidence threshold in config/__init__.py.

        ``diagnosis.expected_values`` should contain:
            - ``"threshold_name"``: the Python variable name (e.g. ``"CONFIDENCE_MEDIUM"``)
            - ``"new_value"``: the desired float value
        """
        threshold_name = diagnosis.expected_values.get("threshold_name")
        new_value = diagnosis.expected_values.get("new_value")

        if threshold_name is None or new_value is None:
            return FixResult(
                success=False,
                fix_type="confidence_threshold",
                description="Missing threshold_name or new_value in expected_values",
                error="expected_values must contain 'threshold_name' and 'new_value'",
            )

        file_path = str(_CONFIG_INIT_PATH)
        self._backup_file(file_path)

        if self.dry_run:
            return FixResult(
                success=True,
                fix_type="confidence_threshold",
                description=f"[dry-run] Would set {threshold_name} = {new_value}",
                files_modified=[file_path],
            )

        source = Path(file_path).read_text(encoding="utf-8")

        # Replace the assignment line:  CONFIDENCE_FOO = <value>
        pattern = rf"(^{threshold_name}\s*=\s*)(.+)$"
        replacement = rf"\g<1>{new_value}"
        new_source, count = re.subn(pattern, replacement, source, flags=re.MULTILINE)

        if count == 0:
            return FixResult(
                success=False,
                fix_type="confidence_threshold",
                description=f"Variable '{threshold_name}' not found in config",
                error=f"'{threshold_name}' not found in {file_path}",
            )

        self._write_file(file_path, new_source)

        return FixResult(
            success=True,
            fix_type="confidence_threshold",
            description=f"Set {threshold_name} = {new_value} (was dynamic)",
            files_modified=[file_path],
        )

    # ------------------------------------------------------------------
    # L2: Intent keyword fix
    # ------------------------------------------------------------------

    def _fix_intent_keywords(self, diagnosis: Any) -> FixResult:
        """Add keywords to an IntentRule in classification/rules.py.

        ``diagnosis.expected_values`` should contain:
            - ``"intent"``: the intent enum value (e.g. ``"REFUND"``)
        ``diagnosis.suggested_keywords`` is a list of strings to add.
        """
        intent_value = diagnosis.expected_values.get("intent")
        keywords = getattr(diagnosis, "suggested_keywords", [])

        if not intent_value:
            return FixResult(
                success=False,
                fix_type="intent_keyword",
                description="Missing 'intent' in expected_values",
                error="expected_values must contain 'intent'",
            )

        if not keywords:
            return FixResult(
                success=False,
                fix_type="intent_keyword",
                description="No keywords to add",
                error="suggested_keywords is empty",
            )

        file_path = str(_CLASSIFICATION_RULES_PATH)
        self._backup_file(file_path)

        if self.dry_run:
            return FixResult(
                success=True,
                fix_type="intent_keyword",
                description=f"[dry-run] Would add {keywords!r} to {intent_value} rule",
                files_modified=[file_path],
            )

        source = Path(file_path).read_text(encoding="utf-8")

        # Strategy: find the IntentRule block for the given intent and append keywords.
        # We look for the pattern:  keywords=[ ... ],
        # inside the IntentRule that has  intent=IntentClass.<INTENT>,
        #
        # Step 1: Locate the IntentRule block for the target intent.
        # Convert to uppercase to match Python enum convention (PRODUCT_CONSULTING vs product_consulting)
        intent_enum_value = intent_value.upper()
        intent_pattern = rf"intent=IntentClass\.{intent_enum_value}\b"
        intent_match = re.search(intent_pattern, source)
        if not intent_match:
            return FixResult(
                success=False,
                fix_type="intent_keyword",
                description=f"IntentClass.{intent_value} not found in rules",
                error=f"intent '{intent_value}' not found in {file_path}",
            )

        # Step 2: From the intent match position, find the keywords=[...] block.
        # Search forward from the intent match for "keywords=["
        search_start = intent_match.start()
        kw_list_pattern = r"keywords=\[(.*?)\]"
        kw_match = re.search(kw_list_pattern, source[search_start:], re.DOTALL)

        if not kw_match:
            return FixResult(
                success=False,
                fix_type="intent_keyword",
                description="Could not locate keywords list for the intent rule",
                error="keywords=[...] not found near intent definition",
            )

        # Step 3: Parse existing keywords from the match.
        kw_body = kw_match.group(1).strip()
        existing: list[str] = []
        if kw_body:
            existing = [m.group(1) for m in re.finditer(r'"([^"]+)"', kw_body)]

        # Filter out already-present keywords
        new_only = [kw for kw in keywords if kw not in existing]
        if not new_only:
            return FixResult(
                success=True,
                fix_type="intent_keyword",
                description=f"All keywords already present in {intent_value}",
                files_modified=[file_path],
            )

        # Step 4: Build the new keywords list string.
        all_keywords = existing + new_only
        kw_entries = ", ".join(f'"{kw}"' for kw in all_keywords)
        new_kw_block = f"keywords=[{kw_entries}]"

        # Step 5: Replace in source.
        abs_start = search_start + kw_match.start()
        abs_end = search_start + kw_match.end()
        new_source = source[:abs_start] + new_kw_block + source[abs_end:]

        self._write_file(file_path, new_source)

        return FixResult(
            success=True,
            fix_type="intent_keyword",
            description=f"Added {len(new_only)} keyword(s) to {intent_value}: {new_only}",
            files_modified=[file_path],
        )

    # ------------------------------------------------------------------
    # L2: Risk keyword fix
    # ------------------------------------------------------------------

    def _fix_risk_keywords(self, diagnosis: Any) -> FixResult:
        """Add keywords to a RiskRule in risk/rules.py.

        ``diagnosis.expected_values`` should contain:
            - ``"risk_flag"``: the RiskFlag enum value (e.g. ``"COMPLAINT_RISK"``)
        ``diagnosis.suggested_keywords`` is a list of strings to add.
        """
        risk_flag = diagnosis.expected_values.get("risk_flag")
        keywords = getattr(diagnosis, "suggested_keywords", [])

        if not risk_flag:
            return FixResult(
                success=False,
                fix_type="risk_keyword",
                description="Missing 'risk_flag' in expected_values",
                error="expected_values must contain 'risk_flag'",
            )

        if not keywords:
            return FixResult(
                success=False,
                fix_type="risk_keyword",
                description="No keywords to add",
                error="suggested_keywords is empty",
            )

        file_path = str(_RISK_RULES_PATH)
        self._backup_file(file_path)

        if self.dry_run:
            return FixResult(
                success=True,
                fix_type="risk_keyword",
                description=f"[dry-run] Would add {keywords!r} to {risk_flag} rule",
                files_modified=[file_path],
            )

        source = Path(file_path).read_text(encoding="utf-8")

        # Locate the RiskRule block for the target flag.
        flag_pattern = rf"flag=RiskFlag\.{risk_flag}\b"
        flag_match = re.search(flag_pattern, source)
        if not flag_match:
            return FixResult(
                success=False,
                fix_type="risk_keyword",
                description=f"RiskFlag.{risk_flag} not found in rules",
                error=f"risk_flag '{risk_flag}' not found in {file_path}",
            )

        # Find the keywords=[...] block after the flag definition.
        search_start = flag_match.start()
        kw_list_pattern = r"keywords=\[(.*?)\]"
        kw_match = re.search(kw_list_pattern, source[search_start:], re.DOTALL)

        if not kw_match:
            return FixResult(
                success=False,
                fix_type="risk_keyword",
                description="Could not locate keywords list for the risk rule",
                error="keywords=[...] not found near flag definition",
            )

        # Parse existing keywords.
        kw_body = kw_match.group(1).strip()
        existing: list[str] = []
        if kw_body:
            existing = [m.group(1) for m in re.finditer(r'"([^"]+)"', kw_body)]

        # Filter out already-present keywords.
        new_only = [kw for kw in keywords if kw not in existing]
        if not new_only:
            return FixResult(
                success=True,
                fix_type="risk_keyword",
                description=f"All keywords already present in {risk_flag}",
                files_modified=[file_path],
            )

        # Build new keywords list.
        all_keywords = existing + new_only
        kw_entries = ", ".join(f'"{kw}"' for kw in all_keywords)
        new_kw_block = f"keywords=[{kw_entries}]"

        abs_start = search_start + kw_match.start()
        abs_end = search_start + kw_match.end()
        new_source = source[:abs_start] + new_kw_block + source[abs_end:]

        self._write_file(file_path, new_source)

        return FixResult(
            success=True,
            fix_type="risk_keyword",
            description=f"Added {len(new_only)} keyword(s) to {risk_flag}: {new_only}",
            files_modified=[file_path],
        )

    # ------------------------------------------------------------------
    # L2: Exclusion rule fix
    # ------------------------------------------------------------------

    def _fix_exclusion_rule(self, diagnosis: Any) -> FixResult:
        """Add exclusion keywords to a high-priority IntentRule.

        Used when COMPLAINT cases are being absorbed by higher-priority
        rules like REFUND or RETURN_EXCHANGE due to first-match-wins.

        ``diagnosis.expected_values`` should contain:
            - ``"intent"``: the intent whose exclusion list to modify (e.g. "REFUND")
            - ``"predicted_intent"``: the intent that's incorrectly matching
        ``diagnosis.suggested_keywords``: keywords to add as exclusions.
        """
        intent_value = diagnosis.expected_values.get("intent")
        predicted_intent = diagnosis.expected_values.get("predicted_intent", "")
        keywords = getattr(diagnosis, "suggested_keywords", [])

        if not intent_value:
            return FixResult(
                success=False,
                fix_type="exclusion_rule",
                description="Missing 'intent' in expected_values",
                error="expected_values must contain 'intent'",
            )

        if not keywords:
            return FixResult(
                success=False,
                fix_type="exclusion_rule",
                description="No exclusion keywords to add",
                error="suggested_keywords is empty",
            )

        file_path = str(_CLASSIFICATION_RULES_PATH)
        self._backup_file(file_path)

        if self.dry_run:
            return FixResult(
                success=True,
                fix_type="exclusion_rule",
                description=f"[dry-run] Would add exclusions {keywords!r} to {intent_value} rule",
                files_modified=[file_path],
            )

        source = Path(file_path).read_text(encoding="utf-8")

        # 定位目标 intent 的 IntentRule
        # 我们找的是 predicted_intent 所在的高优先级规则块
        # 因为 COMPLAINT 被 REFUND 抢走时，需要修改 REFUND 的 exclusions
        target_intent = predicted_intent if predicted_intent else intent_value

        intent_pattern = rf"intent=IntentClass\.{target_intent}\b"
        intent_match = re.search(intent_pattern, source)
        if not intent_match:
            return FixResult(
                success=False,
                fix_type="exclusion_rule",
                description=f"IntentClass.{target_intent} not found in rules",
                error=f"intent '{target_intent}' not found in {file_path}",
            )

        search_start = intent_match.start()

        # 检查是否已经有 exclusions 字段
        excl_pattern = r"exclusions=\[(.*?)\]"
        excl_match = re.search(excl_pattern, source[search_start:], re.DOTALL)

        if excl_match:
            # 已有 exclusions，追加
            excl_body = excl_match.group(1).strip()
            existing_excl: list[str] = []
            if excl_body:
                existing_excl = [
                    m.group(1) for m in re.finditer(r'"([^"]+)"', excl_body)
                ]
            new_only = [kw for kw in keywords if kw not in existing_excl]
            if not new_only:
                return FixResult(
                    success=True,
                    fix_type="exclusion_rule",
                    description=f"All exclusions already present in {target_intent}",
                    files_modified=[file_path],
                )
            all_excl = existing_excl + new_only
            excl_entries = ", ".join(f'"{kw}"' for kw in all_excl)
            new_excl_block = f"exclusions=[{excl_entries}]"

            abs_start = search_start + excl_match.start()
            abs_end = search_start + excl_match.end()
            new_source = source[:abs_start] + new_excl_block + source[abs_end:]
        else:
            # 没有 exclusions 字段，在 keywords 列表之后插入
            # 注意：这个 regex 假设 IntentRule 的 keywords= 后面跟逗号和其他字段
            # 即 format 为 keywords=[...],\n       其他字段
            # 如果 rules.py 格式变化（如末尾字段无逗号），需要调整此 regex
            kw_list_pattern = r"keywords=\[(.*?)\](.*?,)"
            kw_match = re.search(kw_list_pattern, source[search_start:], re.DOTALL)
            if not kw_match:
                return FixResult(
                    success=False,
                    fix_type="exclusion_rule",
                    description="Could not locate keywords list",
                    error="keywords=[...] not found",
                )

            kw_end = search_start + kw_match.end()
            excl_entries = ", ".join(f'"{kw}"' for kw in keywords)
            insertion = f",\n        exclusions=[{excl_entries}],"

            # 找到 keywords 行后面的内容插入位置
            new_source = source[:kw_end] + insertion + source[kw_end:]

        self._write_file(file_path, new_source)

        return FixResult(
            success=True,
            fix_type="exclusion_rule",
            description=f"Added {len(keywords)} exclusion(s) to {target_intent}: {keywords}",
            files_modified=[file_path],
        )
