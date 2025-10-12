"""
teams_nl2sql_agent.py - Microsoft Teams Bot Wrapper for NL2SQL Pipeline
========================================================================

This module wraps the existing NL2SQL pipeline (nl2sql_main.py) with the
Microsoft 365 Agents SDK to enable natural language database queries via Teams.

Architecture:
- Teams message → M365 Agent → NL2SQL pipeline → SQL execution → Teams response
- Reuses 90%+ of existing NL2SQL code
- Thin wrapper layer for Teams messaging

Requirements:
- Microsoft 365 Agents SDK packages (from TestPyPI)
- Azure Bot Service registration
- Environment variables for bot authentication
"""

import os
import sys
import re
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import M365 Agents SDK
try:
    from microsoft_agents.hosting.core import (
        Authorization,
        AgentApplication,
        TurnState,
        TurnContext,
        MemoryStorage,
        MessageFactory,
    )
    from microsoft_agents.activity import load_configuration_from_env, ActivityTypes
    from microsoft_agents.hosting.aiohttp import CloudAdapter
    from microsoft_agents.authentication.msal import MsalConnectionManager
except ImportError as e:
    print("[ERROR] Failed to import Microsoft 365 Agents SDK packages.")
    print("Please install the required packages from TestPyPI:")
    print("  pip install -i https://test.pypi.org/simple/ microsoft-agents-core")
    print("  pip install -i https://test.pypi.org/simple/ microsoft-agents-authorization")
    print("  pip install -i https://test.pypi.org/simple/ microsoft-agents-connector")
    print("  pip install -i https://test.pypi.org/simple/ microsoft-agents-builder")
    print("  pip install -i https://test.pypi.org/simple/ microsoft-agents-authentication-msal")
    print("  pip install -i https://test.pypi.org/simple/ microsoft-agents-hosting-aiohttp")
    sys.exit(1)

# Import our existing NL2SQL functions
try:
    from nl2sql_main import (
        process_nl_query,
        extract_intent,
        generate_sql,
        execute_and_format,
        get_token_usage
    )
except ImportError as e:
    print(f"[ERROR] Failed to import NL2SQL functions: {e}")
    print("Make sure nl2sql_main.py is in the same directory.")
    sys.exit(1)

# Import Adaptive Cards support
try:
    from adaptive_cards import (
        AdaptiveCardBuilder,
        create_card_attachment
    )
    ADAPTIVE_CARDS_ENABLED = True
except ImportError:
    print("[WARNING] Adaptive Cards module not found. Falling back to plain text.")
    print("  To enable Adaptive Cards: ensure adaptive_cards.py is present")
    ADAPTIVE_CARDS_ENABLED = False


# ========== CONFIGURATION ==========

# Load configuration from environment using SDK helper
agents_sdk_config = load_configuration_from_env(os.environ)

# ========== INITIALIZE M365 AGENTS SDK COMPONENTS ==========

# Create storage (in-memory for now, can switch to BlobStorage/CosmosDB later)
STORAGE = MemoryStorage()

# Thread management: Map conversation_id -> thread_id for conversation continuity
# Azure AI Agents SDK handles conversation history natively via threads
CONVERSATION_THREADS = {}

# Create MSAL connection manager for authentication
CONNECTION_MANAGER = MsalConnectionManager(**agents_sdk_config)

# Create cloud adapter for Bot Service communication
ADAPTER = CloudAdapter(connection_manager=CONNECTION_MANAGER)

# Create Authorization (for OAuth scenarios)
AUTHORIZATION = Authorization(STORAGE, CONNECTION_MANAGER, **agents_sdk_config)

# Create agent application
AGENT_APP = AgentApplication[TurnState](
    storage=STORAGE,
    adapter=ADAPTER,
    authorization=AUTHORIZATION,
    **agents_sdk_config
)


# ========== EVENT HANDLERS ==========

