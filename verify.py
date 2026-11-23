# -*- coding: utf-8 -*-
"""
复现脚本：python verify.py
只用 Python 自带模块。读取 data/ 里的币安现货日线快照，用原项目同一套回测引擎（core/engine.py）检验：
  1. 布林带收缩突破（s14）和普通趋势突破（s02）逐币对比：全期 / 2024 年前 / 2024 年后，只做多和允许做空，扣成本
  2. 关键检验：收缩条件放宽 / 完全去掉（收缩分位 = 100%）后结果怎么变
  3. 其他参数敏感性，6 个币合计 R
  4. 2024 年后逐币的笔数、持有天数、胜率、平均每笔 R
收益单位 R：每笔计划亏损（账户的 1%）。结果打印到屏幕，并写入 results/output.txt。
"""
import gzip
import importlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from core.engine import simulate, daily_curve, curve_stats  # noqa: E402
from core.data import day  # noqa: E402

CFG = json.load(open(os.path.join(HERE, "entry.json"), encoding="utf-8"))
MOD = importlib.import_module("strategies." + CFG["module"])
BASE = importlib.import_module("strategies." + CFG["baseline"])
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "DOGEUSDT"]
COST, RISK = 0.001, 0.01
OOS = "2024-01-01"
SEGS = (("全期", None, None), ("2024 年前", None, OOS), ("2024 年后（样本外）", OOS, None))


def load(sym):
    with gzip.open(os.path.join(HERE, "data", sym + "_1d.json.gz"), "rt") as f:
        B = json.load(f)
    B["done"] = [True] * len(B["c"])
    return B


def params(mod, over=None):
    P = {p["key"]: p["value"] for p in mod.META["params"]}
    P.update(CFG.get("params", {}) if mod is MOD else {})
    P.update(over or {})
    return P


def cut(x, e):
    return {k: (v[:e] if isinstance(v, list) else v) for k, v in x.items()}


def run(mod, B, P, a=None, b=None):
    sig = mod.build(B, P)
    n = len(B["c"])
    s = sig["warmup"]
    if a:
        s = max(s, next(i for i in range(n) if day(B["t"][i]) >= a))
    if b:
        e = next((i for i in range(n) if day(B["t"][i]) >= b), n)
        B, sig = cut(B, e), cut(sig, e)
    r = simulate(B, sig, COST, RISK, s, 1.0, "1d")
    st = curve_stats(daily_curve(r["curve"]))
    R = sum(t["r"] for t in r["trades"] if t.get("r") is not None)
    return st, len(r["trades"]), R


def _unused_corr(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sx = sum((a - mx) ** 2 for a in x) ** .5
    sy = sum((b - my) ** 2 for b in y) ** .5
    return sxy / (sx * sy) if sx and sy else 0.0


def main():
    D = {s: load(s) for s in SYMBOLS}
    out = ["# %s 复现结果\n" % MOD.META["name"],
           "对照：%s。成本单边 %.2f%%；每笔风险 1%%；R = 每笔计划亏损。\n" % (BASE.META["name"], COST * 100)]
    for sh in (0, 1):
        out.append("\n## 1. 逐币对比（%s）\n" % ("只做多" if sh == 0 else "允许做空"))
        out.append("| 币 | 段 | 普通突破 笔数 / 收益 / 夏普 / R | 布林收缩突破 笔数 / 收益 / 夏普 / R |\n|---|---|---|---|")
        tot = {}
        for s in SYMBOLS:
            for name, a, b in SEGS:
                cells = []
                for mod in (BASE, MOD):
                    st, n, R = run(mod, D[s], params(mod, {"short": sh}), a, b)
                    tot[(name, mod)] = tot.get((name, mod), 0) + R
                    cells.append("%d / %+.0f%% / %.2f / %+.1fR" % (n, st["ret"] * 100, st["sharpe"], R))
                out.append("| %s | %s | %s |" % (s, name, " | ".join(cells)))
        for name, _, _ in SEGS:
            out.append("| **6 币合计** | %s | %+.1fR | %+.1fR |" % (name, tot[(name, BASE)], tot[(name, MOD)]))

    def total(over):
        return [sum(run(MOD, D[s], params(MOD, over), a, b)[2] for s in SYMBOLS) for _, a, b in SEGS[1:]]
    out.append("\n## 2. 收缩条件放宽 / 去掉（只做多，6 个币合计 R）\n")
    out.append("收缩分位：布林带宽度处在过去 120 天最窄的百分之几才算收缩；100% 等于完全不要求收缩，只剩\"收盘站上布林上轨就买、跌回中轨就卖\"。\n")
    out.append("| 收缩分位 | 2024 年前 | 2024 年后 |\n|---|---|---|")
    for pct in CFG["squeeze_grid"]:
        v = total({"pct": pct})
        tag = "（默认）" if pct == params(MOD)["pct"] else ("（不要求收缩）" if pct >= 100 else "")
        out.append("| %d%%%s | %+.1fR | %+.1fR |" % (pct, tag, v[0], v[1]))
    out.append("\n## 3. 其他参数（只做多，6 个币合计 R）\n")
    out.append("| 参数 | 2024 年前 | 2024 年后 |\n|---|---|---|")
    v = total({})
    out.append("| 默认 | %+.1fR | %+.1fR |" % tuple(v))
    for over in CFG["grid"]:
        out.append("| %s | %+.1fR | %+.1fR |" % ((json.dumps(over),) + tuple(total(over))))
    out.append("\n## 4. 2024 年后逐币交易（只做多，默认参数）\n")
    out.append("| 币 | 笔数 | 平均持有天数 | 胜率 | 平均每笔 R |\n|---|---|---|---|---|")
    for s in SYMBOLS:
        B = D[s]
        sig = MOD.build(B, params(MOD))
        st0 = max(sig["warmup"], next(i for i in range(len(B["c"])) if day(B["t"][i]) >= OOS))
        t = simulate(B, sig, COST, RISK, st0, 1.0, "1d")["trades"]
        n = max(1, len(t))
        out.append("| %s | %d | %.1f | %.0f%% | %+.2f |" % (s, len(t), sum(x["bars"] for x in t) / n,
                   sum(1 for x in t if x["r"] > 0) / n * 100, sum(x["r"] for x in t) / n))
    text = "\n".join(out) + "\n"
    print(text)
    with open(os.path.join(HERE, "results", "output.txt"), "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()
