"""Notion block rendering tests."""

from eaw.infrastructure.connectors.notion_client import NotionClient


def test_block_to_markdown_shapes() -> None:
    # Client requires token; only use helpers via instance
    client = NotionClient("secret_test_token_xxxxx")
    para = {
        "type": "paragraph",
        "paragraph": {"rich_text": [{"plain_text": "Hello world"}]},
    }
    assert client._block_to_text(para) == "Hello world"
    h1 = {
        "type": "heading_1",
        "heading_1": {"rich_text": [{"plain_text": "Title"}]},
    }
    assert client._block_to_text(h1) == "# Title"
    bullet = {
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"plain_text": "Item"}]},
    }
    assert client._block_to_text(bullet) == "- Item"


def test_extract_title() -> None:
    item = {
        "object": "page",
        "properties": {
            "Name": {
                "type": "title",
                "title": [{"plain_text": "Employee Handbook"}],
            }
        },
    }
    assert NotionClient._extract_title(item) == "Employee Handbook"
