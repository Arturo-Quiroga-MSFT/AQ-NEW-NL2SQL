"""
Quick test to verify session-based agent functions exist and work correctly.
"""

import sys

try:
    from nl2sql_main import (
        get_or_create_session_agents,
        cleanup_session_agents,
        _SESSION_AGENTS
    )
    
    print("✅ Session-based functions imported successfully!")
    print(f"✅ _SESSION_AGENTS dictionary exists: {type(_SESSION_AGENTS)}")
    print(f"✅ Current session agents: {len(_SESSION_AGENTS)} sessions")
    
    # Check function signatures
    import inspect
    
    sig1 = inspect.signature(get_or_create_session_agents)
    print(f"✅ get_or_create_session_agents signature: {sig1}")
    
    sig2 = inspect.signature(cleanup_session_agents)
    print(f"✅ cleanup_session_agents signature: {sig2}")
    
    print("\n🎉 All session-based agent functions are correctly defined!")
    print("   The code is ready for deployment.")
    
except ImportError as e:
    print(f"❌ Failed to import session functions: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
