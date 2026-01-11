# Artifact 5 — Runtime Admissibility Gate Schemas

Pydantic schemas for the Runtime Admissibility Gate, defining immutable judgment records and fast-lookup constraint artifacts.

## Schemas

| Schema | Purpose | File Pattern |
|--------|---------|--------------|
| `JudgmentEvent` | Immutable gate decision record | `judgment_event_{id}.json` |
| `ConstraintArtifact` | Fast-path memory for O(1) lookup | `constraint_{runtime_context_hash}.json` |

## Decision Thresholds

| Drift Score | Decision | Block Mode |
|-------------|----------|------------|
| `s ≤ 0.3` | ADMIT | — |
| `0.3 < s ≤ 0.7` | ESCALATE | DEFER |
| `s > 0.7` | HALT | STOP |

## Installation

```bash
pip install pydantic
```

## Usage

```python
from artifact_5_schemas import JudgmentEvent, ConstraintArtifact

# Create a judgment event
judgment = JudgmentEvent(
    id="je-001",
    decision="HALT",
    timestamp=datetime.now(timezone.utc),
    intent_hash="sha256...",
    runtime_context_hash="sha256...",
    drift_score=0.85
)

# Create a constraint (on HALT/ESCALATE)
constraint = ConstraintArtifact(
    runtime_context_hash="sha256...",
    judgment_id="je-001",
    decision="HALT",
    block_mode="STOP",
    reason_code="DRIFT_THRESHOLD_EXCEEDED",
    drift_score_at_block=0.85,
    created_at=datetime.now(timezone.utc)
)
```

## O(1) Constraint Lookup

Constraints are named by hash for instant lookup:
```python
# Backend lookup (O(1))
constraint_file = f"constraint_{runtime_context_hash}.json"
if os.path.exists(constraint_file):
    return {"decision": "HALT", "reason": "PRIOR_CONSTRAINT_MATCH"}
```
