"""
Cleanup old NL2SQL agents from Azure AI Foundry project.
This script deletes persistent agents that will be replaced by session-based agents.
"""

import os
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# Load environment variables
load_dotenv()

PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT")

if not PROJECT_ENDPOINT:
    raise ValueError("PROJECT_ENDPOINT environment variable is required")

# Initialize client
print(f"Connecting to Azure AI Foundry project: {PROJECT_ENDPOINT}")
project_client = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)

# Agents to delete (NL2SQL related only)
AGENTS_TO_DELETE = [
    "intent-extractor-persistent",
    "sql-generator-persistent",
    "data-insights-persistent",  # if it exists
    "intent-extractor-demo",
    "sql-generator-demo"
]

try:
    # List all agents
    print("\n" + "="*80)
    print("CLEANING UP OLD NL2SQL AGENTS")
    print("="*80)
    
    agents = list(project_client.agents.list_agents())  # Convert to list to avoid iterator issues
    
    deleted_count = 0
    failed_count = 0
    kept_count = 0
    
    for agent in agents:
        agent_name = agent.name if hasattr(agent, 'name') else "N/A"
        agent_id = agent.id
        
        # Check if this is an NL2SQL agent to delete
        if agent_name in AGENTS_TO_DELETE:
            try:
                print(f"🗑️  Deleting: {agent_name} (ID: {agent_id})")
                project_client.agents.delete_agent(agent_id)
                deleted_count += 1
            except Exception as e:
                error_msg = str(e)
                if "No assistant found" in error_msg or "not found" in error_msg.lower():
                    print(f"   ⚠️  Already deleted: {agent_id[:20]}...")
                else:
                    print(f"   ❌ Failed: {error_msg[:50]}...")
                failed_count += 1
        else:
            kept_count += 1
    
    print("\n" + "="*80)
    print(f"✅ Cleanup complete!")
    print(f"   - Deleted: {deleted_count} NL2SQL agents")
    print(f"   - Skipped: {failed_count} (already deleted)")
    print(f"   - Kept: {kept_count} other agents")
    print("="*80)
    
    if deleted_count > 0:
        print("\n💡 Next steps:")
        print("   1. Deploy the new session-based architecture")
        print("   2. Test with queries - new agents will be created automatically")
        print("   3. Use /reset to clean up agents when conversation ends")
        
except Exception as e:
    print(f"\n❌ Error during cleanup: {str(e)}")
    print("\nPlease ensure:")
    print("  1. PROJECT_ENDPOINT is set correctly in .env")
    print("  2. You have 'Azure AI User' role with delete permissions")
    print("  3. You're authenticated with Azure CLI: az login")
