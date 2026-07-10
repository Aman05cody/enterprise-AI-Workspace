"""Echo LLM grounding behavior tests."""

from eaw.application.ports.llm import ChatMessage
from eaw.infrastructure.llm.echo_llm import EchoLLMAdapter


def test_insufficient_context() -> None:
    llm = EchoLLMAdapter()
    result = llm.complete(
        [
            ChatMessage(role="system", content="INSUFFICIENT_CONTEXT NO_RELEVANT_CONTEXT"),
            ChatMessage(role="user", content="What is the policy?"),
        ]
    )
    assert "don't have enough information" in result.content.lower()


def test_grounded_answer_streams() -> None:
    llm = EchoLLMAdapter()
    system = """SYSTEM
CONTEXT:
[1] Handbook
Remote work is allowed three days per week.

[2] Benefits
Employees receive 20 days PTO.
"""
    chunks = list(
        llm.stream(
            [
                ChatMessage(role="system", content=system),
                ChatMessage(role="user", content="Tell me about remote work"),
            ]
        )
    )
    text = "".join(chunks)
    assert "Handbook" in text or "Remote" in text or "sources" in text.lower()
