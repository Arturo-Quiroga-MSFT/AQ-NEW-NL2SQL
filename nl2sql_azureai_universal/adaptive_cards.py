"""
adaptive_cards.py - Adaptive Card Builder for Teams NL2SQL Bot
===============================================================

This module provides reusable Adaptive Card templates for displaying
query results, errors, and interactive features in Microsoft Teams.

Adaptive Cards provide:
- Rich visual design with colors and structure
- Interactive buttons and actions
- Better mobile experience
- Professional appearance

Documentation: https://adaptivecards.io/
"""

from typing import List, Dict, Any, Optional
from datetime import datetime


class AdaptiveCardBuilder:
    """
    Builder class for creating Adaptive Cards for Teams bot responses.
    """
    
    @staticmethod
    def create_success_card(
        sql: str,
        results: Dict[str, Any],
        token_usage: Optional[Dict[str, int]] = None,
        execution_time: Optional[float] = None,
        user_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an Adaptive Card for successful query results.
        
        Args:
            sql: Generated SQL query
            results: Query results dict with 'rows', 'count', 'columns'
            token_usage: Token usage statistics
            execution_time: Query execution time in seconds
            user_query: Original user question
            
        Returns:
            Adaptive Card JSON dict
        """
        rows = results.get("rows", [])
        count = results.get("count", 0)
        
        card = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.5",
            "body": []
        }
        
        # Header Section (Green - Success)
        header = {
            "type": "Container",
            "style": "good",
            "items": [
                {
                    "type": "ColumnSet",
                    "columns": [
                        {
                            "type": "Column",
                            "width": "auto",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "✅",
                                    "size": "extraLarge",
                                    "spacing": "none"
                                }
                            ]
                        },
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "Query Results",
                                    "weight": "bolder",
                                    "size": "large",
                                    "spacing": "none"
                                },
                                {
                                    "type": "TextBlock",
                                    "text": f"Found {count:,} result(s)",
                                    "size": "small",
                                    "color": "good",
                                    "spacing": "none",
                                    "isSubtle": True
                                }
                            ]
                        },
                        {
                            "type": "Column",
                            "width": "auto",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": datetime.now().strftime("%I:%M %p"),
                                    "size": "small",
                                    "horizontalAlignment": "right",
                                    "isSubtle": True
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        card["body"].append(header)
        
        # SQL Query Section (Collapsible)
        sql_container = {
            "type": "Container",
            "spacing": "medium",
            "items": [
                {
                    "type": "TextBlock",
                    "text": "📝 Generated SQL",
                    "weight": "bolder",
                    "size": "medium",
                    "color": "accent"
                },
                {
                    "type": "TextBlock",
                    "text": f"```sql\n{sql}\n```",
                    "wrap": True,
                    "fontType": "monospace",
                    "spacing": "small",
                    "color": "default"
                }
            ]
        }
        card["body"].append(sql_container)
        
        # Results Section
        if count == 0:
            no_results = {
                "type": "Container",
                "spacing": "medium",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "ℹ️ No rows returned",
                        "wrap": True,
                        "color": "warning"
                    }
                ]
            }
            card["body"].append(no_results)
        else:
            # Create table for results
            results_container = AdaptiveCardBuilder._create_results_table(rows, count)
            card["body"].append(results_container)
        
        # Metadata Footer
        footer_facts = []
        if execution_time:
            footer_facts.append({
                "title": "⏱️ Execution Time",
                "value": f"{execution_time:.2f}s"
            })
        if token_usage:
            total_tokens = token_usage.get("total", 0)
            footer_facts.append({
                "title": "🎫 Tokens Used",
                "value": str(total_tokens)
            })
            
        if footer_facts:
            footer = {
                "type": "FactSet",
                "facts": footer_facts,
                "spacing": "medium"
            }
            card["body"].append(footer)
        
        # Action Buttons
        actions = []
        
        # Re-run query button
        if user_query:
            actions.append({
                "type": "Action.Submit",
                "title": "🔄 Run Again",
                "data": {
                    "action": "rerun",
                    "query": user_query
                }
            })
        
        # Export button (if results exist)
        if count > 0:
            actions.append({
                "type": "Action.Submit",
                "title": "📋 Copy Results",
                "data": {
                    "action": "copy",
                    "sql": sql,
                    "count": count
                }
            })
        
        # Modify query button
        actions.append({
            "type": "Action.Submit",
            "title": "✏️ Modify Query",
            "data": {
                "action": "modify",
                "sql": sql
            }
        })
        
        if actions:
            card["actions"] = actions
        
        return card
    
    @staticmethod
    def _create_results_table(rows: List[Dict[str, Any]], total_count: int, max_rows: int = 10) -> Dict[str, Any]:
        """
        Create a formatted table container for query results.
        
        Args:
            rows: List of result rows
            total_count: Total number of rows
            max_rows: Maximum rows to display
            
        Returns:
            Container dict with table
        """
        display_rows = rows[:max_rows]
        has_more = total_count > max_rows
        
        container = {
            "type": "Container",
            "spacing": "medium",
            "items": [
                {
                    "type": "TextBlock",
                    "text": "📊 Results",
                    "weight": "bolder",
                    "size": "medium"
                }
            ]
        }
        
        if not display_rows:
            return container
        
        # Get columns
        columns = list(display_rows[0].keys())
        
        # Create table using FactSet (simple key-value display for each row)
        for idx, row in enumerate(display_rows, 1):
            row_container = {
                "type": "Container",
                "spacing": "small",
                "separator": idx > 1,
                "items": [
                    {
                        "type": "TextBlock",
                        "text": f"**Row {idx}**",
                        "size": "small",
                        "weight": "bolder"
                    },
                    {
                        "type": "FactSet",
                        "facts": [
                            {
                                "title": str(col),
                                "value": str(row.get(col, ""))
                            }
                            for col in columns
                        ]
                    }
                ]
            }
            container["items"].append(row_container)
        
        # Add "show more" message if needed
        if has_more:
            more_message = {
                "type": "TextBlock",
                "text": f"_Showing first {max_rows} of {total_count:,} results. {total_count - max_rows:,} more rows available._",
                "wrap": True,
                "size": "small",
                "color": "accent",
                "spacing": "medium"
            }
            container["items"].append(more_message)
        
        return container
    
    @staticmethod
    def create_error_card(
        error_message: str,
        sql: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        user_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an Adaptive Card for error messages.
        
        Args:
            error_message: Error description
            sql: Generated SQL that failed (if available)
            suggestions: List of suggested fixes
            user_query: Original user question
            
        Returns:
            Adaptive Card JSON dict
        """
        card = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.5",
            "body": []
        }
        
        # Header Section (Red - Error)
        header = {
            "type": "Container",
            "style": "attention",
            "items": [
                {
                    "type": "ColumnSet",
                    "columns": [
                        {
                            "type": "Column",
                            "width": "auto",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "❌",
                                    "size": "extraLarge",
                                    "spacing": "none"
                                }
                            ]
                        },
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "Execution Error",
                                    "weight": "bolder",
                                    "size": "large",
                                    "spacing": "none"
                                },
                                {
                                    "type": "TextBlock",
                                    "text": "Query failed to execute",
                                    "size": "small",
                                    "color": "attention",
                                    "spacing": "none",
                                    "isSubtle": True
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        card["body"].append(header)
        
        # Error Message
        error_container = {
            "type": "Container",
            "spacing": "medium",
            "items": [
                {
                    "type": "TextBlock",
                    "text": "**Error Details:**",
                    "weight": "bolder",
                    "size": "medium"
                },
                {
                    "type": "TextBlock",
                    "text": error_message,
                    "wrap": True,
                    "spacing": "small",
                    "color": "attention"
                }
            ]
        }
        card["body"].append(error_container)
        
        # SQL Query (if available)
        if sql:
            sql_container = {
                "type": "Container",
                "spacing": "medium",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "**Generated SQL:**",
                        "weight": "bolder"
                    },
                    {
                        "type": "TextBlock",
                        "text": f"```sql\n{sql}\n```",
                        "wrap": True,
                        "fontType": "monospace",
                        "spacing": "small",
                        "color": "default"
                    }
                ]
            }
            card["body"].append(sql_container)
        
        # Suggestions
        if suggestions:
            suggestions_container = {
                "type": "Container",
                "spacing": "medium",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": "💡 **Try This:**",
                        "weight": "bolder",
                        "color": "accent"
                    }
                ]
            }
            
            for suggestion in suggestions:
                suggestions_container["items"].append({
                    "type": "TextBlock",
                    "text": f"• {suggestion}",
                    "wrap": True,
                    "spacing": "small"
                })
            
            card["body"].append(suggestions_container)
        
        # Action Buttons
        actions = []
        
        if user_query:
            actions.append({
                "type": "Action.Submit",
                "title": "🔄 Try Again",
                "data": {
                    "action": "retry",
                    "query": user_query
                }
            })
        
        actions.append({
            "type": "Action.Submit",
            "title": "💬 Get Help",
            "data": {
                "action": "help"
            }
        })
        
        if actions:
            card["actions"] = actions
        
        return card
    
    @staticmethod
    def create_welcome_card() -> Dict[str, Any]:
        """
        Create an interactive welcome card with quick actions.
        
        Returns:
            Adaptive Card JSON dict
        """
        card = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.5",
            "body": [
                {
                    "type": "Container",
                    "style": "emphasis",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "👋 Welcome to NL2SQL Bot!",
                            "size": "extraLarge",
                            "weight": "bolder",
                            "horizontalAlignment": "center"
                        },
                        {
                            "type": "TextBlock",
                            "text": "Ask database questions in natural language",
                            "size": "medium",
                            "horizontalAlignment": "center",
                            "spacing": "none",
                            "isSubtle": True
                        }
                    ]
                },
                {
                    "type": "Container",
                    "spacing": "large",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "**🚀 Quick Start Examples:**",
                            "weight": "bolder",
                            "size": "medium"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• How many customers do we have?",
                            "wrap": True,
                            "spacing": "small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• Show me loans with balance over $10,000",
                            "wrap": True,
                            "spacing": "small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• What's the average loan amount by state?",
                            "wrap": True,
                            "spacing": "small"
                        },
                        {
                            "type": "TextBlock",
                            "text": "• List top 10 customers by balance",
                            "wrap": True,
                            "spacing": "small"
                        }
                    ]
                },
                {
                    "type": "Container",
                    "spacing": "medium",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "**✨ Features:**",
                            "weight": "bolder"
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {"title": "🧠", "value": "AI-powered SQL generation"},
                                {"title": "⚡", "value": "Real-time query execution"},
                                {"title": "📊", "value": "Formatted results in cards"},
                                {"title": "🔄", "value": "Interactive follow-ups"}
                            ]
                        }
                    ]
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "📋 Show Commands",
                    "data": {"action": "help"}
                },
                {
                    "type": "Action.Submit",
                    "title": "🗂️ View Schema",
                    "data": {"action": "schema"}
                },
                {
                    "type": "Action.Submit",
                    "title": "📝 Sample Query",
                    "data": {"action": "sample", "query": "How many customers do we have?"}
                }
            ]
        }
        
        return card
    
    @staticmethod
    def create_help_card() -> Dict[str, Any]:
        """
        Create a help card with commands and examples.
        
        Returns:
            Adaptive Card JSON dict
        """
        card = {
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.5",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "📚 NL2SQL Bot Help",
                    "size": "extraLarge",
                    "weight": "bolder"
                },
                {
                    "type": "Container",
                    "spacing": "medium",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "**How It Works:**",
                            "weight": "bolder",
                            "size": "medium"
                        },
                        {
                            "type": "TextBlock",
                            "text": "1. 🧠 **Understand** your natural language question\n2. 💡 **Generate** SQL query using Azure AI\n3. ⚡ **Execute** query against the database\n4. 📊 **Format** and display results beautifully",
                            "wrap": True,
                            "spacing": "small"
                        }
                    ]
                },
                {
                    "type": "Container",
                    "spacing": "medium",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "**Example Questions:**",
                            "weight": "bolder",
                            "size": "medium"
                        },
                        {
                            "type": "ColumnSet",
                            "columns": [
                                {
                                    "type": "Column",
                                    "width": "auto",
                                    "items": [{"type": "TextBlock", "text": "📊", "spacing": "none"}]
                                },
                                {
                                    "type": "Column",
                                    "width": "stretch",
                                    "items": [{"type": "TextBlock", "text": "**Count:** How many customers do we have?", "wrap": True, "spacing": "none"}]
                                }
                            ],
                            "spacing": "small"
                        },
                        {
                            "type": "ColumnSet",
                            "columns": [
                                {
                                    "type": "Column",
                                    "width": "auto",
                                    "items": [{"type": "TextBlock", "text": "🔍", "spacing": "none"}]
                                },
                                {
                                    "type": "Column",
                                    "width": "stretch",
                                    "items": [{"type": "TextBlock", "text": "**Filter:** Show loans in California", "wrap": True, "spacing": "none"}]
                                }
                            ],
                            "spacing": "small"
                        },
                        {
                            "type": "ColumnSet",
                            "columns": [
                                {
                                    "type": "Column",
                                    "width": "auto",
                                    "items": [{"type": "TextBlock", "text": "📈", "spacing": "none"}]
                                },
                                {
                                    "type": "Column",
                                    "width": "stretch",
                                    "items": [{"type": "TextBlock", "text": "**Aggregate:** Average loan amount by state", "wrap": True, "spacing": "none"}]
                                }
                            ],
                            "spacing": "small"
                        },
                        {
                            "type": "ColumnSet",
                            "columns": [
                                {
                                    "type": "Column",
                                    "width": "auto",
                                    "items": [{"type": "TextBlock", "text": "🏆", "spacing": "none"}]
                                },
                                {
                                    "type": "Column",
                                    "width": "stretch",
                                    "items": [{"type": "TextBlock", "text": "**Top N:** Top 10 customers by balance", "wrap": True, "spacing": "none"}]
                                }
                            ],
                            "spacing": "small"
                        }
                    ]
                },
                {
                    "type": "Container",
                    "spacing": "medium",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "**Special Commands:**",
                            "weight": "bolder",
                            "size": "medium"
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {"title": "/help", "value": "Show this help message"},
                                {"title": "/about", "value": "About this bot"},
                                {"title": "/schema", "value": "View database schema"}
                            ]
                        }
                    ]
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Try Example",
                    "data": {"action": "sample", "query": "How many customers do we have?"}
                }
            ]
        }
        
        return card


# Helper function to convert card to Teams attachment format
def create_card_attachment(card: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert an Adaptive Card dict to Teams attachment format.
    
    Args:
        card: Adaptive Card JSON dict
        
    Returns:
        Teams attachment dict
    """
    return {
        "contentType": "application/vnd.microsoft.card.adaptive",
        "content": card
    }
