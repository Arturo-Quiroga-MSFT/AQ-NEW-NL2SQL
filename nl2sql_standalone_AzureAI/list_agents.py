#!/usr/bin/env python3
"""
List all agents in the Azure AI Foundry project.
Use this to see which agents are persisting.
"""

import os
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

load_dotenv()

PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT")

client = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential()
)

print("Listing all agents in Azure AI Foundry project:")
print("=" * 60)

try:
    agents = client.agents.list_agents()
    count = 0
    for agent in agents:
        count += 1
        print(f"\nAgent #{count}:")
        print(f"  ID: {agent.id}")
        print(f"  Name: {agent.name}")
        print(f"  Model: {agent.model}")
        print(f"  Created: {agent.created_at}")
    
    print(f"\n{'=' * 60}")
    print(f"Total agents: {count}")
    
    if count == 0:
        print("\nNo agents found. They may have been cleaned up.")
    else:
        print(f"\n✓ Found {count} persistent agent(s) in Azure AI Foundry")
        
except Exception as e:
    print(f"Error listing agents: {e}")
