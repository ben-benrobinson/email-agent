"""LLM client for generating email responses."""

from anthropic import Anthropic

from .config import Config


def generate_reply(
    from_addr: str,
    subject: str,
    original_body: str,
    sender_name: str = "",
) -> str:
    """
    Generate a reply to an email using Claude (Anthropic).
    """
    client = Anthropic(api_key=Config.anthropic_api_key)

    base_instructions = """You are a helpful email assistant. You write concise, professional, 
and friendly email replies. Match the tone of the incoming email when appropriate. 
Keep replies focused and avoid unnecessary length. Do not include email headers 
(From, To, Subject) - output only the body of the reply."""

    knowledge_block = ""
    if Config.knowledge:
        knowledge_block = f"""

Use the following facts about the user when relevant to personalize responses:
{Config.knowledge}
"""

    system_prompt = base_instructions + knowledge_block

    user_content = f"""Reply to this email:

From: {from_addr}
Subject: {subject}

{original_body or "(no body)"}

Write a natural reply:"""

    response = client.messages.create(
        model=Config.anthropic_model,
        max_tokens=500,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )

    if response.content and response.content[0].type == "text":
        return response.content[0].text.strip()
    return ""
