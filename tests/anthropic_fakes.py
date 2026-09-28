"""Fake Anthropic client objects for testing agents without a live API call.

Both News Event Agent and Explanation Agent take their Anthropic client as
a constructor/call argument specifically so tests can inject one of these
instead of a real ``anthropic.Anthropic()``.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class FakeParsedResponse:
    parsed_output: Any


class FakeParseMessages:
    """Stands in for ``client.messages`` when only ``.parse()`` is used."""

    def __init__(self, parsed_output: Any) -> None:
        self._parsed_output = parsed_output
        self.calls: list[dict] = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return FakeParsedResponse(parsed_output=self._parsed_output)


class FakeParseClient:
    def __init__(self, parsed_output: Any) -> None:
        self.messages = FakeParseMessages(parsed_output)


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeCreateResponse:
    content: list[FakeTextBlock]


class FakeCreateMessages:
    """Stands in for ``client.messages`` when only ``.create()`` is used."""

    def __init__(self, text: str) -> None:
        self._text = text
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeCreateResponse(content=[FakeTextBlock(text=self._text)])


class FakeCreateClient:
    def __init__(self, text: str) -> None:
        self.messages = FakeCreateMessages(text)
