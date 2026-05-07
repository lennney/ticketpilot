"""Chat support module for TicketPilot AI customer service copilot."""

from ticketpilot.chat.adapter import (
    chat_display_to_context_metadata,
    evidence_to_display_items,
    ticket_output_to_chat_display,
)
from ticketpilot.chat.schemas import (
    ChatContext,
    ChatDisplay,
    ChatMessage,
    ChatRole,
    ChatSession,
    ChatState,
    EvidenceDisplayItem,
    ReviewDecisionDisplay,
    append_message,
    update_context_from_message,
)

__all__ = [
    "ChatContext",
    "ChatDisplay",
    "ChatMessage",
    "ChatRole",
    "ChatSession",
    "ChatState",
    "EvidenceDisplayItem",
    "ReviewDecisionDisplay",
    "append_message",
    "update_context_from_message",
    "ticket_output_to_chat_display",
    "evidence_to_display_items",
    "chat_display_to_context_metadata",
]
