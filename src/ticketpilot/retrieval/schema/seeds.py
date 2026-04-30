"""Seed data loaders for FAQ, Policy, and Case documents."""

import json
from pathlib import Path

from ticketpilot.retrieval.schema.knowledge import (
    CaseDocument,
    FAQDocument,
    PolicyDocument,
)

_SEED_DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "knowledge"


def _load_json_file(filename: str) -> list[dict]:
    """Load JSON file from data/knowledge directory."""
    file_path = _SEED_DATA_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Seed data file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_faq_seed_data() -> list[FAQDocument]:
    """Load FAQ seed data from JSON file."""
    data = _load_json_file("faq_seed.json")
    return [FAQDocument(**item) for item in data]


def load_policy_seed_data() -> list[PolicyDocument]:
    """Load Policy seed data from JSON file."""
    data = _load_json_file("policy_seed.json")
    return [PolicyDocument(**item) for item in data]


def load_case_seed_data() -> list[CaseDocument]:
    """Load Case seed data from JSON file."""
    data = _load_json_file("case_seed.json")
    return [CaseDocument(**item) for item in data]


def load_seed_data() -> tuple[list[FAQDocument], list[PolicyDocument], list[CaseDocument]]:
    """Load all seed data files."""
    return (
        load_faq_seed_data(),
        load_policy_seed_data(),
        load_case_seed_data(),
    )
