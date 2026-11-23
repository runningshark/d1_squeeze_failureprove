# -*- coding: utf-8 -*-
from core.indicators import sma, prev_high, prev_low, atr
from ._common import SHORT, last_done, point

META = dict(
    id="s02_breakout", name="趋势突破（主策略）", timeframe="1d", family="趋势", verdict="主推", order=2,
    summary="大方向向上时，价格创新高就买，亏损固定为账户的 1%，一直拿到趋势结束。这是登记了纸面实验的主策略，默认只做多。",
    logic=[("方向", "收盘价高于 200 日均线才做多（打开做空后：低于 200 日均线才做空）"),
           ("入场", "收盘价创 20 日新高，次日开盘买入（做空：创 20 日新低）"),
           ("止损", "入场价减 2 倍 ATR（做空：加 2 倍 ATR）"), ("仓位", "每笔最多亏账户的 1%：仓位 = 1% ÷ 止损距离，上限 100%"),
           ("出场", "收盘价跌破 10 日新低，次日开盘卖出（做空：升破 10 日新高）")],
    params=[dict(key="ma", name="方向均线天数", value=200, min=1, max=400, desc="只在价格高于这条均线时做多、低于时做空；填 1 表示不过滤"),
            dict(key="entry", name="突破天数", value=20, min=5, max=120, desc="收盘价高于前 N 天最高价时做多，低于前 N 天最低价时做空"),
            dict(key="exit", name="离场天数", value=10, min=3, max=60, desc="多单：收盘价低于前 N 天最低价离场；空单相反"),
            dict(key="atr", name="ATR 天数", value=20, min=5, max=60, desc="用多少天计算平均波动幅度"),
            dict(key="stop_atr", name="止损倍数", value=2.0, min=0.5, max=6, step=0.5, desc="止损放在入场价之外几倍 ATR"), SHORT],
    finding="第 2、4 课：ETH 和 BTC 上都为正，改参数不崩；但利润集中在少数几笔大行情，2023 年以来很平淡。",
)


def build(B, P, extra=None, extra_s=None):
    c, h, l, n = B["c"], B["h"], B["l"], len(B["c"])
    N, X, sh, use_ma = int(P["entry"]), int(P["exit"]), P["short"] >= 1, P["ma"] > 1
    ma = sma(c, int(P["ma"])) if use_ma else [None] * n
    hiN, loN, hiX, loX, a = prev_high(h, N), prev_low(l, N), prev_high(h, X), prev_low(l, X), atr(h, l, c, int(P["atr"]))
    ok = [hiN[i] is not None and a[i] is not None and (ma[i] is not None or not use_ma) for i in range(n)]
    enter = [ok[i] and c[i] > hiN[i] and (not use_ma or c[i] > ma[i]) and (extra is None or bool(extra[i])) for i in range(n)]
    enter_s = [ok[i] and c[i] < loN[i] and (not use_ma or c[i] < ma[i]) and (extra_s is None or bool(extra_s[i])) for i in range(n)] if sh else None
    k = last_done(B)
    dist = P["stop_atr"] * a[k]
    up = max(max(h[k - N + 1:k + 1]), ma[k] or 0)                              # 今天收盘要高于它才做多
    dn = min(min(l[k - N + 1:k + 1]), ma[k] or float("inf"))                   # 今天收盘要低于它才做空
    risk = 0.01
    return dict(enter=enter, exit=[loX[i] is not None and c[i] < loX[i] for i in range(n)],
                enter_s=enter_s, exit_s=[hiX[i] is not None and c[i] > hiX[i] for i in range(n)] if sh else None,
                stop_dist=[P["stop_atr"] * a[i] if a[i] else None for i in range(n)], sizing="risk",
                warmup=max(int(P["ma"]), N, int(P["atr"])) + 1, exit_name="收盘破%d日高低" % X,
                points=dict(long=point(up, "收盘价高于", stop=up - dist, size=min(1.0, risk / (dist / up))),
                            short=point(dn, "收盘价低于", stop=dn + dist, size=min(1.0, risk / (dist / dn))) if sh else None),
                levels=[("方向均线", ma[k]), ("%d 日最高 / 最低" % N, "%s / %s" % (_p(max(h[k - N + 1:k + 1])), _p(min(l[k - N + 1:k + 1])))),
                        ("多单离场线（%d 日最低）" % X, min(l[k - X + 1:k + 1])), ("空单离场线（%d 日最高）" % X, max(h[k - X + 1:k + 1])),
                        ("ATR", a[k])])


def _p(x):
    return ("%.0f" % x) if x >= 1000 else ("%.2f" % x) if x >= 1 else ("%.5f" % x)
