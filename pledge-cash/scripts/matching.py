"""第一大股东与出质方的匹配规则（04、05 共用，保证质押比例与平仓压力覆盖同一出质方）。

统计表：同一出质方ID在不同时期的任一名称与第一大股东名称相同即匹配；先用基本口径，
某公司—年度基本口径无任何匹配时，再用宽松口径（names.norm_loose）。
明细表事件：出质方ID属于该公司—年度统计表已匹配的ID，或事件任一记录的名称（基本/宽松口径）与第一大股东名称相同。
"""
import pandas as pd
from names import norm_basic, norm_loose


def top1_names(top1):
    t = top1[['Stkcd', 'year', 'Top1Name']].copy()
    t['nb'] = t['Top1Name'].map(norm_basic)
    t['nl'] = t['Top1Name'].map(norm_loose)
    return t


def match_stat(top1, ye, st, loose=True):
    """top1: 第一大股东面板；ye: 统计表出质方年末余额；st: 统计表全部记录（取历史名称）。
    返回 (Stkcd, year, PledgorID, stage) 的匹配表。"""
    t = top1_names(top1)
    nm = st[['Symbol', 'PledgorID', 'Pledgor']].drop_duplicates().rename(columns={'Symbol': 'Stkcd'})
    nm['nb'] = nm['Pledgor'].map(norm_basic)
    nm['nl'] = nm['Pledgor'].map(norm_loose)
    cand = ye.rename(columns={'Symbol': 'Stkcd'})[['Stkcd', 'PledgorID', 'year']].drop_duplicates()
    c1 = cand.merge(nm[['Stkcd', 'PledgorID', 'nb']].drop_duplicates(), on=['Stkcd', 'PledgorID'])
    m1 = t[['Stkcd', 'year', 'nb']].merge(c1, on=['Stkcd', 'year', 'nb'])[['Stkcd', 'year', 'PledgorID']].drop_duplicates()
    m1['stage'] = 'basic'
    if not loose:
        return m1
    done = set(zip(m1.Stkcd, m1.year))
    rest = t[[k not in done for k in zip(t.Stkcd, t.year)]]
    c2 = cand.merge(nm[['Stkcd', 'PledgorID', 'nl']].drop_duplicates(), on=['Stkcd', 'PledgorID'])
    m2 = rest[['Stkcd', 'year', 'nl']].merge(c2, on=['Stkcd', 'year', 'nl'])[['Stkcd', 'year', 'PledgorID']].drop_duplicates()
    m2['stage'] = 'loose'
    return pd.concat([m1, m2], ignore_index=True)


def match_events(ey, info, top1, matched):
    """ey: 事件—年度；info: 事件信息（含 names、names_loose、PledgorID、Stkcd）；matched: match_stat 的输出。
    返回与第一大股东匹配的事件—年度（附 match_by 说明）。"""
    t = top1_names(top1)
    x = ey.merge(info[['Stkcd', 'PledgorID', 'names', 'names_loose']], left_on='EventID', right_index=True)
    x = x.merge(t[['Stkcd', 'year', 'nb', 'nl']], on=['Stkcd', 'year'])
    byname = [(a in s) or (b in sl) for a, b, s, sl in zip(x.nb, x.nl, x.names, x.names_loose)]
    ids = set(zip(matched.Stkcd, matched.year, matched.PledgorID))
    byid = [(a, y, p) in ids for a, y, p in zip(x.Stkcd, x.year, x.PledgorID)]
    x['by_name'], x['by_id'] = byname, byid
    x = x[x.by_name | x.by_id].copy()
    return x.drop(columns=['names', 'names_loose', 'nb', 'nl'])
