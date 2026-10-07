"""Use Claude to turn raw API documentation into a structured IntegrationProfile.

Claude is forced to answer through a tool whose input schema is the
ExtractedProfile model, so the output is always valid, typed JSON.
"""
from __future__ import annotations

import os

from .schema import ExtractedProfile, IntegrationProfile

DEFAULT_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5")

SYSTEM = """You are an integrations analyst for a marketing platform that connects to
brands' martech tools (ecommerce platforms, CRMs, loyalty, helpdesk, analytics).
Read the partner's API documentation and record what an engineer needs to build an
integration that syncs customers, orders, products, and events.

Rules:
- Only state what the documentation supports. If something is not covered, leave
  the field empty or false and add it to open_questions instead of guessing.
- Prefer endpoints for customers/contacts, orders, products/catalog, events, and webhooks.
- Keep descriptions short and concrete."""

TOOL_NAME = "record_integration_profile"


def _tool() -> dict:
    return {
        "name": TOOL_NAME,
        "description": "Record the structured integration profile for this partner.",
        "input_schema": ExtractedProfile.model_json_schema(),
    }


def extract_profile(partner: str, docs_url: str, docs_text: str, client=None, model: str = DEFAULT_MODEL) -> IntegrationProfile:
    if client is None:
        import anthropic

        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY

    msg = client.messages.create(
        model=model,
        max_tokens=4000,
        system=SYSTEM,
        tools=[_tool()],
        tool_choice={"type": "tool", "name": TOOL_NAME},
        messages=[{
            "role": "user",
            "content": f"Partner: {partner}\nDocs URL: {docs_url}\n\n<docs>\n{docs_text}\n</docs>",
        }],
    )
    tool_use = next(b for b in msg.content if getattr(b, "type", None) == "tool_use")
    extracted = ExtractedProfile.model_validate(tool_use.input)
    return IntegrationProfile(**extracted.model_dump(), docs_url=docs_url)
