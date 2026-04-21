"""Pure data tables used by the sentiment subsystem.

Extracted from ``research/sentiment_proxy.py`` (2026-04-21) so that the proxy
module no longer carries ~835 lines of inert data. All public/private names
below are re-exported from ``research.sentiment_proxy`` to preserve the old
import surface.

Contents:
    _IRAN_US_LEXICON         — VADER lexicon updates for the 2025-2026 Iran-US conflict.
    _RISK_KEYWORDS           — geopolitical risk keywords (penalty signal).
    _POSITIVE_KEYWORDS       — diplomacy / de-escalation keywords (positive signal).
    _MONTH_PREFIX            — three-letter English month prefixes for date parsing.
    _TICKER_KEYWORD_MAP      — per-ticker bearish/bullish keyword weights and caps.
    _CONTEXT_DIRECTION_PAIRS — two-word (context, direction) signal pairs.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

# ── Iran-US Conflict Lexicon ──────────────────────────────────────────────────
# Custom VADER lexicon updates for 2025-2026 Iran-US conflict context.
# Negative scores → bearish market signal; positive → bullish.
# Follows VADER scale roughly: strong = ±3.0, moderate = ±2.0, mild = ±1.0.

_IRAN_US_LEXICON: Dict[str, float] = {
    # ── Escalation / military threat (strongly negative) ──
    "irgc":                -2.8,
    "revolutionary guard": -2.5,
    "hypersonic missile":  -3.0,
    "ballistic missile":   -2.8,
    "nuclear warhead":     -3.5,
    "nuclear strike":      -3.5,
    "enrichment":          -2.2,
    "centrifuge":          -1.8,
    "natanz":              -2.0,
    "fordow":              -2.0,
    "uranium":             -1.5,
    "weapons-grade":       -2.5,
    "breakout":            -2.0,
    "khamenei":            -1.8,
    "raisi":               -1.5,
    "tehran threat":       -2.2,
    "strait of hormuz":    -2.5,
    "hormuz blockade":     -3.0,
    "tanker seizure":      -2.5,
    "oil blockade":        -2.8,
    "proxy militia":       -2.0,
    "drone swarm":         -2.3,
    "suicide drone":       -2.5,
    "martyrdom":           -1.5,
    "martyrs":             -1.0,
    "jihad":               -1.8,
    "fatwa":               -1.5,
    "assassination":       -2.5,
    "targeted killing":    -2.3,
    "retaliatory strike":  -2.8,
    "airstrike":           -2.5,
    "air strike":          -2.5,
    "regime change":       -2.0,
    "maximum pressure":    -1.5,
    "snapback sanctions":  -2.0,
    "oil embargo":         -2.5,
    "crude surge":         -1.8,
    "oil spike":           -1.8,
    "energy shock":        -2.0,
    "supply disruption":   -2.2,
    "geopolitical risk":   -1.5,
    "middle east war":     -3.0,
    "regional escalation": -2.5,
    "nuclear crisis":      -3.0,
    "war risk":            -2.5,
    # ── General conflict terms (moderately negative) ──
    "iran":                -1.2,
    "tehran":              -0.8,
    "sanctions":           -1.8,
    "embargo":             -2.0,
    "blockade":            -2.2,
    "missile":             -2.0,
    "nuclear":             -1.5,
    "warship":             -1.5,
    "naval confrontation": -2.0,
    "military action":     -2.0,
    "military strike":     -2.5,
    "war":                 -2.5,
    "conflict":            -1.8,
    "crisis":              -1.5,
    "confrontation":       -1.8,
    "escalation":          -2.2,
    "destabilize":         -1.8,
    "insurgency":          -1.5,
    "attack":              -2.0,
    "retaliation":         -2.0,
    "invasion":            -3.0,
    "occupation":          -2.0,
    "ultimatum":           -2.0,
    "threat":              -1.5,
    "crude oil":           -0.8,
    "supply chain":        -0.5,
    "ban":                 -1.0,
    "missile launch":      -2.8,
    # ── Chinese-language terms ──
    "伊朗":                -1.2,
    "制裁":                -1.8,
    "封锁":                -2.2,
    "战争":                -2.5,
    "冲突":                -1.8,
    "禁令":                -1.0,
    "原油":                -0.8,
    "供应链":              -0.5,
    "导弹":                -2.0,
    "核武器":              -3.0,
    "核危机":              -3.0,
    "霍尔木兹":            -2.5,
    "美伊":                -1.5,
    "军事打击":            -2.5,
    "报复":                -2.0,
    "升级":                -1.8,
    "危机":                -1.5,
    # ── De-escalation / diplomacy (positive) ──
    "ceasefire":           +2.5,
    "cease-fire":          +2.5,
    "truce":               +2.0,
    "diplomacy":           +1.5,
    "diplomatic":          +1.2,
    "negotiations":        +1.5,
    "negotiation":         +1.5,
    "de-escalate":         +2.0,
    "de-escalation":       +2.0,
    "de escalation":       +2.0,
    "back-channel":        +1.0,
    "agreement":           +1.5,
    "deal":                +0.8,
    "nuclear deal":        +1.5,
    "jcpoa":               +1.0,
    "talks":               +1.0,
    "dialogue":            +1.2,
    "restraint":           +1.2,
    "pull back":           +1.5,
    "sanctions relief":    +2.0,
    "sanctions eased":     +2.0,
    "oil supply restored": +2.0,
    "stability":           +1.2,
    "calm":                +1.0,
    "resolution":          +1.5,
    "peace":               +1.5,
    "accord":              +1.5,
    "diplomatic solution": +1.8,
    "停火":                +2.5,
    "外交":                +1.5,
    "谈判":                +1.5,
    "协议":                +1.5,
    "和平":                +1.5,
    "降级":                +2.0,
    "缓和":                +2.0,
    "解除制裁":            +2.0,
}


# ── Risk-keyword penalty (secondary signal) ──────────────────────────────────
_RISK_KEYWORDS = [
    "missile", "blockade", "airstrike", "air strike", "strike",
    "drone", "warship", "invasion", "attack", "nuclear", "explosion",
    "sanctions", "embargo", "ban", "crude oil", "oil spike",
    "supply chain", "disruption", "shortage",
    "war", "conflict", "crisis", "escalation", "tension",
    "irgc", "hormuz", "natanz", "khamenei", "iran",
    "封锁", "制裁", "战争", "冲突", "禁令", "原油", "供应链", "导弹", "核武器",
    "危机", "升级", "美伊", "军事",
]

_POSITIVE_KEYWORDS = [
    "ceasefire", "cease-fire", "truce", "diplomacy", "negotiations",
    "de-escalation", "agreement", "deal", "jcpoa", "sanctions relief",
    "停火", "外交", "谈判", "协议", "和平", "降级", "缓和",
]


_MONTH_PREFIX = (
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec",
)


# ── Per-ticker keyword mapping (all known assets) ────────────────────────────
# Each entry:
#   "bearish": [(phrase_lower, weight), ...]  — hit contributes -weight to ΔS
#   "bullish": [(phrase_lower, weight), ...]  — hit contributes +weight to ΔS
#   "cap":  max |ΔS| for this ticker
# Add any new asset by inserting a new key; no other code change required.
_TICKER_KEYWORD_MAP: Dict[str, Any] = {
    # ── AI / Semiconductor ────────────────────────────────────────────────────
    "NVDA": {
        "bearish": [
            ("nvidia", 0.06), ("nvda", 0.06),
            ("gpu export ban", 0.26), ("ai chip ban", 0.24), ("nvidia ban", 0.24),
            ("nvidia sanction", 0.24), ("export restriction", 0.13),
            ("a100 ban", 0.22), ("h100 ban", 0.22), ("h800", 0.16),
            ("chip restriction", 0.14), ("semiconductor ban", 0.14),
            ("chip sanctions", 0.14), ("semiconductor sanctions", 0.14),
            ("hormuz", 0.10), ("strait of hormuz", 0.12), ("red sea shipping", 0.11),
            ("energy shock", 0.09), ("oil spike fear", 0.09),
            ("ai spending cut", 0.16), ("nvidia miss", 0.18),
            ("data center freeze", 0.14), ("ai bubble", 0.15),
        ],
        "bullish": [
            ("nvidia beat", 0.16), ("nvidia record", 0.13),
            ("ai demand surge", 0.14), ("blackwell", 0.11),
            ("hopper demand", 0.11), ("ai chip demand", 0.11),
            ("data center boom", 0.12),
        ],
        "cap": 0.55,
    },
    "MSFT": {
        "bearish": [
            ("microsoft", 0.05), ("msft", 0.05),
            ("azure outage", 0.18), ("microsoft layoffs", 0.16),
            ("microsoft antitrust", 0.15), ("cloud slowdown", 0.12),
            ("microsoft security breach", 0.18),
            ("energy inflation", 0.08), ("risk-off", 0.09),
        ],
        "bullish": [
            ("azure growth", 0.14), ("microsoft beat", 0.14),
            ("copilot adoption", 0.11), ("microsoft record", 0.11),
        ],
        "cap": 0.45,
    },
    "TSMC": {
        "bearish": [
            ("tsmc", 0.07), ("taiwan semiconductor", 0.07),
            ("taiwan invasion", 0.32), ("china taiwan", 0.22),
            ("taiwan strait", 0.24), ("taiwan blockade", 0.30),
            ("pla exercise taiwan", 0.26), ("taiwan military", 0.22),
            ("chip export control", 0.18), ("tsmc ban", 0.22),
            ("semiconductor shortage", 0.14), ("tsmc cut", 0.14),
            ("taiwan tension", 0.19), ("taiwan crisis", 0.23),
            ("china chip ban", 0.18),
        ],
        "bullish": [
            ("tsmc beat", 0.14), ("tsmc record", 0.13),
            ("arizona fab", 0.11), ("taiwan peace", 0.16),
            ("taiwan stability", 0.13), ("tsmc expansion", 0.12),
        ],
        "cap": 0.60,
    },
    "TSM": {
        "bearish": [
            ("tsmc", 0.07), ("taiwan semiconductor", 0.07),
            ("taiwan invasion", 0.32), ("china taiwan", 0.22),
            ("taiwan blockade", 0.30), ("taiwan tension", 0.19),
            ("taiwan crisis", 0.23), ("chip export control", 0.18),
        ],
        "bullish": [
            ("tsmc beat", 0.14), ("tsmc record", 0.13),
            ("taiwan peace", 0.16),
        ],
        "cap": 0.60,
    },
    "GOOGL": {
        "bearish": [
            ("google", 0.04), ("alphabet", 0.04), ("googl", 0.05),
            ("google antitrust", 0.18), ("google breakup", 0.22),
            ("doj google", 0.17), ("google fine", 0.14),
            ("google layoffs", 0.14), ("google miss", 0.15),
            ("energy inflation", 0.08), ("risk-off", 0.09),
        ],
        "bullish": [
            ("google beat", 0.14), ("alphabet revenue", 0.12),
            ("google ai lead", 0.12), ("google cloud growth", 0.11),
        ],
        "cap": 0.45,
    },
    "AAPL": {
        "bearish": [
            ("apple", 0.04), ("aapl", 0.05), ("iphone", 0.06),
            ("apple china ban", 0.24), ("china apple", 0.15),
            ("iphone ban", 0.22), ("apple sanction", 0.18),
            ("apple supply chain", 0.14), ("foxconn strike", 0.13),
            ("shipping disruption", 0.10), ("logistics disruption", 0.10),
            ("apple antitrust", 0.14), ("app store fine", 0.12),
            ("apple miss", 0.15), ("china sales decline", 0.14),
        ],
        "bullish": [
            ("apple beat", 0.14), ("iphone demand", 0.13),
            ("apple record", 0.12), ("apple ai", 0.11),
        ],
        "cap": 0.50,
    },
    "AMZN": {
        "bearish": [
            ("amazon", 0.04), ("amzn", 0.05), ("aws", 0.05),
            ("amazon antitrust", 0.16), ("aws outage", 0.18),
            ("amazon layoffs", 0.14), ("amazon miss", 0.15),
        ],
        "bullish": [
            ("amazon beat", 0.14), ("aws growth", 0.14),
            ("amazon record", 0.10), ("prime growth", 0.08),
        ],
        "cap": 0.45,
    },
    "ASML": {
        "bearish": [
            ("asml", 0.07), ("euv ban", 0.26), ("asml export ban", 0.26),
            ("dutch export control", 0.24), ("netherlands chip", 0.18),
            ("china asml ban", 0.26), ("euv restricted", 0.24),
            ("semiconductor equipment ban", 0.18), ("lithography ban", 0.22),
        ],
        "bullish": [
            ("asml beat", 0.14), ("asml record", 0.12),
            ("euv demand", 0.12), ("asml backlog", 0.11),
        ],
        "cap": 0.55,
    },
    "META": {
        "bearish": [
            ("meta", 0.04), ("facebook", 0.04), ("instagram", 0.04),
            ("meta antitrust", 0.16), ("meta fine", 0.14),
            ("facebook ban", 0.14), ("meta layoffs", 0.14),
            ("meta miss", 0.15), ("ad revenue decline", 0.12),
        ],
        "bullish": [
            ("meta beat", 0.14), ("meta ai", 0.11),
            ("reels growth", 0.08), ("meta record", 0.10),
        ],
        "cap": 0.45,
    },
    "AVGO": {
        "bearish": [
            ("broadcom", 0.06), ("avgo", 0.06),
            ("broadcom ban", 0.18), ("chip ban broadcom", 0.18),
            ("broadcom miss", 0.14), ("semiconductor restriction", 0.12),
        ],
        "bullish": [
            ("broadcom beat", 0.14), ("broadcom ai", 0.11),
            ("broadcom record", 0.10),
        ],
        "cap": 0.45,
    },
    "ORCL": {
        "bearish": [
            ("oracle", 0.04), ("orcl", 0.05),
            ("oracle miss", 0.14), ("oracle layoffs", 0.12),
        ],
        "bullish": [
            ("oracle beat", 0.14), ("oracle cloud", 0.09),
            ("oracle record", 0.10), ("oracle ai", 0.09),
        ],
        "cap": 0.40,
    },
    "AMD": {
        "bearish": [
            ("amd", 0.05), ("amd ban", 0.20), ("amd miss", 0.14),
            ("gpu export", 0.16), ("amd china ban", 0.20),
            ("mi300 ban", 0.20),
            ("chip sanctions", 0.12), ("hormuz", 0.08), ("red sea shipping", 0.09),
        ],
        "bullish": [
            ("amd beat", 0.14), ("amd record", 0.10),
            ("amd ai", 0.11), ("amd market share", 0.10),
        ],
        "cap": 0.50,
    },
    "INTC": {
        "bearish": [
            ("intel", 0.05), ("intel miss", 0.16),
            ("intel layoffs", 0.14), ("intel foundry fail", 0.16),
            ("intel lose share", 0.14),
        ],
        "bullish": [
            ("intel beat", 0.12), ("intel record", 0.10),
            ("intel recovery", 0.10), ("intel foundry win", 0.12),
        ],
        "cap": 0.45,
    },
    "QCOM": {
        "bearish": [
            ("qualcomm", 0.05), ("qcom", 0.05),
            ("qualcomm ban", 0.18), ("qualcomm china", 0.14),
            ("qualcomm miss", 0.14),
        ],
        "bullish": [
            ("qualcomm beat", 0.12), ("qualcomm record", 0.10),
        ],
        "cap": 0.45,
    },
    "ARM": {
        "bearish": [
            ("arm holdings", 0.06), ("arm ban", 0.16),
            ("arm miss", 0.14), ("arm licensing dispute", 0.14),
        ],
        "bullish": [
            ("arm beat", 0.12), ("arm record", 0.10),
            ("arm ai chip", 0.10),
        ],
        "cap": 0.45,
    },
    # ── Energy ────────────────────────────────────────────────────────────────
    "XLE": {
        "bearish": [
            ("oil price drop", 0.18), ("crude selloff", 0.18),
            ("oil demand cut", 0.16), ("opec+ output increase", 0.14),
            ("energy sector down", 0.14), ("oil glut", 0.16),
            ("brent crash", 0.18), ("wti fall", 0.16),
            ("recession demand oil", 0.12), ("oil inventory surge", 0.12),
        ],
        "bullish": [
            ("oil price surge", 0.22), ("crude spike", 0.22),
            ("opec cut", 0.20), ("hormuz blockade", 0.24),
            ("iran oil sanction", 0.22), ("oil supply shock", 0.22),
            ("energy crisis", 0.18), ("oil embargo", 0.22),
            ("wti spike", 0.20), ("brent surge", 0.20),
            ("pipeline attack", 0.20), ("supply disruption", 0.16),
            ("oil tanker seized", 0.20), ("strait closed", 0.22),
        ],
        "cap": 0.62,
    },
    "USO": {
        "bearish": [
            ("oil price drop", 0.20), ("crude selloff", 0.20),
            ("oil glut", 0.18), ("wti fall", 0.20),
            ("oil demand cut", 0.16),
        ],
        "bullish": [
            ("oil price surge", 0.24), ("crude spike", 0.24),
            ("opec cut", 0.22), ("hormuz blockade", 0.26),
            ("oil supply shock", 0.24), ("wti spike", 0.22),
            ("iran sanction oil", 0.24),
        ],
        "cap": 0.62,
    },
    "CVX": {
        "bearish": [
            ("chevron", 0.05), ("cvx", 0.05),
            ("oil price drop", 0.14), ("chevron miss", 0.14),
        ],
        "bullish": [
            ("chevron beat", 0.12), ("oil surge", 0.14),
            ("chevron record", 0.10),
        ],
        "cap": 0.45,
    },
    "XOM": {
        "bearish": [
            ("exxon", 0.05), ("xom", 0.05),
            ("oil price drop", 0.14), ("exxon miss", 0.14),
        ],
        "bullish": [
            ("exxon beat", 0.12), ("oil surge", 0.14),
            ("exxon record", 0.10),
        ],
        "cap": 0.45,
    },
    "MPC": {
        "bearish": [
            ("marathon petroleum", 0.05), ("mpc", 0.04),
            ("refinery margin down", 0.14), ("mpc miss", 0.14),
        ],
        "bullish": [
            ("mpc beat", 0.12), ("refinery margin up", 0.12),
            ("oil surge", 0.12),
        ],
        "cap": 0.40,
    },
    # ── Safe Haven ────────────────────────────────────────────────────────────
    "GLD": {
        "bearish": [
            ("gold selloff", 0.16), ("gold price drop", 0.14),
            ("gold crash", 0.18), ("dollar surge", 0.10),
            ("gold demand fall", 0.12),
        ],
        "bullish": [
            ("gold surge", 0.20), ("gold record", 0.18), ("gold rally", 0.18),
            ("safe haven", 0.14), ("gold demand", 0.11),
            ("geopolitical risk", 0.13), ("crisis gold", 0.16),
            ("war gold", 0.18), ("inflation gold", 0.11),
            ("flight to gold", 0.18),
        ],
        "cap": 0.52,
    },
    "AU0": {
        "bearish": [
            ("gold selloff", 0.16), ("gold price drop", 0.14),
            ("gold crash", 0.18), ("dollar surge", 0.10),
            ("黄金下跌", 0.16), ("黄金暴跌", 0.18),
        ],
        "bullish": [
            ("gold surge", 0.20), ("gold record", 0.18), ("gold rally", 0.18),
            ("safe haven", 0.14), ("geopolitical risk", 0.13),
            ("war gold", 0.18), ("黄金上涨", 0.18), ("黄金暴涨", 0.20),
            ("避险", 0.14), ("黄金需求", 0.12),
        ],
        "cap": 0.52,
    },
    "IAU": {
        "bearish": [
            ("gold selloff", 0.16), ("gold crash", 0.18), ("dollar surge", 0.10),
        ],
        "bullish": [
            ("gold surge", 0.20), ("gold record", 0.18), ("safe haven", 0.14),
            ("geopolitical risk", 0.13), ("war gold", 0.18),
        ],
        "cap": 0.50,
    },
    "TLT": {
        "bearish": [
            ("treasury selloff", 0.16), ("bond yield spike", 0.16),
            ("rate hike", 0.13), ("fed rate hike", 0.15),
            ("debt ceiling", 0.14), ("tlt drop", 0.14),
            ("inflation surprise", 0.15), ("yield surge", 0.14),
            ("us downgrade", 0.22), ("fiscal crisis", 0.18),
        ],
        "bullish": [
            ("treasury rally", 0.16), ("bond rally", 0.14),
            ("fed cut", 0.17), ("rate cut", 0.15),
            ("flight to safety", 0.18), ("safe haven bonds", 0.16),
            ("yield drop", 0.14), ("recession fear", 0.12),
            ("dovish fed", 0.14),
        ],
        "cap": 0.52,
    },
    "IEF": {
        "bearish": [
            ("treasury selloff", 0.14), ("rate hike", 0.12),
            ("inflation surprise", 0.13), ("yield spike", 0.13),
        ],
        "bullish": [
            ("rate cut", 0.14), ("bond rally", 0.12),
            ("flight to safety", 0.14), ("yield drop", 0.12),
        ],
        "cap": 0.40,
    },
    "SHY": {
        "bearish": [("rate hike aggressive", 0.12), ("fed hawkish", 0.10)],
        "bullish": [("rate cut", 0.12), ("fed dovish", 0.11)],
        "cap": 0.30,
    },
    "BIL": {
        "bearish": [("rate cut", 0.10)],
        "bullish": [("rate hike", 0.08), ("fed hawkish", 0.08)],
        "cap": 0.20,
    },
    # ── Broad Market ──────────────────────────────────────────────────────────
    "SPY": {
        "bearish": [
            ("market crash", 0.24), ("s&p selloff", 0.22),
            ("recession", 0.17), ("market collapse", 0.24),
            ("stocks plunge", 0.22), ("wall street panic", 0.24),
            ("black monday", 0.30), ("circuit breaker", 0.26),
            ("systemic risk", 0.22), ("financial crisis", 0.24),
            ("trade war escalate", 0.20), ("tariff shock", 0.17),
            ("global recession", 0.22),
        ],
        "bullish": [
            ("market rally", 0.16), ("s&p record", 0.14),
            ("stocks surge", 0.15), ("bull market", 0.13),
            ("soft landing", 0.15), ("fed pivot", 0.15),
            ("all-time high", 0.14),
        ],
        "cap": 0.58,
    },
    "QQQ": {
        "bearish": [
            ("tech selloff", 0.20), ("nasdaq plunge", 0.22),
            ("tech crash", 0.24), ("qqq drop", 0.16),
            ("big tech down", 0.18), ("chip ban", 0.17),
            ("geopolitical selloff", 0.11), ("risk-off", 0.10),
            ("middle east conflict", 0.09), ("energy inflation", 0.09),
        ],
        "bullish": [
            ("tech rally", 0.16), ("nasdaq record", 0.15),
            ("big tech surge", 0.15),
        ],
        "cap": 0.52,
    },
    "IWM": {
        "bearish": [
            ("small cap selloff", 0.16), ("recession small", 0.14),
            ("iwm drop", 0.14), ("small cap crash", 0.18),
        ],
        "bullish": [
            ("small cap rally", 0.14), ("rate cut small", 0.14),
            ("iwm record", 0.12),
        ],
        "cap": 0.45,
    },
}


# ── Context × direction pairs for two-word signal detection ──────────────────
# (context_word, direction_word, ticker, side, weight)
# Fires when BOTH words appear anywhere in the combined headline text.
# Captures "oil … soar", "energy … surge", "iran … war", etc.
_CONTEXT_DIRECTION_PAIRS: Tuple[Tuple[str, str, str, str, float], ...] = (
    # ── XLE / Energy ─────────────────────────────────────────────────────────
    ("oil",    "soar",       "XLE", "bull", 0.20),
    ("oil",    "surge",      "XLE", "bull", 0.20),
    ("oil",    "spike",      "XLE", "bull", 0.20),
    ("oil",    "rally",      "XLE", "bull", 0.18),
    ("oil",    "gain",       "XLE", "bull", 0.16),
    ("oil",    "record",     "XLE", "bull", 0.16),
    ("oil",    "high",       "XLE", "bull", 0.14),
    ("energy", "soar",       "XLE", "bull", 0.20),
    ("energy", "surge",      "XLE", "bull", 0.20),
    ("energy", "spike",      "XLE", "bull", 0.18),
    ("energy", "record",     "XLE", "bull", 0.16),
    ("crude",  "surge",      "XLE", "bull", 0.20),
    ("crude",  "soar",       "XLE", "bull", 0.20),
    ("crude",  "spike",      "XLE", "bull", 0.18),
    ("brent",  "surge",      "XLE", "bull", 0.20),
    ("wti",    "surge",      "XLE", "bull", 0.20),
    ("iran",   "war",        "XLE", "bull", 0.22),
    ("iran",   "supply",     "XLE", "bull", 0.20),
    ("oil",    "drop",       "XLE", "bear", 0.18),
    ("oil",    "fall",       "XLE", "bear", 0.18),
    ("oil",    "crash",      "XLE", "bear", 0.20),
    ("oil",    "plunge",     "XLE", "bear", 0.20),
    ("energy", "drop",       "XLE", "bear", 0.18),
    ("energy", "fall",       "XLE", "bear", 0.16),
    ("crude",  "drop",       "XLE", "bear", 0.18),
    ("crude",  "fall",       "XLE", "bear", 0.18),
    # USO (oil ETF)
    ("oil",    "soar",       "USO", "bull", 0.22),
    ("oil",    "surge",      "USO", "bull", 0.22),
    ("oil",    "drop",       "USO", "bear", 0.20),
    ("oil",    "crash",      "USO", "bear", 0.22),
    # CVX / XOM
    ("oil",    "surge",      "CVX", "bull", 0.14),
    ("oil",    "soar",       "CVX", "bull", 0.14),
    ("oil",    "drop",       "CVX", "bear", 0.14),
    ("oil",    "surge",      "XOM", "bull", 0.14),
    ("oil",    "soar",       "XOM", "bull", 0.14),
    ("oil",    "drop",       "XOM", "bear", 0.14),
    # ── Gold (GLD / AU0 / IAU) ────────────────────────────────────────────────
    ("gold",   "soar",       "GLD", "bull", 0.22),
    ("gold",   "surge",      "GLD", "bull", 0.22),
    ("gold",   "record",     "GLD", "bull", 0.20),
    ("gold",   "high",       "GLD", "bull", 0.18),
    ("gold",   "rally",      "GLD", "bull", 0.18),
    ("iran",   "war",        "GLD", "bull", 0.16),
    ("war",    "volatility", "GLD", "bull", 0.14),
    ("gold",   "drop",       "GLD", "bear", 0.18),
    ("gold",   "fall",       "GLD", "bear", 0.16),
    ("gold",   "crash",      "GLD", "bear", 0.20),
    ("gold",   "soar",       "AU0", "bull", 0.22),
    ("gold",   "surge",      "AU0", "bull", 0.22),
    ("gold",   "record",     "AU0", "bull", 0.20),
    ("gold",   "drop",       "AU0", "bear", 0.18),
    ("gold",   "soar",       "IAU", "bull", 0.22),
    ("gold",   "surge",      "IAU", "bull", 0.22),
    ("gold",   "drop",       "IAU", "bear", 0.18),
    # ── Treasury / Rates (TLT / IEF) ─────────────────────────────────────────
    ("yield",  "surge",      "TLT", "bear", 0.18),
    ("yield",  "spike",      "TLT", "bear", 0.18),
    ("yield",  "soar",       "TLT", "bear", 0.18),
    ("yield",  "drop",       "TLT", "bull", 0.16),
    ("yield",  "fall",       "TLT", "bull", 0.16),
    ("bond",   "selloff",    "TLT", "bear", 0.18),
    ("bond",   "rally",      "TLT", "bull", 0.16),
    ("iran",   "war",        "TLT", "bull", 0.12),
    ("rate",   "hike",       "TLT", "bear", 0.14),
    ("rate",   "cut",        "TLT", "bull", 0.14),
    ("yield",  "surge",      "IEF", "bear", 0.14),
    ("yield",  "drop",       "IEF", "bull", 0.12),
    ("rate",   "cut",        "IEF", "bull", 0.12),
    # ── Semiconductors (direct bans / restrictions) ───────────────────────────
    ("chip",   "ban",        "NVDA", "bear", 0.26),
    ("chip",   "ban",        "TSMC", "bear", 0.22),
    ("chip",   "ban",        "AMD",  "bear", 0.22),
    ("chip",   "ban",        "ASML", "bear", 0.22),
    ("chip",   "ban",        "AVGO", "bear", 0.16),
    ("nvidia", "ban",        "NVDA", "bear", 0.28),
    ("nvidia", "record",     "NVDA", "bull", 0.18),
    ("nvidia", "beat",       "NVDA", "bull", 0.18),
    ("taiwan", "invasion",   "TSMC", "bear", 0.35),
    ("taiwan", "military",   "TSMC", "bear", 0.24),
    ("taiwan", "blockade",   "TSMC", "bear", 0.32),
    ("taiwan", "tension",    "TSMC", "bear", 0.20),
    # ── Geopolitical conflict → Tech/Growth valuation compression ─────────────
    # Transmission A: war → oil spike → inflation → rate-hike fear → growth selloff
    ("iran",   "war",        "NVDA",  "bear", 0.12),
    ("iran",   "war",        "MSFT",  "bear", 0.09),
    ("iran",   "war",        "GOOGL", "bear", 0.09),
    ("iran",   "war",        "AAPL",  "bear", 0.09),
    ("iran",   "war",        "QQQ",   "bear", 0.13),
    ("iran",   "war",        "TSMC",  "bear", 0.08),
    # Transmission B: war → global growth slowdown → enterprise IT spend cuts
    ("war",    "growth",     "NVDA",  "bear", 0.14),
    ("war",    "growth",     "MSFT",  "bear", 0.10),
    ("war",    "growth",     "GOOGL", "bear", 0.10),
    ("war",    "growth",     "QQQ",   "bear", 0.14),
    ("war",    "slow",       "NVDA",  "bear", 0.12),
    ("war",    "slow",       "MSFT",  "bear", 0.09),
    ("war",    "slow",       "QQQ",   "bear", 0.12),
    # Transmission C: "global growth to weakest/slowest since pandemic"
    ("global", "growth",     "NVDA",  "bear", 0.11),
    ("global", "growth",     "MSFT",  "bear", 0.08),
    ("global", "growth",     "GOOGL", "bear", 0.08),
    ("global", "growth",     "QQQ",   "bear", 0.11),
    ("growth", "slowest",    "NVDA",  "bear", 0.14),
    ("growth", "slowest",    "MSFT",  "bear", 0.10),
    ("growth", "slowest",    "QQQ",   "bear", 0.14),
    ("growth", "slowest",    "SPY",   "bear", 0.12),
    ("growth", "weakest",    "NVDA",  "bear", 0.14),
    ("growth", "weakest",    "MSFT",  "bear", 0.10),
    ("growth", "weakest",    "QQQ",   "bear", 0.14),
    ("growth", "weakest",    "SPY",   "bear", 0.12),
    ("growth", "slow",       "NVDA",  "bear", 0.10),
    ("growth", "slow",       "MSFT",  "bear", 0.08),
    ("growth", "slow",       "QQQ",   "bear", 0.10),
    ("growth", "pandemic",   "NVDA",  "bear", 0.12),
    ("growth", "pandemic",   "QQQ",   "bear", 0.12),
    ("growth", "pandemic",   "SPY",   "bear", 0.10),
    # Transmission D: IMF / major-institution growth warning
    ("imf",    "growth",     "NVDA",  "bear", 0.10),
    ("imf",    "growth",     "QQQ",   "bear", 0.10),
    ("imf",    "growth",     "SPY",   "bear", 0.09),
    ("imf",    "warns",      "NVDA",  "bear", 0.09),
    ("imf",    "warns",      "QQQ",   "bear", 0.09),
    ("imf",    "warns",      "SPY",   "bear", 0.08),
    # Transmission E: war volatility → broad risk-off → tech sector
    ("war",    "volatility", "NVDA",  "bear", 0.12),
    ("war",    "volatility", "QQQ",   "bear", 0.14),
    ("war",    "volatility", "MSFT",  "bear", 0.09),
    # Transmission F2: Hormuz / oil shock → growth & semis (implicit, headline often omits tickers)
    ("hormuz", "blockade",   "NVDA",  "bear", 0.14),
    ("hormuz", "blockade",   "QQQ",   "bear", 0.13),
    ("hormuz", "blockade",   "AMD",   "bear", 0.12),
    ("hormuz", "attack",     "NVDA",  "bear", 0.12),
    ("hormuz", "attack",     "QQQ",   "bear", 0.11),
    ("strait", "hormuz",     "NVDA",  "bear", 0.11),
    ("strait", "hormuz",     "QQQ",   "bear", 0.10),
    ("oil",    "spike",      "NVDA",  "bear", 0.10),
    ("oil",    "spike",      "QQQ",   "bear", 0.11),
    ("crude",  "spike",      "QQQ",   "bear", 0.10),
    ("oil",    "inflation",  "NVDA",  "bear", 0.11),
    ("oil",    "inflation",  "QQQ",   "bear", 0.12),
    ("oil",    "inflation",  "MSFT",  "bear", 0.08),
    ("energy", "inflation",  "QQQ",   "bear", 0.10),
    ("sanctions", "chip",    "NVDA",  "bear", 0.14),
    ("sanctions", "semiconductor", "NVDA", "bear", 0.14),
    ("sanctions", "technology", "NVDA", "bear", 0.11),
    ("export", "controls",   "NVDA",  "bear", 0.11),
    ("export", "controls",   "AMD",   "bear", 0.10),
    ("shipping", "disruption", "AAPL", "bear", 0.10),
    ("shipping", "disruption", "NVDA", "bear", 0.10),
    ("ukraine", "war",       "NVDA",  "bear", 0.10),
    ("ukraine", "war",       "QQQ",   "bear", 0.10),
    # Transmission F: general recession / slowdown language → tech
    ("recession", "growth",  "NVDA",  "bear", 0.14),
    ("recession", "growth",  "MSFT",  "bear", 0.10),
    ("recession", "growth",  "QQQ",   "bear", 0.14),
    ("slowdown",  "growth",  "NVDA",  "bear", 0.12),
    ("slowdown",  "growth",  "QQQ",   "bear", 0.12),
    # ── Broad Market ──────────────────────────────────────────────────────────
    ("market", "crash",      "SPY", "bear", 0.26),
    ("market", "plunge",     "SPY", "bear", 0.24),
    ("market", "rally",      "SPY", "bull", 0.16),
    ("market", "record",     "SPY", "bull", 0.16),
    ("iran",   "war",        "SPY", "bear", 0.16),
    ("war",    "volatility", "SPY", "bear", 0.16),
    ("tariff", "war",        "SPY", "bear", 0.20),
    ("trade",  "war",        "SPY", "bear", 0.20),
    ("recession", "fear",    "SPY", "bear", 0.18),
    ("market", "crash",      "QQQ", "bear", 0.24),
    ("tech",   "selloff",    "QQQ", "bear", 0.22),
    ("nasdaq", "plunge",     "QQQ", "bear", 0.24),
    ("nasdaq", "record",     "QQQ", "bull", 0.14),
    # ── AAPL ──────────────────────────────────────────────────────────────────
    ("apple",  "ban",        "AAPL", "bear", 0.24),
    ("iphone", "ban",        "AAPL", "bear", 0.24),
    ("china",  "apple",      "AAPL", "bear", 0.18),
    ("apple",  "record",     "AAPL", "bull", 0.16),
    ("apple",  "beat",       "AAPL", "bull", 0.16),
)


__all__ = [
    "_IRAN_US_LEXICON",
    "_RISK_KEYWORDS",
    "_POSITIVE_KEYWORDS",
    "_MONTH_PREFIX",
    "_TICKER_KEYWORD_MAP",
    "_CONTEXT_DIRECTION_PAIRS",
]
