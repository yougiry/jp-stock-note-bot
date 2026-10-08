import json
import math
from pathlib import Path
from statistics import mean

from feature_engine import (
    MIN_HISTORY,
    build_stock_history,
    calculate_stock,
)
RAW_DIR = Path("data/market/jquants")
LABEL_DIR = Path("data/labels")
OUTPUT_DIR = Path("data/backtest")

MIN_HISTORY = 20
TOP_N = 30


def log(*args):
    print(*args, flush=True)


def num(v):
    try:
        if v is None:
            return None
        v = float(v)
        if math.isnan(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def normalize_code(v):
    code = str(v).strip().upper()

    if code.endswith(".0"):
        code = code[:-2]

    if len(code) == 5:
        code = code[:4]

    return code


def pct(a, b):
    if a is None or b is None or b == 0:
        return None

    return ((a / b) - 1.0) * 100.0


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# --------------------------------------
# SAME v1 RULES AS CURRENT RANKER
# Do not optimize during this test.
# --------------------------------------

def price_score(f):
    score = 0.0

    r1 = f.get("return_1d")
    r5 = f.get("return_5d")
    r20 = f.get("return_20d")
    h20 = f.get("distance_from_20d_high")

    if r1 is not None:
        if 1 <= r1 <= 5:
            score += 5
        elif 0 < r1 < 1:
            score += 2
        elif 5 < r1 <= 10:
            score += 3
        elif r1 < -3:
            score -= 3

    if r5 is not None:
        if 2 <= r5 <= 12:
            score += 7
        elif 0 < r5 < 2:
            score += 3
        elif 12 < r5 <= 20:
            score += 4
        elif r5 > 20:
            score -= 2

    if r20 is not None:
        if 3 <= r20 <= 20:
            score += 6
        elif 0 < r20 < 3:
            score += 2
        elif 20 < r20 <= 35:
            score += 3
        elif r20 > 35:
            score -= 2

    if h20 is not None:
        if -3 <= h20 <= 0:
            score += 7
        elif -7 <= h20 < -3:
            score += 4
        elif h20 < -15:
            score -= 2

    return clamp(score, 0, 25)


def flow_score(f):
    score = 0.0

    vr5 = f.get("volume_ratio_5d")
    vr20 = f.get("volume_ratio_20d")
    tvr5 = f.get("trading_value_ratio_5d")
    tvr20 = f.get("trading_value_ratio_20d")

    if vr5 is not None:
        if 1.5 <= vr5 < 3:
            score += 7
        elif 3 <= vr5 < 6:
            score += 9
        elif vr5 >= 6:
            score += 6
        elif vr5 < 0.5:
            score -= 2

    if vr20 is not None:
        if 1.3 <= vr20 < 3:
            score += 5
        elif vr20 >= 3:
            score += 6

    if tvr5 is not None:
        if 1.5 <= tvr5 < 3:
            score += 5
        elif 3 <= tvr5 < 6:
            score += 7
        elif tvr5 >= 6:
            score += 5

    if tvr20 is not None and tvr20 >= 1.3:
        score += 3

    return clamp(score, 0, 25)


def liquidity_score(f):
    value = f.get("trading_value")

    if value is None:
        return 0

    if value >= 1_000_000_000:
        return 20
    if value >= 500_000_000:
        return 17
    if value >= 100_000_000:
        return 13
    if value >= 30_000_000:
        return 8
    if value >= 10_000_000:
        return 4

    return 0


def risk_score(f):
    score = 20.0

    vol20 = f.get("volatility_20d")
    gap = f.get("gap")
    r1 = f.get("return_1d")

    if vol20 is not None:
        if vol20 > 8:
            score -= 10
        elif vol20 > 5:
            score -= 6
        elif vol20 > 3:
            score -= 3

    if gap is not None:
        if abs(gap) > 15:
            score -= 8
        elif abs(gap) > 10:
            score -= 5
        elif abs(gap) > 5:
            score -= 2

    if r1 is not None:
        if r1 > 15:
            score -= 5
        elif r1 < -10:
            score -= 5

    return clamp(score, 0, 20)
def load_history():

    payloads_by_date = {}

    files = sorted(
        RAW_DIR.glob("????-??-??.json")
    )

    for path in files:

        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        payloads_by_date[path.stem] = payload

    return payloads_by_date
def build_features(rows):
    current = rows[-1]

    closes = [x["close"] for x in rows]
    volumes = [x["volume"] for x in rows]
    values = [x["value"] for x in rows]

    if current["close"] is None:
        return None

    f = {}

    if len(rows) >= 2:
        f["return_1d"] = pct(
            closes[-1],
            closes[-2]
        )
    else:
        f["return_1d"] = None

    if len(rows) >= 6:
        f["return_5d"] = pct(
            closes[-1],
            closes[-6]
        )
    else:
        f["return_5d"] = None

    if len(rows) >= 21:
        f["return_20d"] = pct(
            closes[-1],
            closes[-21]
        )
    else:
        f["return_20d"] = None

    if len(rows) >= 20:
        baseline = volumes[-20:-1]

        if (
            current["volume"] is not None
            and baseline
            and all(x is not None for x in baseline)
            and mean(baseline) > 0
        ):
            f["volume_ratio_20d"] = (
                current["volume"] / mean(baseline)
            )
        else:
            f["volume_ratio_20d"] = None

        baseline_value = values[-20:-1]

        if (
            current["value"] is not None
            and baseline_value
            and all(x is not None for x in baseline_value)
            and mean(baseline_value) > 0
        ):
            f["trading_value_ratio_20d"] = (
                current["value"] /
                mean(baseline_value)
            )
        else:
            f["trading_value_ratio_20d"] = None
    else:
        f["volume_ratio_20d"] = None
        f["trading_value_ratio_20d"] = None

    if len(rows) >= 6:
        baseline = volumes[-6:-1]

        if (
            current["volume"] is not None
            and all(x is not None for x in baseline)
            and mean(baseline) > 0
        ):
            f["volume_ratio_5d"] = (
                current["volume"] / mean(baseline)
            )
        else:
            f["volume_ratio_5d"] = None

        baseline_value = values[-6:-1]

        if (
            current["value"] is not None
            and all(x is not None for x in baseline_value)
            and mean(baseline_value) > 0
        ):
            f["trading_value_ratio_5d"] = (
                current["value"] /
                mean(baseline_value)
            )
        else:
            f["trading_value_ratio_5d"] = None
    else:
        f["volume_ratio_5d"] = None
        f["trading_value_ratio_5d"] = None

    if len(rows) >= 20:
        recent = [
            x["close"]
            for x in rows[-20:]
            if x["close"] is not None
        ]

        if len(recent) == 20:
            high20 = max(recent)
            f["distance_from_20d_high"] = pct(
                current["close"],
                high20
            )
        else:
            f["distance_from_20d_high"] = None

        returns = []

        for i in range(1, len(recent)):
            r = pct(recent[i], recent[i - 1])

            if r is not None:
                returns.append(r)

        if len(returns) == 19:
            avg = mean(returns)

            variance = mean(
                [(x - avg) ** 2 for x in returns]
            )

            f["volatility_20d"] = math.sqrt(variance)
        else:
            f["volatility_20d"] = None
    else:
        f["distance_from_20d_high"] = None
        f["volatility_20d"] = None

    if (
        current["open"] is not None
        and len(rows) >= 2
        and closes[-2] not in (None, 0)
    ):
        f["gap"] = pct(
            current["open"],
            closes[-2]
        )
    else:
        f["gap"] = None

    f["trading_value"] = current["value"]
    f["market_cap"] = current["market_cap"]

    return f


def size_score(f):
    cap = f.get("market_cap")

    if cap is None:
        return 0

    # Preserves current v1 rule exactly.
    if 10_000 <= cap < 100_000:
        return 10
    if 100_000 <= cap < 300_000:
        return 8
    if 300_000 <= cap < 1_000_000:
        return 5
    if cap >= 1_000_000:
        return 2

    return 3


def score(f):
    p = price_score(f)
    fl = flow_score(f)
    liq = liquidity_score(f)
    risk = risk_score(f)
    size = size_score(f)

    return {
        "price": p,
        "flow": fl,
        "liquidity": liq,
        "risk": risk,
        "size": size,
        "total": p + fl + liq + risk + size,
    }


def load_label(feature_date):
    path = LABEL_DIR / f"next_day_{feature_date}.json"

    if not path.exists():
        return {}

    payload = json.loads(path.read_text(encoding="utf-8"))

    return {
        normalize_code(x["code"]): x
        for x in payload.get("labels", [])
    }


def avg(items, key):
    vals = [
        num(x.get(key))
        for x in items
        if num(x.get(key)) is not None
    ]

    return mean(vals) if vals else None


def rate(items, key):
    vals = [
        x.get(key)
        for x in items
        if x.get(key) is not None
    ]

    if not vals:
        return None

    return (
        sum(1 for x in vals if x is True)
        / len(vals)
        * 100
    )


def main():
    log("")
    log("==============================")
    log("v5.11 MARKET SCORE BACKTEST")
    log("==============================")

    history = load_history()
    dates = sorted(history)

    log("Trading days:", len(dates))

    results = []

    # Need current day plus 20-day history,
    # and a following label day.
    for date_index in range(20, len(dates) - 1):
        feature_date = dates[date_index]
        labels = load_label(feature_date)

        if not labels:
            continue

        universe_codes = set()

        for d in dates[:date_index + 1]:
            universe_codes.update(history[d].keys())

        daily = []

        for code in universe_codes:
            rows = []

            for d in dates[:date_index + 1]:
                row = history[d].get(code)

                if row is not None:
                    rows.append(row)

            if len(rows) < MIN_HISTORY:
                continue

            f = build_features(rows)

            if f is None:
                continue

            s = score(f)

            label = labels.get(code)

            if not label or not label.get("valid_open"):
                continue

            daily.append({
                "code": code,
                "feature_date": feature_date,
                "score": s["total"],
                "price_score": s["price"],
                "flow_score": s["flow"],
                "liquidity_score": s["liquidity"],
                "risk_score": s["risk"],
                "size_score": s["size"],
                "mfe_pct": label.get("mfe_pct"),
                "mae_pct": label.get("mae_pct"),
                "open_to_close_pct":
                    label.get("open_to_close_pct"),
                "hit_plus_3":
                    label.get("hit_plus_3"),
                "hit_plus_5":
                    label.get("hit_plus_5"),
                "hit_plus_10":
                    label.get("hit_plus_10"),
                "hit_minus_3":
                    label.get("hit_minus_3"),
                "hit_minus_5":
                    label.get("hit_minus_5"),
                "benchmark_return_pct":
                    label.get("benchmark_return_pct"),
            })

        daily.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        for rank, item in enumerate(daily, 1):
            item["rank"] = rank

        results.extend(daily[:TOP_N])

    if not results:
        log("NO-RUN: no matched samples")
        return

    top5 = [x for x in results if x["rank"] <= 5]
    top10 = [x for x in results if x["rank"] <= 10]
    top30 = results

    def report(name, items):
        log("")
        log("---", name, "---")
        log("Samples:", len(items))
        log("Avg MFE:", round(avg(items, "mfe_pct"), 3))
        log("Avg MAE:", round(avg(items, "mae_pct"), 3))
        log(
            "Avg Open->Close:",
            round(avg(items, "open_to_close_pct"), 3)
        )
        log(
            "+3% rate:",
            round(rate(items, "hit_plus_3"), 2)
        )
        log(
            "+5% rate:",
            round(rate(items, "hit_plus_5"), 2)
        )
        log(
            "+10% rate:",
            round(rate(items, "hit_plus_10"), 2)
        )
        log(
            "-3% rate:",
            round(rate(items, "hit_minus_3"), 2)
        )
        log(
            "-5% rate:",
            round(rate(items, "hit_minus_5"), 2)
        )
        log(
            "Benchmark return:",
            round(avg(items, "benchmark_return_pct"), 3)
        )

    report("TOP 5", top5)
    report("TOP 10", top10)
    report("TOP 30", top30)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output = OUTPUT_DIR / "market_score_backtest.json"

    output.write_text(
        json.dumps(
            {
                "schema":
                    "v511-market-score-backtest-v1",
                "formal_prediction":
                    False,
                "rule_version":
                    "market-score-v1-frozen",
                "samples": results,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    log("")
    log("==============================")
    log("MARKET SCORE BACKTEST: PASS")
    log("==============================")
    log("Output:", output)


if __name__ == "__main__":
    main()
