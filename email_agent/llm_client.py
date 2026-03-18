"""LLM client for generating email responses."""

import json

from anthropic import Anthropic

from .config import Config
from .feedback_store import get_all_feedback


def generate_reply(
    from_addr: str,
    subject: str,
    original_body: str,
    sender_name: str = "",
    tone_instruction: str = "",
) -> str:
    """
    Generate a reply to an email using Claude (Anthropic).
    """
    client = Anthropic(api_key=Config.anthropic_api_key)

    base_instructions = """You are a helpful email assistant. You write concise, professional, 
and friendly email replies. Match the tone of the incoming email when appropriate. 
Keep replies focused and avoid unnecessary length. Do not include email headers 
(From, To, Subject) - output only the body of the reply.

Be proactively helpful: when your reply naturally implies follow-up or practical next steps, include them in the same message. For example:
- When suggesting a meal or dinner, also add a short shopping list for that dish so the recipient can cook it.
- When suggesting an activity, include what to bring or how to prepare if relevant.
- When giving a recommendation (recipe, place, etc.), add any concrete next steps that would be useful (ingredients, directions, booking link, etc.).
Stay concise; only add these extras when they clearly help the recipient act on your suggestion."""

    knowledge_block = ""
    if Config.knowledge:
        knowledge_block = f"""

Use the following facts about the user when relevant to personalize responses:
{Config.knowledge}
"""

    tone_block = ""
    if tone_instruction:
        tone_block = f"""

Tone/style for this reply: {tone_instruction}
"""

    feedback_block = ""
    feedback_text = get_all_feedback()
    if feedback_text:
        feedback_block = f"""

The user has given the following feedback. Use it to improve your suggestions and style in this and future replies (e.g. what they liked or disliked):
{feedback_text}
"""

    system_prompt = base_instructions + knowledge_block + tone_block + feedback_block

    user_content = f"""Reply to this email:

From: {from_addr}
Subject: {subject}

{original_body or "(no body)"}

Write a natural reply:"""

    response = client.messages.create(
        model=Config.anthropic_model,
        max_tokens=800,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )

    if response.content and response.content[0].type == "text":
        return response.content[0].text.strip()
    return ""


def extract_calendar_proposals(*, emails: list[dict], now_iso: str) -> list[dict]:
    """
    Given a list of emails, extract proposed dates/times suitable for a calendar digest.

    Input email dict keys (expected):
      - from, subject, date, body

    Returns a list of dicts:
      - from: str
      - subject: str
      - description: str (brief event description)
      - proposed_times: list[str] (date/time options as readable strings)
    """
    if not emails:
        return []

    client = Anthropic(api_key=Config.anthropic_api_key)

    system = """You extract scheduling proposals from emails.
You will be given a batch of emails (sender, subject, date, body). For each email:
- If it suggests meeting times/dates (explicit or implicit), extract the proposed options.
- If there are no proposed dates/times, omit that email from the output.

Output MUST be valid JSON only (no surrounding prose), with this exact shape:
{
  "items": [
    {
      "from": "sender@example.com",
      "subject": "...",
      "description": "brief event description",
      "proposed_times": ["...", "..."]
    }
  ]
}

Guidelines:
- Prefer concrete times/dates. If relative like \"tomorrow afternoon\", keep it as-is (don't guess a calendar date).
- Keep description short and useful (e.g. \"Coffee chat\" / \"Interview\" / \"Dinner\" / \"Call\").
- proposed_times should be human-readable strings; do not invent details.
"""

    user = json.dumps({"now": now_iso, "emails": emails}, ensure_ascii=False)

    resp = client.messages.create(
        model=Config.anthropic_model,
        max_tokens=900,
        system=system,
        messages=[{"role": "user", "content": user}],
    )

    if not (resp.content and resp.content[0].type == "text"):
        return []

    text = resp.content[0].text.strip()
    try:
        data = json.loads(text)
        items = data.get("items", [])
        return items if isinstance(items, list) else []
    except json.JSONDecodeError:
        return []
