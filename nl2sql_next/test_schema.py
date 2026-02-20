"""Test schema extractor against live RetailDW database."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schema import get_schema_context, refresh_schema_cache, CACHE_FILE

print("Refreshing schema cache from live database...")
path = refresh_schema_cache()
print(f"Cache saved to: {path}\n")

print("="*80)
print("SCHEMA CONTEXT (as sent to LLM)")
print("="*80)
ctx = get_schema_context(ttl=0)
print(ctx)
print(f"\n--- Context length: {len(ctx)} chars ---")