@AGENT_APP.conversation_update("membersAdded")
async def on_members_added(context: TurnContext, state: TurnState):
    """
    Handle new members added to conversation (welcome message).
    """
    for member in context.activity.members_added:
        if member.id != context.activity.recipient.id:
            if ADAPTIVE_CARDS_ENABLED:
                # Send welcome Adaptive Card
                welcome_card = AdaptiveCardBuilder.create_welcome_card()
                attachment = create_card_attachment(welcome_card)
                # Create activity manually with attachment
                from microsoft_agents.activity import Activity
                activity = Activity(
                    type=ActivityTypes.message,
                    attachments=[attachment]
                )
                await context.send_activity(activity)
            else:
                # Fallback to plain text
                welcome_message = """👋 **Welcome to NL2SQL Bot!**

I can help you query databases using natural language. Just ask me questions like:
- "How many customers do we have?"
- "Show me loans with balance over $10,000"
- "What's the average loan amount by state?"
- "List customers who joined in the last 30 days"

I'll convert your question to SQL, execute it, and show you the results!

**Powered by Azure AI Agents** 🤖"""
                
                await context.send_activity(MessageFactory.text(welcome_message))


@AGENT_APP.activity(ActivityTypes.message)
async def on_message(context: TurnContext, state: TurnState):
    """
    Handle incoming messages - this is where the NL2SQL magic happens!
    """
    raw_text = context.activity.text or ""
    # Debug raw incoming text (will show commands vs queries)
    print(f"[TEAMS][DEBUG] Raw incoming text repr={raw_text!r}")

    # Check if this is a button click (Adaptive Card action)
    if context.activity.value:
        action_data = context.activity.value
        action_type = action_data.get("action")
        
        if action_type == "rerun":
            # Re-run the query
            user_query = action_data.get("query")
            if not user_query:
                await context.send_activity("❌ Cannot re-run: No query found.")
                return
        elif action_type == "copy":
            # Acknowledge copy action
            await context.send_activity("✅ Results copied! (Paste from clipboard)")
            return
        elif action_type == "modify":
            # Prompt user to modify the query
            sql = action_data.get("sql", "")
            prompt_msg = f"📝 **Modify Query**\n\nOriginal SQL:\n```sql\n{sql}\n```\n\nPlease type your modified question or SQL query below:"
            await context.send_activity(MessageFactory.text(prompt_msg))
            return
        else:
            await context.send_activity("❓ Unknown action.")
            return
    else:
        # Regular text message
        user_query = context.activity.text
    
    if not user_query or not user_query.strip():
        await context.send_activity("Please provide a query.")
        return
    
    # Handle help command
    if user_query.strip().lower() in ["/help", "help", "?"]:
        if ADAPTIVE_CARDS_ENABLED:
            # Send help Adaptive Card
            help_card = AdaptiveCardBuilder.create_help_card()
            attachment = create_card_attachment(help_card)
            from microsoft_agents.activity import Activity
            activity = Activity(
                type=ActivityTypes.message,
                attachments=[attachment]
            )
            await context.send_activity(activity)
        else:
            # Fallback to plain text
            help_message = """**NL2SQL Bot Commands:**

Just type your natural language question to query the database!

**Examples:**
- Count records: "How many loans are active?"
- Filter data: "Show customers in California"
- Aggregate: "What's the total loan amount by state?"
- Complex: "List top 10 customers by loan balance"

**Special Commands:**
- `/help` - Show this help message
- `/reset` - Start a new conversation (clears context)
- `/about` - About this bot

**Conversation Features:**
Ask follow-up questions naturally! The bot remembers your conversation context.
- "Show me top 5 customers"
- "Tell me about the third one"
- "What was their balance?"

The bot will:
1. 🧠 Extract intent from your question
2. 💡 Generate SQL query
3. ⚡ Execute against the database
4. 📊 Format and return results"""
            
            await context.send_activity(MessageFactory.text(help_message))
        return
    
    # Normalize & robust command parsing (tolerate leading mention / whitespace)
    stripped = user_query.strip()
    lowered = stripped.lower()
    # If Teams mentions bot, pattern might be like "@BotName /sessionreset" – split and scan tokens
    tokens = [t for t in re.split(r"\s+", lowered) if t]
    # First slash token wins
    slash_token = next((t for t in tokens if t.startswith('/')), lowered if lowered.startswith('/') else '')

    reset_commands = {"/sessionreset", "/nl2sqlreset", "/nlreset", "/agentreset"}
    legacy_reset_commands = {"/reset", "reset"}

    if slash_token in reset_commands or slash_token in legacy_reset_commands:
        conversation_id = context.activity.conversation.id
        had_thread = conversation_id in CONVERSATION_THREADS
        if had_thread:
            thread_id = CONVERSATION_THREADS[conversation_id]
            from nl2sql_main import cleanup_session_agents
            cleanup_session_agents(thread_id)
            del CONVERSATION_THREADS[conversation_id]
        # Craft response clarifying which command was used
        if slash_token in legacy_reset_commands and slash_token not in reset_commands:
            extra = " (legacy /reset detected—prefer /sessionreset going forward)"
        else:
            extra = ""
        if had_thread:
            await context.send_activity(f"✅ Session agents destroyed; next query will start a fresh session.{extra}")
        else:
            await context.send_activity(f"✅ No prior session found; ready for a fresh start.{extra}")
        return
    
    # Handle about command
    if user_query.strip().lower() in ["/about", "about"]:
        about_message = """**NL2SQL Bot** - Natural Language to SQL Query Assistant

**Technology Stack:**
- 🤖 Microsoft 365 Agents SDK
- 🧠 Azure AI Foundry Agent Service
- 💾 Azure SQL Database
- 🔗 Python + aiohttp

**Architecture:**
Teams → M365 Agent → Azure AI → SQL → Results

**Code Reuse:** 90%+ of existing NL2SQL pipeline

Built with ❤️ for seamless database querying in Teams!"""
        
        await context.send_activity(MessageFactory.text(about_message))
        return
    
    # Send typing indicator
    await context.send_activity(MessageFactory.text("🤔 Processing your query..."))
    
    try:
        # Get or create thread for this conversation
        # Azure AI Agents SDK handles conversation history natively via threads
        conversation_id = context.activity.conversation.id
        thread_id = CONVERSATION_THREADS.get(conversation_id)
        
        # Track if this is part of an ongoing conversation
        is_conversation = thread_id is not None
        
        # Call the NL2SQL pipeline with thread for conversation continuity
        result = process_nl_query(user_query, execute=True, thread_id=thread_id)
        
        # Store thread_id for future messages in this conversation
        CONVERSATION_THREADS[conversation_id] = result.get("thread_id")
        
        # Send Adaptive Card or plain text response
        if ADAPTIVE_CARDS_ENABLED:
            # Check if execution was successful
            if result.get("results", {}).get("success"):
                # Create success card with conversation indicator and insights
                card = AdaptiveCardBuilder.create_success_card(
                    sql=result.get("sql", ""),
                    results=result.get("results", {}),
                    token_usage=result.get("token_usage"),
                    user_query=user_query,
                    elapsed_time=result.get("elapsed_time"),
                    is_conversation=is_conversation,
                    insights=result.get("insights")  # Pass insights from pipeline
                )
            else:
                # Create error card with conversation indicator
                error_msg = result.get("results", {}).get("error", "Unknown error")
                suggestions = [
                    "Check table and column names",
                    "Try rephrasing your question",
                    "Use simpler filters or conditions"
                ]
                card = AdaptiveCardBuilder.create_error_card(
                    error_message=error_msg,
                    sql=result.get("sql"),
                    suggestions=suggestions,
                    user_query=user_query,
                    is_conversation=is_conversation
                )
            
            # Send as attachment
            attachment = create_card_attachment(card)
            from microsoft_agents.activity import Activity
            activity = Activity(
                type=ActivityTypes.message,
                attachments=[attachment]
            )
            await context.send_activity(activity)
        else:
            # Fallback to plain text
            response_message = _format_response(user_query, result)
            await context.send_activity(MessageFactory.text(response_message))
        
    except Exception as e:
        if ADAPTIVE_CARDS_ENABLED:
            # Send error card
            error_card = AdaptiveCardBuilder.create_error_card(
                error_message=str(e),
                suggestions=[
                    "Try rephrasing your question",
                    "Use /help to see examples",
                    "Contact support if the issue persists"
                ],
                user_query=user_query
            )
            attachment = create_card_attachment(error_card)
            from microsoft_agents.activity import Activity
            activity = Activity(
                type=ActivityTypes.message,
                attachments=[attachment]
            )
            await context.send_activity(activity)
        else:
            # Fallback plain text error
            error_message = f"❌ **Error processing query**\n\n{str(e)}\n\nPlease try rephrasing your question or contact support."
            await context.send_activity(MessageFactory.text(error_message))
        print(f"[ERROR] Exception in on_message: {e}", file=sys.stderr)


