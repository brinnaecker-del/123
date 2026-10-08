"""由 panel_raw.pkl 生成回归样本 sample.pkl（sample.load 的唯一调用处）。

用法：python -I 04b_sample.py <派生目录>
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sample import load

der = sys.argv[1]
s = load(os.path.join(der, 'panel_raw.pkl'))
s.to_pickle(os.path.join(der, 'sample.pkl'))
print('回归样本', len(s), '个观测，', s.Stkcd.nunique(), '家公司；SOE 原始缺失记为 0 的', int(s.SOE_raw.isna().sum()), '个')
