from pydantic import BaseModel
from typing import List, Optional


class TestCase(BaseModel):
    title: str
    steps: List[str]
    expected_result: str
    type: str  # positive, negative, edge_case


class GenerateTestResponse(BaseModel):
    run_id: int
    filename: str
    total: int
    context_used: bool = False  # lets the caller know if context tuning was applied
    test_cases: List[TestCase]