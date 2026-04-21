"""Sentiment subsystem (extracted 2026-04-21 from monolithic ``research/sentiment_proxy.py``).

This package holds the decomposition of what was a 3225-line module. To preserve
backward compatibility, **all callers should continue importing from**
``research.sentiment_proxy`` — that module re-exports every public/private name
from the submodules below.

Submodule layout:
    lexicons   — pure data tables (VADER lexicon, ticker keyword map, context pairs, etc.)
    scoring    — per-ticker sentiment analysis + public ``get_sentiment_*`` API
    series     — daily VADER S_t time-series builders (used by Phase-pipeline)

The headline-fetching plumbing (RSS / NewsAPI / AKShare / Crawl4AI / merge /
orchestrator) intentionally stays inside ``sentiment_proxy.py`` for now — it is
highly inter-coupled and was already simplified in the previous slim-down round.
"""
