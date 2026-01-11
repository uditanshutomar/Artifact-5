"""
Artifact 5 — Runtime Admissibility Gate Schemas

These Pydantic models define the on-disk and in-memory
contract for:
  - JudgmentEvent: immutable gate decision records
  - ConstraintArtifact: fast-path memory keyed by runtime_context_hash

They are designed to align with the style used in Artifact 4
(`schemas.py` with simple BaseModel subclasses and Literal types).
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


Decision = Literal["ADMIT", "ESCALATE", "HALT"]
ReasonCode = Literal["DRIFT_THRESHOLD_EXCEEDED", "PRIOR_CONSTRAINT_MATCH"]


class PriorArtifactRef(BaseModel):
    """
    Lightweight reference to prior verification artifacts
    (e.g., ANSYS scenarios, Synopsys constraints, or earlier judgments).
    """

    type: str
    id: str
    uri: Optional[str] = None


class JudgmentEvent(BaseModel):
    """
    Immutable record of a gate decision.

    Intended filename pattern:
      judgment_event_{id}.json
    """

    # Immutable identifier for this judgment event (e.g., UUID).
    id: str

    # ADMIT / ESCALATE / HALT
    decision: Decision

    # UTC timestamp when the gate produced this judgment.
    timestamp: datetime

    # Hashes that anchor this judgment to intent and runtime context
    intent_hash: str
    runtime_context_hash: str

    # References back into prior artifacts (Artifact 4, simulations, constraints, etc.)
    prior_artifact_refs: list[PriorArtifactRef] = []


class ConstraintArtifact(BaseModel):
    """
    Lightweight, fast-lookup constraint used for the gate's memory-first path.

    Intended filename pattern:
      constraint_{runtime_context_hash}.json
    """

    # Primary lookup key derived from the runtime_context payload.
    runtime_context_hash: str

    # ID of the JudgmentEvent that created this constraint.
    judgment_id: str

    # Decision that resulted in this constraint being created.
    decision: Literal["HALT", "ESCALATE"]

    # Machine-readable reason for the block.
    reason_code: ReasonCode

    # Optional human-readable explanation.
    reason_detail: Optional[str] = None

    # Drift score that triggered the block (if applicable).
    drift_score_at_block: Optional[float] = None

    # When the constraint was created.
    created_at: datetime
