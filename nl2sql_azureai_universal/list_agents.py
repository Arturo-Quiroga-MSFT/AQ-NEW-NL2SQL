"""
List all agents in Azure AI Foundry project.
This script helps identify agents that need cleanup before deploying session-based architecture.
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

try:
    # List all agents
    print("\n" + "="*80)
    print("AGENTS IN AZURE AI FOUNDRY PROJECT")
    print("="*80)
    
    agents = project_client.agents.list_agents()
    
    agent_list = []
    for agent in agents:
        agent_list.append({
            "id": agent.id,
            "name": agent.name if hasattr(agent, 'name') else "N/A",
            "model": agent.model if hasattr(agent, 'model') else "N/A",
            "created_at": agent.created_at if hasattr(agent, 'created_at') else "N/A"
        })
    
    if not agent_list:
        print("\n✅ No agents found in the project.")
    else:
        print(f"\n📊 Found {len(agent_list)} agent(s):\n")
        
        for i, agent in enumerate(agent_list, 1):
            print(f"{i}. Agent ID: {agent['id']}")
            print(f"   Name: {agent['name']}")
            print(f"   Model: {agent['model']}")
            print(f"   Created: {agent['created_at']}")
            print()
        
        print("="*80)
        print("\n💡 To delete agents, you can:")
        print("   1. Use the Azure AI Foundry portal (https://ai.azure.com)")
        print("   2. Use the cleanup_session_agents() function in nl2sql_main.py")
        print("   3. Run: project_client.agents.delete_agent('<agent_id>')")
        print("\n⚠️  Note: The new session-based architecture will create agents dynamically")
        print("   and clean them up automatically when conversations end.")
        
except Exception as e:
    print(f"\n❌ Error listing agents: {str(e)}")
    print("\nPlease ensure:")
    print("  1. PROJECT_ENDPOINT is set correctly in .env")
    print("  2. You have 'Azure AI User' role in the project")
    print("  3. You're authenticated with Azure CLI: az login")
