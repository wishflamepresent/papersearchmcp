import asyncio
import json
import unittest
from datetime import UTC, datetime
from typing import List

from paper_search_mcp import server
from paper_search_mcp.paper import Paper


class DummySearcher:
    """Minimal searcher used to simulate search/fetch behaviour in tests."""

    def __init__(self) -> None:
        self._papers = self._build_papers()

    def _build_papers(self) -> List[Paper]:
        now = datetime.now(UTC)
        return [
            Paper(
                paper_id=f"dummy-{idx}",
                title=f"Dummy Paper {idx}",
                authors=["Test Author"],
                abstract=f"Abstract for paper {idx}.",
                doi=f"10.1000/dummy{idx}",
                published_date=now,
                pdf_url=f"https://example.com/paper{idx}.pdf",
                url=f"https://example.com/paper{idx}",
                source="dummy",
            )
            for idx in range(3)
        ]

    def search(self, query: str, max_results: int = 10, **_: str) -> List[Paper]:
        return self._papers[:max_results]

    def read_paper(self, paper_id: str, save_path: str = "./downloads") -> str:
        return f"Full text for {paper_id} stored in {save_path}."


class TestDeepResearchTools(unittest.TestCase):
    def setUp(self) -> None:
        self.original_searchers = server.SEARCHERS.copy()
        server.SEARCHERS.clear()
        server.SEARCH_CACHE.clear()
        server.SEARCHERS["dummy"] = DummySearcher()

    def tearDown(self) -> None:
        server.SEARCHERS.clear()
        server.SEARCHERS.update(self.original_searchers)
        server.SEARCH_CACHE.clear()

    def test_search_returns_call_tool_result(self) -> None:
        result = asyncio.run(server.search("quantum", max_results=2))
        self.assertEqual(len(result.content), 1)
        payload = json.loads(result.content[0].text)
        self.assertIn("results", payload)
        self.assertLessEqual(len(payload["results"]), 2)
        first_result = payload["results"][0]
        self.assertTrue(first_result["id"].startswith("dummy:"))
        self.assertIn("title", first_result)
        self.assertIn("url", first_result)

    def test_fetch_uses_cached_metadata(self) -> None:
        search_result = asyncio.run(server.search("dummy", max_results=1))
        payload = json.loads(search_result.content[0].text)
        document_id = payload["results"][0]["id"]

        fetch_result = asyncio.run(server.fetch(document_id))
        self.assertEqual(len(fetch_result.content), 1)
        fetch_payload = json.loads(fetch_result.content[0].text)
        self.assertEqual(fetch_payload["id"], document_id)
        self.assertIn("text", fetch_payload)
        self.assertIn("metadata", fetch_payload)
        metadata = fetch_payload["metadata"]
        self.assertEqual(metadata["source"], "dummy")
        self.assertIn("authors", metadata)
        self.assertTrue(fetch_payload["text"].startswith("Full text"))


if __name__ == "__main__":
    unittest.main()
