"""
Artifact 5 — Runtime Admissibility Gate Schemas

These Pydantic models define the on-disk and in-memory
contract for:
  - JudgmentEvent: immutable gate decision records
  - ConstraintArtifact: fast-path memory keyed by runtime_context_hash

File Naming Conventions (O(1) Lookup):
  - judgment_event_{id}.json
  - constraint_{runtime_context_hash}.json

Alignment: Designed to match Artifact 4 style (BaseModel + Literal types).
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# -----------------------------------------------------------------------------
# Type Aliases (Core Gate Vocabulary)
# -----------------------------------------------------------------------------

Decision = Literal["ADMIT", "ESCALATE", "HALT"]
"""
Gate decision outcomes based on drift score thresholds (Fidel):
  - ADMIT:    s <= 0.3  → Allow execution, log as normal
  - ESCALATE: 0.3 < s <= 0.7 → Block (DEFER), do not execute, generate Judgment + Constraint
  - HALT:     s > 0.7  → Block (STOP), do not execute, generate Judgment + Constraint
"""

ReasonCode = Literal["DRIFT_THRESHOLD_EXCEEDED", "PRIOR_CONSTRAINT_MATCH"]
"""
Machine-readable reason for a gate decision:
  - DRIFT_THRESHOLD_EXCEEDED: Slow path triggered block via drift calculation
  - PRIOR_CONSTRAINT_MATCH:   Fast path triggered block via constraint memory lookup
"""

BlockMode = Literal["DEFER", "STOP"]
"""
Block mode semantics per spec:
  - DEFER: Used for ESCALATE decisions (requires human review before proceeding)
  - STOP:  Used for HALT decisions (immediate refusal, no execution)
"""


# -----------------------------------------------------------------------------
# Supporting Models
# -----------------------------------------------------------------------------

class PriorArtifactRef(BaseModel):
    """
    Lightweight reference to prior verification artifacts
    (e.g., ANSYS scenarios, Synopsys constraints, or earlier judgments).
    """
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"type": "ansys_scenario", "id": "as-001", "uri": "artifacts/ansys_scenario_001.json"}]}
    )

    type: str = Field(..., description="Artifact type, e.g., 'ansys_scenario', 'synopsys_constraint', 'judgment_event'")
    id: str = Field(..., description="Unique identifier of the referenced artifact")
    uri: Optional[str] = Field(default=None, description="Optional file path or URI to the artifact")


# -----------------------------------------------------------------------------
# Core Schemas
# -----------------------------------------------------------------------------

class JudgmentEvent(BaseModel):
    """
    Immutable record of a gate decision. Emitted for ADMIT, HALT, and ESCALATE.

    Spec Compliance (Section 4):
      - decision (ADMIT / HALT / ESCALATE)
      - timestamp
      - intent hash
      - runtime context hash
      - reference to prior verification artifacts
      - immutable ID

    File naming pattern: judgment_event_{id}.json
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [{
                "id": "je-001",
                "decision": "HALT",
                "timestamp": "2026-01-11T12:00:00Z",
                "intent_hash": "sha256:abc123...",
                "runtime_context_hash": "sha256:def456...",
                "drift_score": 0.85,
                "prior_artifact_refs": []
            }]
        }
    )

    # Immutable identifier — spec requirement: "immutable ID"
    id: str = Field(..., description="Immutable UUID for this judgment event")

    # Gate decision — spec requirement: "decision (ADMIT / HALT / ESCALATE)"
    decision: Decision = Field(..., description="Gate decision: ADMIT / ESCALATE / HALT")

    # When the judgment was made — spec requirement: "timestamp"
    timestamp: datetime = Field(..., description="UTC timestamp when the gate produced this judgment")

    # Hash of declared intent — spec requirement: "intent hash"
    intent_hash: str = Field(..., description="SHA256 hash of the declared intent")

    # Hash of runtime context — spec requirement: "runtime context hash"
    runtime_context_hash: str = Field(..., description="SHA256 hash of the runtime context")

    # Drift score (slow path only) — enhancement for traceability
    drift_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Calculated drift score (0.0-1.0), null if blocked via fast-path constraint lookup"
    )

    # Prior artifacts — spec requirement: "reference to prior verification artifacts"
    prior_artifact_refs: list[PriorArtifactRef] = Field(
        default_factory=list,
        description="References to prior verification artifacts (Artifact 4 outputs, etc.)"
    )

    def get_filename(self) -> str:
        """Returns the spec-compliant filename: judgment_event_{id}.json"""
        return f"judgment_event_{self.id}.json"


class ConstraintArtifact(BaseModel):
    """
    Fast-lookup constraint for the gate's memory-first path.
    Created when a JudgmentEvent results in HALT or ESCALATE.

    Spec Compliance (Section 5):
      - runtime_context_hash: Required (primary lookup key)
      - Proposed fields for blocked event context

    File naming pattern: constraint_{runtime_context_hash}.json
    This enables O(1) lookup — check if file exists for given hash.
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [{
                "runtime_context_hash": "sha256:def456...",
                "judgment_id": "je-001",
                "decision": "HALT",
                "block_mode": "STOP",
                "reason_code": "DRIFT_THRESHOLD_EXCEEDED",
                "reason_detail": "Drift score 0.85 exceeded HALT threshold (0.7)",
                "drift_score_at_block": 0.85,
                "created_at": "2026-01-11T12:00:00Z"
            }]
        }
    )

    # Primary lookup key — spec requirement (enables O(1) lookup)
    runtime_context_hash: str = Field(
        ...,
        description="Primary lookup key (SHA256 of runtime_context). File named by this hash for O(1) lookup."
    )

    # Link back to original judgment — proposed field per spec
    judgment_id: str = Field(..., description="ID of the JudgmentEvent that created this constraint")

    # The blocking decision (only HALT or ESCALATE create constraints)
    decision: Literal["HALT", "ESCALATE"] = Field(
        ...,
        description="The blocking decision (only HALT or ESCALATE, not ADMIT)"
    )

    # Action status — proposed field per spec ("e.g., the action status")
    block_mode: BlockMode = Field(
        ...,
        description="Block semantics: DEFER (requires review) or STOP (immediate refusal)"
    )

    # Reason for block — proposed field per spec ("the specific reason for the block")
    reason_code: ReasonCode = Field(
        ...,
        description="Machine-readable reason: DRIFT_THRESHOLD_EXCEEDED or PRIOR_CONSTRAINT_MATCH"
    )

    # Human-readable explanation — complements reason_code
    reason_detail: Optional[str] = Field(
        default=None,
        description="Human-readable explanation of why this request was blocked"
    )

    # Drift score at time of block — provides context for why it was blocked
    drift_score_at_block: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Drift score that triggered the block (if slow-path calculated)"
    )

    # Timestamp — proposed field per spec ("timestamps")
    created_at: datetime = Field(..., description="UTC timestamp when constraint was created")

    def get_filename(self) -> str:
        """Returns the spec-compliant filename: constraint_{runtime_context_hash}.json"""
        return f"constraint_{self.runtime_context_hash}.json"
