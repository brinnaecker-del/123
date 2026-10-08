"""股东名称规范化与名义持有人识别（01、02、04、05 共用）。"""
import re

NOMINEE = re.compile(r'香港中央结算|HKSCC|代理人|NOMINEE', re.I)


def norm_basic(s):
    """去空白、全角括号转半角。"""
    s = str(s).strip().replace('（', '(').replace('）', ')')
    return re.sub(r'\s+', '', s)


def norm_loose(s):
    """宽松口径：在 norm_basic 基础上去掉“(原名…)”注记、“及其一致行动人”、末尾编号、
    开头的地区括注（如“(香港)”），统一“有限责任公司”为“有限公司”，再去掉括号符号本身。
    仅在同一公司—年度内、基本口径未能匹配时使用。"""
    s = norm_basic(s)
    s = re.sub(r'\(原名[^)]*\)', '', s)
    s = re.sub(r'及其一致行动人.*$', '', s)
    s = re.sub(r'\d+$', '', s)
    s = re.sub(r'^\([^)]*\)', '', s)
    s = s.replace('有限责任公司', '有限公司')
    return s.replace('(', '').replace(')', '')


def is_nominee(s):
    return bool(NOMINEE.search(str(s)))