@AGENT_APP.error
async def on_error(context: TurnContext, error: Exception):
    """
    Global error handler for the agent.
    """
    print(f"[ERROR] Unhandled exception: {error}", file=sys.stderr)
    
    # Send a friendly error message to the user
    error_message = """❌ **Oops! Something went wrong.**

I encountered an error while processing your request. Please try again or rephrase your question.

If the problem persists, contact the bot administrator."""
    
    try:
        await context.send_activity(MessageFactory.text(error_message))
    except Exception:
        # If we can't even send an error message, just log it
        print("[ERROR] Failed to send error message to user", file=sys.stderr)


# ========== HELPER FUNCTIONS ==========

def _format_response(query: str, result: dict) -> str:
    """
    Format the NL2SQL pipeline result into a Teams-friendly message.
    
    Args:
        query: Original user query
        result: Result dictionary from process_nl_query()
    
    Returns:
        Formatted markdown message for Teams
    """
    lines = []
    
    # Header
    lines.append("✅ **Query Results**")
    lines.append("")
    
    # Show SQL query
    lines.append("**Generated SQL:**")
    lines.append("```sql")
    lines.append(result.get("sql", "N/A"))
    lines.append("```")
    lines.append("")
    
    # Show results
    if "results" in result and result["results"].get("success"):
        rows = result["results"].get("rows", [])
        count = result["results"].get("count", 0)
        
        lines.append(f"**Found {count} result(s):**")
        lines.append("")
        
        if count == 0:
            lines.append("_No rows returned._")
        elif count <= 10:
            # Show all rows as formatted table
            lines.append(_format_rows_as_table(rows))
        else:
            # Show first 10 rows + message
            lines.append(_format_rows_as_table(rows[:10]))
            lines.append("")
            lines.append(f"_Showing first 10 of {count} results. Query returned {count - 10} more rows._")
    else:
        # Execution error
        error_msg = result.get("results", {}).get("error", "Unknown error")
        lines.append(f"❌ **Execution Error:**")
        lines.append(f"```")
        lines.append(error_msg)
        lines.append("```")
    
    # Token usage (optional, for monitoring)
    token_usage = result.get("token_usage", {})
    if token_usage:
        total = token_usage.get("total", 0)
        lines.append("")
        lines.append(f"_Tokens used: {total}_")
    
    return "\n".join(lines)


