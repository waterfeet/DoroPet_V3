import json
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

import requests
from bs4 import BeautifulSoup

from src.agent.core.tool import Tool, ToolSchema, ToolCategory, ToolResult
from src.agent.core.context import ToolCallContext, ToolPermission

logger = logging.getLogger("DoroPet.Agent")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"


class SearchBaiduTool(Tool):
    schema = ToolSchema(
        name="search_baidu",
        description="Search for real-time information on the internet using Baidu.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search keywords."}
            },
            "required": ["query"],
        },
        category=ToolCategory.SEARCH,
        required_permissions=[ToolPermission.NETWORK],
        timeout_ms=15000,
        max_output_chars=8000,
    )

    async def execute(self, context: ToolCallContext, query: str = "", **kwargs) -> ToolResult:
        if not query:
            return ToolResult(tool_name=self.schema.name, success=False, error="Query is required.")

        try:
            url = "https://www.baidu.com/s"
            headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
            response = requests.get(url, params={"wd": query}, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            results = []

            for item in soup.select(".result.c-container, .result-op.c-container"):
                try:
                    title_elem = item.select_one("h3")
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)
                    link = title_elem.select_one("a")["href"] if title_elem.select_one("a") else ""

                    abstract_elem = item.select_one(".c-abstract") or item.select_one(".c-font-normal")
                    snippet = abstract_elem.get_text(strip=True) if abstract_elem else ""

                    if title and link:
                        results.append({"title": title, "link": link, "snippet": snippet})
                    if len(results) >= 5:
                        break
                except Exception:
                    continue

            return ToolResult(
                tool_name=self.schema.name,
                success=True,
                data={"query": query, "results": results, "count": len(results)},
            )
        except Exception as e:
            return ToolResult(tool_name=self.schema.name, success=False, error=str(e))


class SearchBingTool(Tool):
    schema = ToolSchema(
        name="search_bing",
        description="Search for real-time information using Bing.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search keywords."}
            },
            "required": ["query"],
        },
        category=ToolCategory.SEARCH,
        required_permissions=[ToolPermission.NETWORK],
        timeout_ms=15000,
        max_output_chars=8000,
    )

    async def execute(self, context: ToolCallContext, query: str = "", **kwargs) -> ToolResult:
        if not query:
            return ToolResult(tool_name=self.schema.name, success=False, error="Query is required.")

        try:
            url = "https://cn.bing.com/search"
            headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
            response = requests.get(url, params={"q": query}, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            results = []

            for item in soup.select(".b_algo"):
                try:
                    title_elem = item.select_one("h2 a")
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get("href", "")

                    snippet_elem = item.select_one(".b_caption p")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    if title and link:
                        results.append({"title": title, "link": link, "snippet": snippet})
                    if len(results) >= 5:
                        break
                except Exception:
                    continue

            return ToolResult(
                tool_name=self.schema.name,
                success=True,
                data={"query": query, "results": results, "count": len(results)},
            )
        except Exception as e:
            return ToolResult(tool_name=self.schema.name, success=False, error=str(e))


class VisitWebpageTool(Tool):
    schema = ToolSchema(
        name="visit_webpage",
        description="Visit a URL and extract its text content.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to visit."}
            },
            "required": ["url"],
        },
        category=ToolCategory.SEARCH,
        required_permissions=[ToolPermission.NETWORK],
        timeout_ms=15000,
        max_output_chars=4000,
    )

    async def execute(self, context: ToolCallContext, url: str = "", **kwargs) -> ToolResult:
        if not url:
            return ToolResult(tool_name=self.schema.name, success=False, error="URL is required.")

        if not url.startswith("http"):
            url = "https://" + url

        if not (url.startswith("https://") or url.startswith("http://")):
            return ToolResult(tool_name=self.schema.name, success=False, error="Invalid URL scheme.")

        try:
            headers = {"User-Agent": USER_AGENT}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            if response.encoding == "ISO-8859-1":
                response.encoding = response.apparent_encoding

            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "meta", "noscript", "svg", "iframe"]):
                tag.extract()

            text = soup.get_text(separator="\n", strip=True)
            content = text[:4000] + ("..." if len(text) > 4000 else "")

            if not content:
                content = "No readable text found on this page."

            return ToolResult(
                tool_name=self.schema.name,
                success=True,
                data={"url": url, "content": content, "content_length": len(text)},
            )
        except requests.exceptions.Timeout:
            return ToolResult(tool_name=self.schema.name, success=False, error=f"Timeout visiting {url}")
        except requests.exceptions.RequestException as e:
            return ToolResult(tool_name=self.schema.name, success=False, error=f"Failed to visit {url}: {str(e)}")
        except Exception as e:
            return ToolResult(tool_name=self.schema.name, success=False, error=str(e))


_search_tools = [SearchBaiduTool(), SearchBingTool(), VisitWebpageTool()]


def register_search_tools(registry=None):
    from src.agent.core.tool import ToolRegistry
    reg = registry or ToolRegistry.get_instance()
    for tool in _search_tools:
        reg.register(tool)
