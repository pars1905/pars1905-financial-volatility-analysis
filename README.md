# pars1905-financial-volatility-analysis

[![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![pandas](https://img.shields.io/badge/pandas-2.x-150458?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![matplotlib](https://img.shields.io/badge/matplotlib-3.x-11557c?logo=python&logoColor=white)](https://matplotlib.org/)
[![yfinance](https://img.shields.io/badge/data-yfinance-orange)](https://github.com/ranaroussi/yfinance)
[![BIST](https://img.shields.io/badge/market-BIST%2030-003087)](https://www.borsaistanbul.com/)
[![license](https://img.shields.io/badge/license-MIT-green)](#license)

**BIST 10 volatility & risk-adjusted return analysis** — annualized volatility,
Sharpe ratio, maximum drawdown and a 5-tier risk score for a basket of
Borsa Istanbul blue chips.

> Author: **Osman Manay** ([github.com/pars1905](https://github.com/pars1905))

---

## What it does

The script `financial_volatility_analysis.py`:

1. Pulls 2 years of daily adjusted close prices from Yahoo Finance for
   10 BIST tickers (`GARAN.IS, AKBNK.IS, THYAO.IS, EREGL.IS, BIMAS.IS,
   ASELS.IS, KCHOL.IS, SAHOL.IS, SISE.IS, TUPRS.IS`).
2. Computes daily log-equivalent returns, annualized volatility,
   Sharpe ratio (`rf = 26%`, TR 2y reference), maximum drawdown.
3. Assigns each ticker a **risk tier 1–5** via quintile bucketing on
   annualized volatility.
4. Renders five 150-dpi PNG figures (BIST blue `#003087`, BIST red
   `#e31937`, serif typeface, white background).
5. Writes a tidy `summary.csv` for downstream notebooks.

## Methodology

| Metric              | Formula                                              |
|---------------------|------------------------------------------------------|
| Daily return        | `r_t = P_t / P_{t-1} − 1`                            |
| Annualized return   | `mean(r) × 252`                                      |
| Annualized vol      | `std(r) × √252`                                      |
| Sharpe ratio        | `(annual_return − rf) / annual_vol`,  `rf = 0.26`    |
| Maximum drawdown    | `min(cum / cummax(cum) − 1)`                         |
| Risk tier (1–5)     | `pd.qcut(annual_vol, q=5)` — 1 = calmest, 5 = wildest |

## Quick start

```bash
git clone https://github.com/pars1905/pars1905-financial-volatility-analysis.git
cd pars1905-financial-volatility-analysis
pip install -r requirements.txt
python financial_volatility_analysis.py
```

Outputs land next to the script:

```
summary.csv
volatility_comparison.png
sharpe_ratio.png
risk_return.png
drawdown.png
dashboard.png
```

## Outputs

| File                          | What it shows                                          |
|-------------------------------|--------------------------------------------------------|
| `volatility_comparison.png`   | Horizontal bar — annualized vol per ticker             |
| `sharpe_ratio.png`            | Sharpe per ticker, positive (blue) / negative (red)    |
| `risk_return.png`             | Vol vs return scatter, Sharpe-coloured                 |
| `drawdown.png`                | Max drawdown per ticker                                |
| `dashboard.png`               | 2×2 composite — vol, Sharpe, risk-return, risk matrix  |

## Caveats

- **Synthetic fallback.** If `yfinance` cannot reach Yahoo (offline runner,
  sandboxed container, rate-limited host), the script falls back to a
  deterministic synthetic price series seeded with `19051905` so that
  metrics and figures are still produced and reproducible. The committed
  PNGs in this repo may have been generated from the synthetic path
  — re-run locally with network access to get live BIST numbers.
- **Risk-free rate is a static reference** (26%, TR 2y) and not a daily
  curve; Sharpe is sensitive to this choice.
- **Quintile risk tiering is relative** to the current basket; adding or
  removing tickers will reshuffle tiers.
- **Past volatility ≠ future volatility.** Nothing here is investment advice.

## License

MIT — see [LICENSE](LICENSE) if present, otherwise treat code as MIT-licensed.
