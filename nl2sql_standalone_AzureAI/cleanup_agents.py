#!/usr/bin/env python3
"""
Cleanup old NL2SQL agents from Azure AI Foundry project.
This helps manage the accumulation of persistent agents.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

load_dotenv()

PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT")

client = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential()
)


def cleanup_nl2sql_agents(keep_recent=2, older_than_days=7, dry_run=True):
    """
    Clean up old NL2SQL agents.
    
    Args:
        keep_recent: Keep this many most recent agents of each type
        older_than_days: Only delete agents older than this many days
        dry_run: If True, only show what would be deleted (don't actually delete)
    """
    print("=" * 70)
    print("NL2SQL Agent Cleanup Utility")
    print("=" * 70)
    print(f"Mode: {'DRY RUN (no deletions)' if dry_run else 'LIVE (will delete)'}")
    print(f"Keep recent: {keep_recent} agents per type")
    print(f"Delete agents older than: {older_than_days} days")
    print()
    
    try:
        agents = list(client.agents.list_agents())
        
        # Filter for NL2SQL agents
        intent_agents = []
        sql_agents = []
        
        for agent in agents:
            if 'intent-extractor' in agent.name.lower():
                intent_agents.append(agent)
            elif 'sql-generator' in agent.name.lower():
                sql_agents.append(agent)
        
        print(f"Found {len(intent_agents)} intent extraction agents")
        print(f"Found {len(sql_agents)} SQL generation agents")
        print()
        
        # Sort by creation date (newest first)
        intent_agents.sort(key=lambda a: a.created_at, reverse=True)
        sql_agents.sort(key=lambda a: a.created_at, reverse=True)
        
        # Calculate cutoff date
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        
        deleted_count = 0
        kept_count = 0
        
        # Process intent agents
        print("Intent Extraction Agents:")
        print("-" * 70)
        for idx, agent in enumerate(intent_agents):
            age_days = (datetime.now(timezone.utc) - agent.created_at).days
            
            # Keep recent agents
            if idx < keep_recent:
                print(f"  ✓ KEEP   [{idx+1}] {agent.id} (age: {age_days}d) - Recent")
                kept_count += 1
            # Keep agents newer than cutoff
            elif agent.created_at > cutoff_date:
                print(f"  ✓ KEEP   [{idx+1}] {agent.id} (age: {age_days}d) - Too new")
                kept_count += 1
            # Delete old agents
            else:
                action = "WOULD DELETE" if dry_run else "DELETING"
                print(f"  ✗ {action} [{idx+1}] {agent.id} (age: {age_days}d)")
                if not dry_run:
                    try:
                        client.agents.delete_agent(agent.id)
                        print(f"    → Deleted successfully")
                    except Exception as e:
                        print(f"    → Error: {e}")
                deleted_count += 1
        
        print()
        
        # Process SQL agents
        print("SQL Generation Agents:")
        print("-" * 70)
        for idx, agent in enumerate(sql_agents):
            age_days = (datetime.now(timezone.utc) - agent.created_at).days
            
            # Keep recent agents
            if idx < keep_recent:
                print(f"  ✓ KEEP   [{idx+1}] {agent.id} (age: {age_days}d) - Recent")
                kept_count += 1
            # Keep agents newer than cutoff
            elif agent.created_at > cutoff_date:
                print(f"  ✓ KEEP   [{idx+1}] {agent.id} (age: {age_days}d) - Too new")
                kept_count += 1
            # Delete old agents
            else:
                action = "WOULD DELETE" if dry_run else "DELETING"
                print(f"  ✗ {action} [{idx+1}] {agent.id} (age: {age_days}d)")
                if not dry_run:
                    try:
                        client.agents.delete_agent(agent.id)
                        print(f"    → Deleted successfully")
                    except Exception as e:
                        print(f"    → Error: {e}")
                deleted_count += 1
        
        print()
        print("=" * 70)
        print("Summary:")
        print(f"  Kept: {kept_count} agents")
        if dry_run:
            print(f"  Would delete: {deleted_count} agents")
        else:
            print(f"  Deleted: {deleted_count} agents")
        print("=" * 70)
        
        if dry_run and deleted_count > 0:
            print()
            print("To actually delete agents, run:")
            print("  python cleanup_agents.py --live")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Clean up old NL2SQL agents from Azure AI Foundry"
    )
    parser.add_argument(
        '--live',
        action='store_true',
        help='Actually delete agents (default is dry-run)'
    )
    parser.add_argument(
        '--keep',
        type=int,
        default=2,
        help='Number of recent agents to keep per type (default: 2)'
    )
    parser.add_argument(
        '--older-than',
        type=int,
        default=7,
        help='Only delete agents older than this many days (default: 7)'
    )
    
    args = parser.parse_args()
    
    return cleanup_nl2sql_agents(
        keep_recent=args.keep,
        older_than_days=args.older_than,
        dry_run=not args.live
    )


if __name__ == "__main__":
    sys.exit(main())
