# Implementation Plan: AFK Level Enforcement

## Overview

Fix the three bugs in `src/main.py` that allow the session to bypass AFK level enforcement: the premature loop exit, the reply handler early return, and the missing bridge-alive check on approve. Then add comprehensive tests covering all AFK levels and the blocking behavior.

## Tasks

- [x] 1. Fix _run_loop exit condition to check for pending queries
  - [x] 1.1 Add pending query check to the exit condition in _run_loop
    - In src/main.py, _run_loop() method, add has_pending check using self._pending_lock before the if block that checks self._bridge.state == CliState.EXITED
    - Add "and not has_pending" to the exit condition
    - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Fix _handle_reply_inner to process replies when pending query exists
  - [x] 2.1 Add pending query check to the early-return guard in _handle_reply_inner
    - In src/main.py, _handle_reply_inner() method, acquire _pending_lock and check _pending_query is not None before the EXITED early-return guard
    - Add "and not has_pending" to the early-return condition
    - _Requirements: 2.1, 2.2, 2.3_
  - [x] 2.2 Add bridge-alive check in the Approve path
    - In the first_char == "A" branch, wrap self._bridge.send("y") with a check: only send if self._bridge is not None and self._bridge.state != CliState.EXITED
    - _Requirements: 2.3, 4.3_

- [x] 3. Checkpoint - Verify fixes
  - Ensure all existing tests still pass, ask the user if questions arise.

- [ ] 4. Add tests for AFK level enforcement
  - [x] 4.1 Create test_afk_enforcement.py with test fixtures and mock helpers
    - Create mock classes for GhostBridge, ScreenNotifier, and TelegramBot
    - Create a helper function to instantiate ClaudeGhost with mocked dependencies
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  - [ ]* 4.2 Write property test for session loop pending query behavior
    - **Property 1: Session loop does not exit while a pending query exists**
    - **Validates: Requirements 1.1, 1.3**
  - [ ]* 4.3 Write property test for reply handler with pending query and EXITED bridge
    - **Property 2: Reply handler processes replies when pending query exists despite EXITED bridge**
    - **Validates: Requirements 2.1**
  - [ ]* 4.4 Write property test for autonomy matrix correctness
    - **Property 3: Autonomy matrix correctness across all AFK levels**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
  - [ ]* 4.5 Write property test for ASK_USER setting pending query
    - **Property 4: ASK_USER decision sets pending query and sends notification**
    - **Validates: Requirements 4.1**
  - [ ]* 4.6 Write property test for no premature CLI response
    - **Property 5: No premature CLI response while pending query is set**
    - **Validates: Requirements 4.2**
  - [ ]* 4.7 Write unit tests for specific scenarios
    - Test: session loop exits normally when bridge EXITED and no pending query (Req 1.2)
    - Test: reply handler discards replies when bridge EXITED and no pending query (Req 2.2)
    - Test: approve clears pending query when bridge is EXITED (Req 2.3)
    - Test: approve sends "y" to live bridge (Req 4.3)
    - Test: block sends "n", kills, restarts (Req 4.4)
    - Test: detonate kills bridge and terminates session (Req 4.5)
    - Test: level 1 triggers approval for "create test.md" write command (Req 5.5)

- [x] 5. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- The core fix is in tasks 1 and 2 — only two methods in src/main.py need changes
- No changes to guardian.py or bridge.py are required
- Property tests use hypothesis library for Python property-based testing
- Each property test references its design document property number