def _format_rows_as_table(rows: list) -> str:
    """
    Format query result rows as a simple text table.
    
    Args:
        rows: List of dictionaries (query results)
    
    Returns:
        Formatted table string
    """
    if not rows:
        return "_No rows_"
    
    # Get columns
    columns = list(rows[0].keys())
    
    # Calculate column widths
    col_widths = {}
    for col in columns:
        col_widths[col] = max(len(str(col)), max(len(str(row.get(col, ""))) for row in rows))
    
    # Build table
    lines = []
    
    # Header
    header = " | ".join(str(col).ljust(col_widths[col]) for col in columns)
    lines.append(header)
    
    # Separator
    separator = "-+-".join("-" * col_widths[col] for col in columns)
    lines.append(separator)
    
    # Rows
    for row in rows:
        row_str = " | ".join(str(row.get(col, "")).ljust(col_widths[col]) for col in columns)
        lines.append(row_str)
    
    return "```\n" + "\n".join(lines) + "\n```"


# ========== EXPORTS ==========

# Export agent application for use by start_server.py
__all__ = [
    "AGENT_APP",
    "ADAPTER",
    "CONNECTION_MANAGER",
    "STORAGE"
]


if __name__ == "__main__":
    print("teams_nl2sql_agent.py - This module should be imported by start_server.py")
    print("Run: python start_server.py")
