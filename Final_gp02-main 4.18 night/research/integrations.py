"""Crawl4AI、Ollama 与财经资讯源配置（各 Phase 可调用的统一接口契约，环境变量可覆盖）。"""

from __future__ import annotations

import os
from typing import List

from pydantic import BaseModel, Field


class ExternalIntegrations(BaseModel):
    crawl4ai_base_url: str = Field(description="Crawl4AI 或兼容抓取服务基址")
    ollama_base_url: str = Field(description="Ollama 本地 API 基址")
    ollama_model: str = Field(description="默认对话/摘要模型名")
    news_finance_urls: List[str] = Field(description="新闻与财经资讯入口（仅配置，实际抓取走 Crawl4AI/asyncio）")
    news_history_finance_urls: List[str] = Field(
        description="补充 hub/专题页（更易混有往期标题；环境变量 NEWS_HISTORY_FINANCE_URLS）"
    )


def load_external_integrations() -> ExternalIntegrations:
    raw_news = os.environ.get(
        "NEWS_FINANCE_URLS",
        "https://www.sec.gov/news/press-releases,"
        "https://www.reuters.com/markets/,"
        "https://www.bloomberg.com/markets,"
        "https://finance.yahoo.com/news/,"
        "https://www.cnbc.com/markets/,"
        "https://www.ft.com/markets",
    )
    urls = [u.strip() for u in raw_news.split(",") if u.strip()]
    raw_hist = os.environ.get(
        "NEWS_HISTORY_FINANCE_URLS",
        # AP News: multi-week archive with "April 7, 2026"-style dates
        "https://apnews.com/hub/financial-markets,"
        # AP geopolitics / world news (oil, sanctions, war)
        "https://apnews.com/hub/world-news,"
        # Guardian economics: "14 Apr 2026"-style dates 2-4 weeks back
        "https://www.theguardian.com/business/economics,"
        # BBC business: "April 06, 2026"-style dates up to a month back
        "https://www.bbc.com/news/business,"
        # CNBC world economy
        "https://www.cnbc.com/world-economy/,"
        # NYT business archives listing
        "https://www.nytimes.com/section/business",
    )
    hist_urls = [u.strip() for u in raw_hist.split(",") if u.strip()]
    return ExternalIntegrations(
        crawl4ai_base_url=os.environ.get("CRAWL4AI_BASE_URL", "http://127.0.0.1:11235"),
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        ollama_model=os.environ.get("OLLAMA_MODEL", "llama3"),
        news_finance_urls=urls,
        news_history_finance_urls=hist_urls,
    )
