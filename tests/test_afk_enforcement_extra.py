
from unittest.mock import patch, MagicMock
from src.bridge import CliState
from tests.test_afk_enforcement import make_ghost, MockBridge

def test_context_restart_restart_does_not_approve_rejected_tool():
    """Applying context (C) restarts session but does NOT approve the rejected tool.

    Validates: Rejection flow distinction between A (approve) and C (context).
    """
    # Create ghost and mock bridge
    ghost, bridge = make_ghost(afk_level=3)
    bridge.state = CliState.EXITED
    
    # Simulate a rejected tool scenario
    with ghost._pending_lock:
        ghost._pending_query = "restart: Bash"
        ghost._pending_tool_name = "Bash"
    
    # Start context flow (C)
    # _handle_reply returns None normally, but in tests catching printed output 
    # might verify notify called. 
    ghost._handle_reply("C") 
    assert ghost._context_state == "awaiting_text"
    
    # Provide context
    ghost._handle_reply("Use python instead")
    assert ghost._context_state == "awaiting_confirm"
    
    # Confirm (Y)
    # Patch GhostBridge to verify restart
    new_bridge = MockBridge() 
    with patch("src.main.GhostBridge", return_value=new_bridge):
        ghost._handle_reply("Y")

    # Pending query/tool should be cleared
    assert ghost._pending_query is None
    # Rejected tool should NOT be in extra_allowed_tools (that's for A)
    assert "Bash" not in ghost._extra_allowed_tools
    
    # New bridge started
    assert new_bridge.started is True
    # Task should be updated (the mock bridge stores task in self.task if passed)
    # MockBridge doesn't store task in __init__ in test helper, but main pass it.
    # Let's inspect ghost.task which is updated
    assert "IMPORTANT ADDITIONAL CONTEXT" in ghost.task
    assert "Use python instead" in ghost.task
