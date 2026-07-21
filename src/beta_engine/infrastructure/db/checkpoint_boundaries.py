"""Declared branch-checkpoint boundaries and legacy capture command identities.

Only the first five checkpoint kinds have capture behavior in R3H.  The
remaining kinds document reserved future boundaries without enabling them.
"""

BRANCH_CHECKPOINT_KIND_INITIAL = "initial"
BRANCH_CHECKPOINT_KIND_CURRENT_STATE_CAPTURE = "current_state_capture"
BRANCH_CHECKPOINT_KIND_EVENT_COMPLETED = "event_completed"
BRANCH_CHECKPOINT_KIND_WEEK_COMPLETED = "week_completed"

# Declared-only future boundaries; do not add capture behavior here.
BRANCH_CHECKPOINT_KIND_MATCH_COMPLETED = "match_completed"
BRANCH_CHECKPOINT_KIND_ROUND_COMPLETED = "round_completed"

# Implemented explicit, capture-only boundary for an already persisted legacy action.
BRANCH_CHECKPOINT_KIND_ADMIN_ACTION_APPLIED = "admin_action_applied"
BRANCH_CHECKPOINT_KIND_SEASON_ROLLOVER = "season_rollover"
BRANCH_CHECKPOINT_KIND_BOOTSTRAP_START = "bootstrap_start"

BRANCH_CHECKPOINT_COMMAND_KIND_CAPTURE_INITIAL = "capture_initial"
BRANCH_CHECKPOINT_COMMAND_KIND_CAPTURE_CURRENT_LEGACY_STATE = "capture_current_legacy_state"
BRANCH_CHECKPOINT_COMMAND_KIND_CAPTURE_COMPLETED_EVENT_LEGACY_STATE = "capture_completed_event_legacy_state"
BRANCH_CHECKPOINT_COMMAND_KIND_CAPTURE_COMPLETED_WEEK_LEGACY_STATE = "capture_completed_week_legacy_state"
BRANCH_CHECKPOINT_COMMAND_KIND_CAPTURE_ADMIN_ACTION_LEGACY_STATE = "capture_admin_action_legacy_state"
