"""Prompt templates for grounded enterprise chat."""

from __future__ import annotations

from dataclasses import dataclass


SYSTEM_GROUNDED = """You are an enterprise knowledge assistant for a company workspace.
You must answer ONLY using the provided CONTEXT sources.
Rules:
1. If the context is insufficient, say you don't have enough information. Do not invent policies, numbers, or document titles.
2. Cite sources using [n] markers that match the CONTEXT list.
3. Be concise, professional, and accurate.
4. Prefer quoting key facts from sources over speculation.
"""


SYSTEM_INSUFFICIENT = """You are an enterprise knowledge assistant.
NO_RELEVANT_CONTEXT
INSUFFICIENT_CONTEXT
There is no reliable retrieved context for this question.
Instruct the user that you cannot answer from the knowledge base and must not invent facts.
Do not fabricate citations.
"""


@dataclass
class BuiltPrompt:
    system: str
    insufficient: bool
    context_block: str


def build_context_block(
    passages: list[dict],
) -> str:
    """
    passages: [{rank, title, content, score}]
    """
    lines: list[str] = ["CONTEXT:"]
    for p in passages:
        rank = p["rank"]
        title = p.get("title") or "Source"
        content = (p.get("content") or "").strip()
        lines.append(f"[{rank}] {title}")
        lines.append(content)
        lines.append("")
    return "\n".join(lines).strip()


def build_system_prompt(
    *,
    passages: list[dict],
    memory_summary: str | None,
    insufficient: bool,
) -> BuiltPrompt:
    if insufficient or not passages:
        return BuiltPrompt(
            system=SYSTEM_INSUFFICIENT,
            insufficient=True,
            context_block="",
        )
    ctx = build_context_block(passages)
    memory = ""
    if memory_summary:
        memory = f"\n\nCONVERSATION MEMORY SUMMARY:\n{memory_summary.strip()}\n"
    system = f"{SYSTEM_GROUNDED}\n\n{ctx}{memory}"
    return BuiltPrompt(system=system, insufficient=False, context_block=ctx)


def suggest_followups(question: str, answer: str, has_context: bool) -> list[str]:
    if not has_context:
        return [
            "Which documents should I upload for this topic?",
            "Can you search a different knowledge base?",
        ]
    q = question.strip()
    base = [
        f"Can you elaborate on the most important point about: {q[:80]}?",
        "What related policies or exceptions exist?",
        "Summarize the sources in bullet points.",
    ]
    return base[:3]
