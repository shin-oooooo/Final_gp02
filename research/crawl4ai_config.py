"""Crawl4AI 语义锚定：风险种子词库（Phase 0 硬编码 search / 审计用）。"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from urllib.parse import quote_plus

# Phase0.md §3：地缘 /供给冲击 / 科技供应链 — 供 RSS 检索、审计与 VADER 隐性映射对齐
RISK_SEARCH_SEEDS: List[str] = [
    "Missile",
    "Blockade",
    "Ceasefire",
    "Sanctions",
    "Crude Oil Supply",
    "Strait of Hormuz",
    "Iran",
    "Taiwan",
    "semiconductor",
    "export control",
    "chip ban",
    "oil embargo",
    "geopolitical risk",
]

# Google News RSS：分束查询，避免单 URL 过长；与种子语义同向
GEO_NEWS_QUERY_BUNDLES: List[str] = [
    "Missile OR blockade OR ceasefire OR sanctions OR crude oil OR "
    "Hormuz OR Iran oil OR embargo OR oil supply OR strait",
    "Taiwan OR TSMC OR semiconductor OR export control OR chip ban OR "
    "ASML OR China chip OR lithography OR foundry",
    "Middle East OR oil shock OR energy crisis OR geopolitical risk OR "
    "war OR missile OR naval OR sanctions",
]

# Crawl4AI 标题初筛：至少命中下列之一才视为「可能新闻」（全小写子串匹配）。
# 与 :data:`RISK_SEARCH_SEEDS` 同向但更细，覆盖宏观 / 市场 / 地缘 / 科技供应链等。
#
# **2026-04 精简记录**（删除以下过泛词以消除 crawl4ai 页面导航泄漏）：
#
# * ``rates`` / ``yield`` / ``growth``（命中 "Lowest mortgage rates" / "Tax brackets and rates"）
# * ``budget`` / ``tax`` / ``court`` / ``judge``（命中 "Budget & Performance" / "Administrative Law Judge"）
# * ``loss`` / ``profit`` / ``prices`` / ``wage`` / ``workers``（报道短语碎片，信噪比低）
# * ``deal`` / ``brexit`` / ``minister`` / ``prime minister`` / ``president``（营销 / 人物栏目常见词）
# * ``supermarket`` / ``retail``（零售促销页）
#
# 保留 ``stock`` / ``stocks`` / ``market`` / ``markets``：这些是市场新闻的核心词，短语形态由新增的
# :data:`_HEADLINE_PAGE_NAV_JUNK_RE` 做负向过滤（如 "Most active penny stocks" / "SEC & Markets Data"）。
CRAWL4AI_TITLE_SEED_TERMS: Tuple[str, ...] = (
    "missile",
    "blockade",
    "ceasefire",
    "sanctions",
    "embargo",
    "hormuz",
    "strait",
    "iran",
    "israel",
    "gaza",
    "ukraine",
    "russia",
    "taiwan",
    "tsmc",
    "semiconductor",
    "chip",
    "lithography",
    "asml",
    "export",
    "nvidia",
    "apple",
    "microsoft",
    "alphabet",
    "google",
    "amazon",
    "meta",
    "oil",
    "crude",
    "opec",
    "energy",
    "refinery",
    "pipeline",
    "fed",
    "ecb",
    "boj",
    "inflation",
    "recession",
    "gdp",
    "bond",
    "treasury",
    "stock",
    "stocks",
    "market",
    "markets",
    "trading",
    "investor",
    "earnings",
    "revenue",
    "bank",
    "gold",
    "dollar",
    "euro",
    "yuan",
    "china",
    "beijing",
    "washington",
    "congress",
    "senate",
    "white house",
    "war",
    "conflict",
    "military",
    "naval",
    "strike",
    "attack",
    "tariff",
    "trade",
    "election",
    "imf",
    "opec+",
    "blackrock",
    "jpmorgan",
    "goldman",
    "morgan stanley",
    "citigroup",
    "barclays",
    "deutsche",
    "ubs",
    "credit suisse",
    "middle east",
    "red sea",
    "supply chain",
    "export ban",
    "geopolitical",
)


def geo_google_news_rss_feeds() -> Tuple[Tuple[str, str], ...]:
    """(url, label) for English Google News RSS, aligned with :data:`GEO_NEWS_QUERY_BUNDLES`."""
    return tuple(
        (
            f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=en-US&gl=US&ceid=US:en",
            f"GoogleNews-Geo-{i}",
        )
        for i, q in enumerate(GEO_NEWS_QUERY_BUNDLES, start=1)
    )


def risk_search_params_dict(extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """供 Crawl4AI `search_params` 或 LLM 语义审计引用的种子配置。"""
    base: Dict[str, Any] = {
        "risk_seeds": list(RISK_SEARCH_SEEDS),
        "geo_news_bundles": list(GEO_NEWS_QUERY_BUNDLES),
        "crawl4ai_title_seed_terms": list(CRAWL4AI_TITLE_SEED_TERMS),
        "audit_focus": (
            "一阶段语义审计需识别上述种子词与标的（如 XLE、NVDA、TSMC）的逻辑关联，"
            "使情绪分 S 足以反映地缘/制裁/半导体供应链类尾部风险。"
        ),
    }
    if extra:
        base.update(extra)
    return base
