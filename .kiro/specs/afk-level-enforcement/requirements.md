# Requirements Document

## Introduction

The AFK level enforcement system in ClaudeGhost controls how much autonomy the Claude CLI agent has during a supervised session. Each AFK level (1-5) defines which risk categories of commands require user approval versus automatic approval. Currently, the session loop (`_run_loop`) exits prematurely when the CLI process finishes, even if there is a pending user approval query. Additionally, the reply handler (`_handle_reply_inner`) silently discards user responses when the bridge has already exited. This means that at lower AFK levels (especially level 1 "Paranoid"), the agent can complete its entire task without ever asking the user for approval, defeating the purpose of the supervision system.

## Glossary

- **Session_Loop**: The `_run_loop` method in `ClaudeGhost` that polls bridge state and processes screen notifications until the session ends.
- **Guardian**: The module (`src/guardian.py`) that classifies commands by risk and evaluates them against the autonomy matrix to produce a Decision.
- **Bridge**: The `GhostBridge` class (`src/bridge.py`) that manages the Claude CLI subprocess and exposes its state via `CliState`.
- **Pending_Query**: A field (`_pending_query`) on `ClaudeGhost` that holds the command string awaiting user approval; `None` when no approval is outstanding.
- **AFK_Level**: An integer 1-5 representing the user's chosen autonomy level, mapped to decisions per risk category in the autonomy matrix.
- **Autonomy_Matrix**: A lookup table mapping each AFK level and risk category pair to either `AUTO_APPROVE` or `ASK_USER`.
- **Decision**: The outcome of evaluating a command: either `AUTO_APPROVE` (proceed without user input) or `ASK_USER` (block until user responds).
- **Risk_Category**: One of `READ_ONLY`, `WRITE`, `EXECUTE`, or `HIGH_RISK`, determined by pattern-matching the command string.
- **Reply_Handler**: The `_handle_reply_inner` method that processes user responses (A/B/C/D) to approval requests.

## Requirements

### Requirement 1: Session Loop Must Not Exit While a Query Is Pending

**User Story:** As a user supervising an agent at a restrictive AFK level, I want the session to remain active until I have responded to every pending approval request, so that no command executes without my explicit consent.

#### Acceptance Criteria

1. WHILE a Pending_Query is set, THE Session_Loop SHALL continue running even when the Bridge state is `EXITED`.
2. WHEN the Bridge state transitions to `EXITED` and no Pending_Query is set, THE Session_Loop SHALL exit normally.
3. WHEN the Bridge state is `EXITED` and a Pending_Query is set, THE Session_Loop SHALL continue processing screen notifications and user input until the Pending_Query is resolved.

### Requirement 2: Reply Handler Must Process Responses Regardless of Bridge State

**User Story:** As a user who receives an approval prompt, I want my response to be processed even if the CLI process has already exited, so that my approval or rejection is never silently ignored.

#### Acceptance Criteria

1. WHEN the user sends a reply and the Bridge state is `EXITED` and a Pending_Query is set, THE Reply_Handler SHALL process the reply normally (A/B/C/D).
2. WHEN the user sends a reply and the Bridge state is `EXITED` and no Pending_Query is set and the session is not budget-paused or restarting, THE Reply_Handler SHALL discard the reply.
3. WHEN the user approves (reply "A") a Pending_Query while the Bridge state is `EXITED`, THE Reply_Handler SHALL clear the Pending_Query and allow the Session_Loop to exit.

### Requirement 3: Autonomy Matrix Enforcement Per AFK Level

**User Story:** As a user, I want each AFK level to enforce its defined autonomy matrix exactly, so that I can trust the level I selected controls which commands require my approval.

#### Acceptance Criteria

1. WHILE AFK_Level is 1 (Paranoid), THE Guardian SHALL return `ASK_USER` for every Risk_Category (`READ_ONLY`, `WRITE`, `EXECUTE`, `HIGH_RISK`).
2. WHILE AFK_Level is 2 (Auditor), THE Guardian SHALL return `AUTO_APPROVE` for `READ_ONLY` and `ASK_USER` for `WRITE`, `EXECUTE`, and `HIGH_RISK`.
3. WHILE AFK_Level is 3 (Manager), THE Guardian SHALL return `AUTO_APPROVE` for `READ_ONLY` and `WRITE`, and `ASK_USER` for `EXECUTE` and `HIGH_RISK`.
4. WHILE AFK_Level is 4 (Director), THE Guardian SHALL return `AUTO_APPROVE` for `READ_ONLY`, `WRITE`, and `EXECUTE`, and `ASK_USER` for `HIGH_RISK`.
5. WHILE AFK_Level is 5 (God Mode), THE Guardian SHALL return `AUTO_APPROVE` for every Risk_Category.

### Requirement 4: Blocking Behavior on ASK_USER Decision

**User Story:** As a user at a restrictive AFK level, I want the agent to fully stop and wait for my response when an action requires approval, so that no further actions proceed until I decide.

#### Acceptance Criteria

1. WHEN the Guardian returns `ASK_USER` for a command, THE Session_Loop SHALL set the Pending_Query and send an approval notification to the user.
2. WHILE a Pending_Query is set, THE Session_Loop SHALL NOT send "y" or "n" to the Bridge for that command until the user responds.
3. WHEN the user responds with "A" (Approve), THE Reply_Handler SHALL send "y" to the Bridge and clear the Pending_Query.
4. WHEN the user responds with "B" (Block), THE Reply_Handler SHALL send "n" to the Bridge, clear the Pending_Query, and restart with an alternative approach.
5. WHEN the user responds with "D" (Detonate), THE Reply_Handler SHALL kill the Bridge, clear the Pending_Query, and terminate the session.

### Requirement 5: AFK Level Enforcement Integration Tests

**User Story:** As a developer, I want automated tests that verify each AFK level correctly blocks or auto-approves commands according to the autonomy matrix, so that regressions in enforcement behavior are caught early.

#### Acceptance Criteria

1. THE Test_Suite SHALL include a test for each AFK level (1 through 5) that verifies the Guardian returns the correct Decision for every Risk_Category.
2. THE Test_Suite SHALL include a test that verifies the Session_Loop does not exit while a Pending_Query is set and the Bridge state is `EXITED`.
3. THE Test_Suite SHALL include a test that verifies the Reply_Handler processes user replies when the Bridge state is `EXITED` and a Pending_Query is set.
4. THE Test_Suite SHALL include a test that verifies the Reply_Handler discards replies when the Bridge state is `EXITED` and no Pending_Query is set.
5. THE Test_Suite SHALL include a test for AFK level 1 that verifies a simulated "create test.md" task triggers an approval request before any write action proceeds.
