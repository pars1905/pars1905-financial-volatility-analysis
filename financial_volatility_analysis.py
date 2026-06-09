"""
BIST 30 Volatility & Risk-Adjusted Return Analysis
==================================================

Computes annualized volatility, Sharpe ratio, maximum drawdown and a
5-tier risk score for a basket of Borsa Istanbul (BIST) tickers.

Data source: Yahoo Finance via yfinance. If the network is unavailable
(e.g. inside a sandboxed container), the script falls back to a
deterministic synthetic price series (seed=19051905) so the pipeline,
metrics and figures remain fully reproducible.

Author: Osman Manay  (github.com/pars1905)
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

warnings.filterwarnings("ignore")

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

TICKERS = [
    "GARAN.IS", "AKBNK.IS", "THYAO.IS", "EREGL.IS", "BIMAS.IS",
    "ASELS.IS", "KCHOL.IS", "SAHOL.IS", "SISE.IS",  "TUPRS.IS",
]

TICKER_NAMES = {
    "GARAN.IS": "Garanti BBVA",
    "AKBNK.IS": "Akbank",
    "THYAO.IS": "Turkish Airlines",
    "EREGL.IS": "Eregli Demir-Celik",
    "BIMAS.IS": "BIM Magazalar",
    "ASELS.IS": "Aselsan",
    "KCHOL.IS": "Koc Holding",
    "SAHOL.IS": "Sabanci Holding",
    "SISE.IS":  "Sisecam",
    "TUPRS.IS": "Tupras",
}

SECTORS = {
    "GARAN.IS": "Banking",  "AKBNK.IS": "Banking",
    "THYAO.IS": "Transport", "EREGL.IS": "Steel",
    "BIMAS.IS": "Retail",   "ASELS.IS": "Defense",
    "KCHOL.IS": "Holding",  "SAHOL.IS": "Holding",
    "SISE.IS":  "Glass",    "TUPRS.IS": "Energy",
}

RISK_FREE_RATE = 0.26          # TR 2y reference rate
TRADING_DAYS = 252
LOOKBACK_DAYS = 365 * 2
SEED = 19051905
OUTPUT_DIR = Path(__file__).resolve().parent

BIST_BLUE = "#003087"
BIST_RED = "#e31937"


# -----------------------------------------------------------------------------
# Data loading
# -----------------------------------------------------------------------------

@dataclass
class LoadResult:
    prices: pd.DataFrame
    source: str  # "yfinance" or "synthetic"


def _load_from_yfinance() -> pd.DataFrame | None:
    try:
        import yfinance as yf
    except Exception:
        return None

    end = pd.Timestamp.today().normalize()
    start = end - pd.Timedelta(days=LOOKBACK_DAYS)
    try:
        data = yf.download(
            TICKERS, start=start, end=end,
            progress=False, auto_adjust=True, threads=True,
        )
    except Exception:
        return None

    if data is None or len(data) == 0:
        return None

    if isinstance(data.columns, pd.MultiIndex):
        if "Close" in data.columns.get_level_values(0):
            prices = data["Close"]
        else:
            return None
    else:
        prices = data

    prices = prices.dropna(how="all").ffill().dropna()
    missing = [t for t in TICKERS if t not in prices.columns]
    if missing or len(prices) < 60:
        return None
    return prices[TICKERS]


def _synthetic_prices() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    n = LOOKBACK_DAYS
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)

    profiles = {
        "GARAN.IS": (0.00075, 0.022), "AKBNK.IS": (0.00068, 0.024),
        "THYAO.IS": (0.00120, 0.031), "EREGL.IS": (0.00055, 0.026),
        "BIMAS.IS": (0.00060, 0.018), "ASELS.IS": (0.00095, 0.028),
        "KCHOL.IS": (0.00070, 0.020), "SAHOL.IS": (0.00065, 0.021),
        "SISE.IS":  (0.00050, 0.023), "TUPRS.IS": (0.00110, 0.029),
    }

    market = rng.normal(0.0008, 0.014, n)
    prices = {}
    for t in TICKERS:
        mu, sigma = profiles[t]
        beta = rng.uniform(0.7, 1.3)
        idio = rng.normal(0.0, sigma, n)
        returns = mu + beta * market + idio
        path = 100.0 * np.exp(np.cumsum(returns))
        prices[t] = path
    return pd.DataFrame(prices, index=dates)


def load_prices() -> LoadResult:
    df = _load_from_yfinance()
    if df is not None:
        return LoadResult(df, "yfinance")
    print("[warn] yfinance unavailable — using deterministic synthetic data "
          f"(seed={SEED}).")
    return LoadResult(_synthetic_prices(), "synthetic")


# -----------------------------------------------------------------------------
# Metrics
# -----------------------------------------------------------------------------

def compute_metrics(prices: pd.DataFrame) -> pd.DataFrame:
    returns = prices.pct_change().dropna()

    annual_return = returns.mean() * TRADING_DAYS
    annual_vol = returns.std() * np.sqrt(TRADING_DAYS)
    sharpe = (annual_return - RISK_FREE_RATE) / annual_vol

    cum = (1 + returns).cumprod()
    drawdown = (cum / cum.cummax() - 1).min()

    df = pd.DataFrame({
        "ticker": returns.columns,
        "name": [TICKER_NAMES[t] for t in returns.columns],
        "sector": [SECTORS[t] for t in returns.columns],
        "annual_return": annual_return.values,
        "annual_vol": annual_vol.values,
        "sharpe": sharpe.values,
        "max_drawdown": drawdown.values,
    })

    df["risk_tier"] = pd.qcut(
        df["annual_vol"], q=5, labels=[1, 2, 3, 4, 5]
    ).astype(int)
    return df.sort_values("annual_vol").reset_index(drop=True)


# -----------------------------------------------------------------------------
# Plot helpers
# -----------------------------------------------------------------------------

def _setup_style() -> None:
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 11,
        "axes.titleweight": "bold",
        "axes.edgecolor": "#222",
        "axes.linewidth": 0.8,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "grid.color": "#dddddd",
        "grid.linestyle": "--",
        "grid.linewidth": 0.5,
    })


def _save(fig: plt.Figure, name: str) -> Path:
    path = OUTPUT_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def plot_volatility(df: pd.DataFrame) -> Path:
    d = df.sort_values("annual_vol", ascending=True)
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(d["ticker"], d["annual_vol"] * 100,
                   color=BIST_BLUE, edgecolor="white")
    for bar, val in zip(bars, d["annual_vol"] * 100):
        ax.text(val + 0.3, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", fontsize=9)
    ax.set_xlabel("Annualized Volatility (%)")
    ax.set_title("BIST 10 — Annualized Volatility Comparison")
    ax.grid(axis="x", alpha=0.4)
    ax.invert_yaxis()
    return _save(fig, "volatility_comparison.png")


def plot_sharpe(df: pd.DataFrame) -> Path:
    d = df.sort_values("sharpe", ascending=True)
    colors = [BIST_BLUE if s >= 0 else BIST_RED for s in d["sharpe"]]
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(d["ticker"], d["sharpe"], color=colors, edgecolor="white")
    for bar, val in zip(bars, d["sharpe"]):
        offset = 0.03 if val >= 0 else -0.03
        ha = "left" if val >= 0 else "right"
        ax.text(val + offset, bar.get_y() + bar.get_height() / 2,
                f"{val:.2f}", va="center", ha=ha, fontsize=9)
    ax.axvline(0, color="#222", linewidth=0.8)
    ax.set_xlabel(f"Sharpe Ratio (rf = {RISK_FREE_RATE:.0%})")
    ax.set_title("BIST 10 — Sharpe Ratio (Risk-Adjusted Return)")
    ax.grid(axis="x", alpha=0.4)
    ax.invert_yaxis()
    return _save(fig, "sharpe_ratio.png")


def plot_risk_return(df: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(10, 7))
    sc = ax.scatter(
        df["annual_vol"] * 100, df["annual_return"] * 100,
        c=df["sharpe"], cmap="RdYlBu", s=240,
        edgecolor=BIST_BLUE, linewidth=1.5, alpha=0.9,
    )
    for _, row in df.iterrows():
        ax.annotate(
            row["ticker"].replace(".IS", ""),
            (row["annual_vol"] * 100, row["annual_return"] * 100),
            xytext=(8, 6), textcoords="offset points",
            fontsize=9, fontweight="bold",
        )
    ax.axhline(RISK_FREE_RATE * 100, color=BIST_RED, linestyle="--",
               linewidth=1, label=f"Risk-free ({RISK_FREE_RATE:.0%})")
    ax.set_xlabel("Annualized Volatility (%)")
    ax.set_ylabel("Annualized Return (%)")
    ax.set_title("Risk-Return Profile — BIST 10")
    ax.grid(alpha=0.4)
    ax.legend(loc="upper left")
    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label("Sharpe Ratio")
    return _save(fig, "risk_return.png")


def plot_drawdown(df: pd.DataFrame) -> Path:
    d = df.sort_values("max_drawdown", ascending=False)
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(d["ticker"], d["max_drawdown"] * 100,
                   color=BIST_RED, edgecolor="white")
    for bar, val in zip(bars, d["max_drawdown"] * 100):
        ax.text(val - 0.5, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", ha="right",
                color="white", fontsize=9, fontweight="bold")
    ax.set_xlabel("Maximum Drawdown (%)")
    ax.set_title("BIST 10 — Maximum Drawdown")
    ax.grid(axis="x", alpha=0.4)
    ax.invert_yaxis()
    return _save(fig, "drawdown.png")


def plot_dashboard(df: pd.DataFrame, source: str) -> Path:
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.28)

    # Volatility
    ax1 = fig.add_subplot(gs[0, 0])
    d1 = df.sort_values("annual_vol")
    ax1.barh(d1["ticker"], d1["annual_vol"] * 100,
             color=BIST_BLUE, edgecolor="white")
    ax1.set_title("Annualized Volatility (%)")
    ax1.grid(axis="x", alpha=0.4)
    ax1.invert_yaxis()

    # Sharpe
    ax2 = fig.add_subplot(gs[0, 1])
    d2 = df.sort_values("sharpe")
    colors = [BIST_BLUE if s >= 0 else BIST_RED for s in d2["sharpe"]]
    ax2.barh(d2["ticker"], d2["sharpe"], color=colors, edgecolor="white")
    ax2.axvline(0, color="#222", linewidth=0.8)
    ax2.set_title(f"Sharpe Ratio (rf = {RISK_FREE_RATE:.0%})")
    ax2.grid(axis="x", alpha=0.4)
    ax2.invert_yaxis()

    # Risk-return
    ax3 = fig.add_subplot(gs[1, 0])
    sc = ax3.scatter(df["annual_vol"] * 100, df["annual_return"] * 100,
                     c=df["sharpe"], cmap="RdYlBu", s=180,
                     edgecolor=BIST_BLUE, linewidth=1.2)
    for _, row in df.iterrows():
        ax3.annotate(row["ticker"].replace(".IS", ""),
                     (row["annual_vol"] * 100, row["annual_return"] * 100),
                     xytext=(6, 4), textcoords="offset points", fontsize=8)
    ax3.axhline(RISK_FREE_RATE * 100, color=BIST_RED,
                linestyle="--", linewidth=1)
    ax3.set_xlabel("Volatility (%)")
    ax3.set_ylabel("Return (%)")
    ax3.set_title("Risk-Return Profile")
    ax3.grid(alpha=0.4)
    plt.colorbar(sc, ax=ax3, label="Sharpe")

    # Risk tier heatmap
    ax4 = fig.add_subplot(gs[1, 1])
    tier_table = df.set_index("ticker")[
        ["annual_vol", "sharpe", "max_drawdown", "risk_tier"]
    ].copy()
    tier_table["annual_vol"] *= 100
    tier_table["max_drawdown"] *= 100
    sns.heatmap(
        tier_table, annot=True, fmt=".2f",
        cmap="RdYlBu_r", ax=ax4, cbar=False,
        linewidths=0.5, linecolor="white",
    )
    ax4.set_title("Risk Tiering Matrix")
    ax4.set_ylabel("")

    fig.suptitle(
        f"BIST 10 Volatility Dashboard  ·  data: {source}  ·  rf={RISK_FREE_RATE:.0%}",
        fontsize=15, fontweight="bold", y=0.995,
    )
    return _save(fig, "dashboard.png")


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------

def main() -> None:
    _setup_style()
    load = load_prices()
    metrics = compute_metrics(load.prices)

    print("\n=== BIST 10 Volatility Analysis ===")
    print(f"Data source : {load.source}")
    print(f"Observations: {len(load.prices)} trading days")
    print(f"Risk-free   : {RISK_FREE_RATE:.0%}\n")
    show = metrics.copy()
    show["annual_return"] = (show["annual_return"] * 100).round(2)
    show["annual_vol"] = (show["annual_vol"] * 100).round(2)
    show["max_drawdown"] = (show["max_drawdown"] * 100).round(2)
    show["sharpe"] = show["sharpe"].round(2)
    print(show.to_string(index=False))

    summary_path = OUTPUT_DIR / "summary.csv"
    metrics.to_csv(summary_path, index=False)
    print(f"\n[ok] summary written -> {summary_path.name}")

    for path in [
        plot_volatility(metrics),
        plot_sharpe(metrics),
        plot_risk_return(metrics),
        plot_drawdown(metrics),
        plot_dashboard(metrics, load.source),
    ]:
        print(f"[ok] figure  written -> {path.name}")


if __name__ == "__main__":
    main()
