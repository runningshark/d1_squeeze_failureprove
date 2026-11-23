# -*- coding: utf-8 -*-
from core.indicators import sma, stdev, atr
from ._common import SHORT, last_done, point

META = dict(
    id="s14_squeeze", name="布林带收缩突破", timeframe="1d", family="趋势", verdict="偏弱", order=14,
    summary="波动先收窄、再放大：布林带宽度处在近期低位时，价格收在上轨之外做多，收在下轨之外做空。",
    logic=[("方向", "跟着突破方向；默认只做多"), ("入场", "近 5 天内布林带宽度处于过去 120 天最窄的 25%，并且收盘价高于上轨，次日开盘买入（做空：低于下轨）"),
           ("止损", "入场价之外 2 倍 ATR"), ("仓位", "每笔最多亏账户的 1%"), ("出场", "收盘价回到布林带中轨（20 日均线）另一侧")],
    params=[dict(key="n", name="布林带天数", value=20, min=10, max=60, desc="中轨是 N 日均线"),
            dict(key="k", name="布林带倍数", value=2.0, min=1, max=3, step=0.5, desc="上下轨 = 中轨 ± K 倍标准差"),
            dict(key="look", name="比较宽度的天数", value=120, min=30, max=365, desc="和过去多少天的带宽比"),
            dict(key="pct", name="收缩分位 %", value=25, min=5, max=60, step=5, desc="带宽处于这段时间最窄的百分之几才算收缩"),
            dict(key="recent", name="收缩有效天数", value=5, min=1, max=20, desc="最近几天内出现过收缩就算"),
            dict(key="atr", name="ATR 天数", value=20, min=5, max=60, desc="计算平均波动幅度"),
            dict(key="stop_atr", name="止损倍数", value=2.0, min=0.5, max=6, step=0.5, desc="止损放在入场价之外几倍 ATR"), SHORT],
    finding="波动收缩后会放大这一点是真的，但它不告诉你方向。回测里 BTC 夏普 0.64、ETH 0.47，2024 年后接近零；把收缩条件放宽反而更好，说明起作用的是突破本身，不是收缩。",
)


def build(B, P):
    c, n, sh = B["c"], len(B["c"]), P["short"] >= 1
    N, K, L, R = int(P["n"]), P["k"], int(P["look"]), int(P["recent"])
    mid, sd, a = sma(c, N), stdev(c, N), atr(B["h"], B["l"], c, int(P["atr"]))
    width = [(2 * K * sd[i] / mid[i]) if mid[i] else None for i in range(n)]
    tight = [False] * n
    for i in range(N + L, n):
        win = sorted(width[i - L + 1:i + 1])
        tight[i] = width[i] <= win[max(0, int(len(win) * P["pct"] / 100) - 1)]
    recent = [any(tight[max(0, i - R + 1):i + 1]) for i in range(n)]
    up = [mid[i] + K * sd[i] if mid[i] else None for i in range(n)]
    dn = [mid[i] - K * sd[i] if mid[i] else None for i in range(n)]
    ok = [up[i] is not None and a[i] is not None for i in range(n)]
    k = last_done(B)
    dist = P["stop_atr"] * a[k]
    note = "带宽 %.1f%%，%s" % (width[k] * 100, "近期处于收缩状态，条件具备" if recent[k] else "近期没有收缩，即使突破也不进")
    return dict(enter=[ok[i] and recent[i] and c[i] > up[i] for i in range(n)], exit=[ok[i] and c[i] < mid[i] for i in range(n)],
                enter_s=[ok[i] and recent[i] and c[i] < dn[i] for i in range(n)] if sh else None,
                exit_s=[ok[i] and c[i] > mid[i] for i in range(n)] if sh else None,
                stop_dist=[P["stop_atr"] * a[i] if a[i] else None for i in range(n)], sizing="risk", warmup=N + L + 1, exit_name="回到中轨",
                points=dict(long=point(up[k], "收盘价高于（上轨）", stop=up[k] - dist, size=min(1.0, 0.01 / (dist / up[k])), note=note),
                            short=point(dn[k], "收盘价低于（下轨）", stop=dn[k] + dist, size=min(1.0, 0.01 / (dist / dn[k])), note=note) if sh else None),
                levels=[("上轨 / 中轨 / 下轨", "%.2f / %.2f / %.2f" % (up[k], mid[k], dn[k])), ("带宽", "%.1f%%" % (width[k] * 100)), ("ATR", a[k])])
