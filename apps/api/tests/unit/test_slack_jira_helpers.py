"""Slack/Jira helper unit tests (no network)."""

from eaw.infrastructure.connectors.jira_client import JiraClient
from eaw.infrastructure.connectors.slack_client import SlackClient


def test_slack_messages_to_text() -> None:
    msgs = [
        {"user": "U1", "text": "Ship it", "ts": "1"},
        {"subtype": "channel_join", "text": "joined", "ts": "2"},
        {"user": "U2", "text": "Blocked on API", "ts": "3"},
    ]
    text = SlackClient.messages_to_text(msgs, channel_name="eng")
    assert "# Slack channel #eng" in text
    assert "Ship it" in text
    assert "Blocked on API" in text
    assert "joined" not in text


def test_jira_adf_to_text() -> None:
    adf = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Hello "}, {"type": "text", "text": "Jira"}],
            }
        ],
    }
    assert "Hello Jira" in JiraClient.adf_to_text(adf)


def test_jira_issue_markdown() -> None:
    issue = {
        "key": "ENG-1",
        "fields": {
            "summary": "Add login",
            "status": {"name": "In Progress"},
            "issuetype": {"name": "Story"},
            "assignee": {"displayName": "Ada"},
            "priority": {"name": "High"},
            "labels": ["auth"],
            "description": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Implement JWT login"}],
                    }
                ],
            },
            "comment": {"comments": []},
        },
    }
    md = JiraClient.issue_to_markdown(issue)
    assert "ENG-1" in md
    assert "Implement JWT login" in md
    assert "Ada" in md
