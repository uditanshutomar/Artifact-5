"""
Artifact 5 — Runtime Admissibility Gate Schemas

These Pydantic models define the on-disk and in-memory
contract for:
  - JudgmentEvent: immutable gate decision records
  - ConstraintArtifact: fast-path memory keyed by runtime_context_hash

File Naming Conventions:
  - judgment_event_{id}.json
  - constraint_{runtime_context_hash}.json (enables O(1) lookup)

Alignment: Designed to match Artifact 4 style (BaseModel + Literal types).
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Type Aliases (Core Gate Vocabulary)
# -----------------------------------------------------------------------------

Decision = Literal["ADMIT", "ESCALATE", "HALT"]
"""
Gate decision outcomes based on drift score thresholds:
  - ADMIT:    s <= 0.3  → Allow execution
  - ESCALATE: 0.3 < s <= 0.7 → Block (defer), requires review
  - HALT:     s > 0.7  → Block (stop), immediate refusal
"""

ReasonCode = Literal["DRIFT_THRESHOLD_EXCEEDED", "PRIOR_CONSTRAINT_MATCH"]
"""
Machine-readable reason for a gate decision:
  - DRIFT_THRESHOLD_EXCEEDED: Slow path triggered block via drift calculation
  - PRIOR_CONSTRAINT_MATCH:   Fast path triggered block via constraint lookup
"""

BlockMode = Literal["DEFER", "STOP"]
"""
Block mode semantics per spec:
  - DEFER: Used for ESCALATE decisions (requires human review)
  - STOP:  Used for HALT decisions (immediate refusal)
"""


# -----------------------------------------------------------------------------
# Supporting Models
# -----------------------------------------------------------------------------

class PriorArtifactRef(BaseModel):
    """
    Lightweight reference to prior verification artifacts
    (e.g., ANSYS scenarios, Synopsys constraints, or earlier judgments).
    """

    type: str = Field(..., description="Artifact type, e.g., 'ansys_scenario', 'synopsys_constraint', 'judgment_event'")
    id: str = Field(..., description="Unique identifier of the referenced artifact")
    uri: Optional[str] = Field(default=None, description="Optional file path or URI to the artifact")


# -----------------------------------------------------------------------------
# Core Schemas
# -----------------------------------------------------------------------------

class JudgmentEvent(BaseModel):
    """
    Immutable record of a gate decision. Emitted for ADMIT, HALT, and ESCALATE.

    File naming pattern: judgment_event_{id}.json
    """

    id: str = Field(..., description="Immutable UUID for this judgment event")
    decision: Decision = Field(..., description="Gate decision: ADMIT / ESCALATE / HALT")
    timestamp: datetime = Field(..., description="UTC timestamp when the gate produced this judgment")
    intent_hash: str = Field(..., description="SHA256 hash of the declared intent")
    runtime_context_hash: str = Field(..., description="SHA256 hash of the runtime context")
    drift_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Calculated drift score (0.0-1.0), null if fast-path blocked")
    prior_artifact_refs: list[PriorArtifactRef] = Field(default_factory=list, description="References to prior verification artifacts")


class ConstraintArtifact(BaseModel):
    """
    Fast-lookup constraint for the gate's memory-first path.
    Created when a JudgmentEvent results in HALT or ESCALATE.

    File naming pattern: constraint_{runtime_context_hash}.json
    Enables O(1) lookup by checking if file exists for a given hash.
    """

    runtime_context_hash: str = Field(..., description="Primary lookup key (SHA256 of runtime_context)")
    judgment_id: str = Field(..., description="ID of the JudgmentEvent that created this constraint")
    decision: Literal["HALT", "ESCALATE"] = Field(..., description="The blocking decision (HALT or ESCALATE only)")
    block_mode: BlockMode = Field(..., description="Block semantics: DEFER (review) or STOP (refuse)")
    reason_code: ReasonCode = Field(..., description="Machine-readable reason for the block")
    reason_detail: Optional[str] = Field(default=None, description="Human-readable explanation of why blocked")
    drift_score_at_block: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Drift score that triggered the block")
    created_at: datetime = Field(..., description="UTC timestamp when constraint was created")
