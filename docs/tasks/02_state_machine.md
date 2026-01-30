# Task: Implement SRE State Machine

## Objective
Implement a robust state machine in `src/sre/core/state_machine.py` to manage `IncidentStatus` transitions. This is a prerequisite for the Supervisor Agent's routing logic.

## Requirements
- Define valid transitions (e.g., MONITORING -> DIAGNOSING is OK, but RESOLVED -> MONITORING might not be).
- Implement a `validate_transition(current, next)` function.
- Integrate with `SREState`.
- Add unit tests in `tests/sre/unit/core/test_state_machine.py`.

## SOP
- Atomic commits: One file or logical change per commit.
- Run `make all` or equivalent tests after changes.
- Use Python 3.11 features and type hints.
