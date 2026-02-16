# Changelog

All notable changes to ClaudeGhost will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.1] - 2026-02-16

### Fixed
- **AFK Level Enforcement**: Fixed critical bug where session would exit without waiting for user approval at restrictive AFK levels (especially level 1 "Paranoid")
  - Session loop now properly checks for pending queries before exiting
  - Reply handler now processes user responses even if CLI process has already exited
  - Approve action now checks if bridge is alive before sending response
  - Added comprehensive test suite (30 tests) covering all AFK levels and blocking behavior

## [2.1.0] - 2026-02-13

### Added
- Session loop - continue working with multiple tasks without restarting
- Changelog tracking - automatic session logs with files modified and commands executed
- Auto-update checker - get notified when new version is available
- Live dashboard with real-time status and logs

### Changed
- Improved Telegram notification format
- Enhanced error handling and reporting

## [2.0.0] - 2026-02-10

### Added
- Initial release with core features
- AFK autonomy levels (1-5)
- Telegram Bot API integration
- Risk classification system
- Budget control
- Cross-platform support (Windows, macOS, Linux)
- Stall detection
