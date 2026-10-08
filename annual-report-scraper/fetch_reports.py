#!/usr/bin/env python3
"""
企业年报批量下载脚本

两种模式：

1. cninfo  —— 从巨潮资讯网（证监会指定信息披露网站）下载 A 股上市公司年报 PDF。
             覆盖沪、深、北交所全部上市公司，最稳定，推荐优先使用。

     python fetch_reports.py cninfo 600519 000858 --start 2019 --end 2024
     python fetch_reports.py cninfo 贵州茅台 --start 2020
     python fetch_reports.py cninfo --file codes.txt --start 2018 --end 2024

2. site    —— 从公司自己的官网爬取年报 PDF（适合港股、未上市公司、海外公司等）。
             官网结构千差万别，脚本按「链接文字或地址里含年报关键词、且指向 PDF」来识别，
             建议把起点设为官网的「投资者关系 / 定期报告」栏目页，命中率最高。

     python fetch_reports.py site https://ir.example.com/reports --depth 2

依赖：pip install requests
"""

import argparse
import csv
import re
import sys
import time
from collections import deque
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag, unquote

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

CNINFO = "https://www.cninfo.com.cn"
CNINFO_STATIC = "https://static.cninfo.com.cn/"

# 默认剔除的公告：摘要、英文版、已取消的、以及年报相关的其他公告
EXCLUDE_WORDS = ["半年度", "季度", "摘要", "英文", "English", "已取消", "取消", "提示性公告", "更正公告",
                 "补充公告", "审核意见", "说明", "披露", "问询", "回复"]


def safe_name(s):
    return re.sub(r'[\\/:*?"<>|\s]+', "_", s).strip("_")


def download(session, url, dest, retries=3):
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  已存在，跳过：{dest.name}")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    for i in range(retries):
        try:
            with session.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(64 * 1024):
                        f.write(chunk)
            tmp.replace(dest)
            print(f"  已下载：{dest.name}（{dest.stat().st_size / 1e6:.1f} MB）")
            return True
        except requests.RequestException as e:
            print(f"  下载失败（第 {i + 1} 次）：{e}")
            time.sleep(2 * (i + 1))
    tmp.unlink(missing_ok=True)
    return False


# ---------------------------------------------------------------- 巨潮资讯网

class Cninfo:
    def __init__(self, delay=1.0):
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": UA,
            "Referer": CNINFO + "/new/commonUrl/pageOfSearch?url=disclosure/list/search",
            "Origin": CNINFO,
            "X-Requested-With": "XMLHttpRequest",
        })
        self.delay = delay

    def lookup(self, keyword):
        """股票代码或简称 -> (代码, orgId, 简称)。"""
        r = self.s.post(CNINFO + "/new/information/topSearch/query",
                        data={"keyWord": keyword, "maxNum": 10}, timeout=30)
        r.raise_for_status()
        items = r.json() or []
        # A 股公司的 category 为「A股」；优先精确匹配代码或简称
        a_shares = [x for x in items if x.get("category") == "A股"] or items
        for x in a_shares:
            if keyword in (x.get("code"), x.get("zwjc")):
                return x["code"], x["orgId"], x["zwjc"]
        if a_shares:
            x = a_shares[0]
            return x["code"], x["orgId"], x["zwjc"]
        return None

    @staticmethod
    def column_of(code):
        if code.startswith(("6", "9")):
            return "sse"
        if code.startswith(("4", "8", "92")):
            return "bj"
        return "szse"

    def announcements(self, code, org_id, start, end):
        """查询某公司指定年度区间的全部年报类公告。"""
        # 第 N 年的年报在第 N+1 年披露，个别公司会拖到下半年
        se_date = f"{start + 1}-01-01~{end + 1}-12-31"
        columns = [self.column_of(code)]
        if columns[0] != "szse":
            columns.append("szse")  # 兜底：巨潮对部分板块只认 szse
        for column in columns:
            results, page = [], 1
            while True:
                data = {
                    "pageNum": page, "pageSize": 30, "column": column,
                    "tabName": "fulltext", "plate": "", "stock": f"{code},{org_id}",
                    "searchkey": "", "secid": "", "category": "category_ndbg_szsh;",
                    "trade": "", "seDate": se_date, "sortName": "", "sortAsc": "",
                    "isHLtitle": "true",
                }
                r = self.s.post(CNINFO + "/new/hisAnnouncement/query", data=data, timeout=30)
                r.raise_for_status()
                js = r.json()
                results.extend(js.get("announcements") or [])
                if not js.get("hasMore"):
                    break
                page += 1
                time.sleep(self.delay)
            if results:
                return results
        return []


def pick_reports(anns, start, end, include_all=False):
    """从公告列表中挑出每个年度的正式年报（同一年度有修订版时取最新）。"""
    by_year = {}
    for a in anns:
        title = re.sub(r"<[^>]+>", "", a.get("announcementTitle", ""))
        if not include_all and any(w in title for w in EXCLUDE_WORDS):
            continue
        if "年度报告" not in title and "年报" not in title:
            continue
        m = re.search(r"(20\d{2}|19\d{2})\s*年", title)
        if not m:
            continue
        year = int(m.group(1))
        if not start <= year <= end:
            continue
        a = dict(a, title=title, year=year)
        if include_all:
            by_year.setdefault(year, []).append(a)
        else:
            # 同一年度多份（原版 + 修订版）时保留发布时间最晚的一份
            cur = by_year.get(year)
            if cur is None or a.get("announcementTime", 0) > cur[0].get("announcementTime", 0):
                by_year[year] = [a]
    return [a for y in sorted(by_year) for a in by_year[y]]


def run_cninfo(args):
    keywords = list(args.stocks)
    if args.file:
        keywords += [ln.strip() for ln in Path(args.file).read_text(encoding="utf-8").splitlines()
                     if ln.strip() and not ln.startswith("#")]
    if not keywords:
        sys.exit("请提供股票代码 / 简称，或用 --file 指定列表文件")

    end = args.end or datetime.now().year - 1
    start = args.start or end
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cn = Cninfo(delay=args.delay)
    index_rows = []

    for kw in keywords:
        print(f"\n== {kw} ==")
        try:
            hit = cn.lookup(kw)
        except requests.RequestException as e:
            print(f"  查询失败：{e}")
            continue
        if not hit:
            print("  巨潮资讯网上找不到这家公司，跳过")
            continue
        code, org_id, name = hit
        print(f"  {code} {name}（orgId={org_id}）")
        try:
            anns = cn.announcements(code, org_id, start, end)
        except requests.RequestException as e:
            print(f"  获取公告列表失败：{e}")
            continue
        reports = pick_reports(anns, start, end, args.include_all)
        if not reports:
            print(f"  {start}–{end} 年度没有找到年报")
            continue
        for a in reports:
            url = CNINFO_STATIC + a["adjunctUrl"]
            ext = Path(a["adjunctUrl"]).suffix or ".pdf"
            fname = safe_name(f"{code}_{name}_{a['year']}_{a['title']}") + ext
            dest = out / f"{code}_{safe_name(name)}" / fname
            ok = download(cn.s, url, dest)
            pub = datetime.fromtimestamp(a["announcementTime"] / 1000).strftime("%Y-%m-%d")
            index_rows.append([code, name, a["year"], a["title"], pub, url,
                               str(dest) if ok else "下载失败"])
            time.sleep(args.delay)

    write_index(out, ["代码", "简称", "报告年度", "标题", "披露日期", "原始链接", "本地文件"],
                index_rows)


# ---------------------------------------------------------------- 公司官网

REPORT_PAT = re.compile(
    r"年报|年度报告|annual[\s_-]*report|integrated[\s_-]*report|\bAR\s*20\d{2}|"
    r"ESG|可持续发展报告|社会责任报告",
    re.I,
)
ANNUAL_ONLY_PAT = re.compile(r"年报|年度报告|annual[\s_-]*report|\bAR\s*20\d{2}", re.I)
SKIP_EXT = re.compile(r"\.(jpg|jpeg|png|gif|svg|webp|ico|css|js|mp4|mp3|zip|rar|xls|xlsx|doc|docx|ppt|pptx)$", re.I)


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self._href, self._text = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            a = dict(attrs)
            self._href = a.get("href")
            self._text = [a.get("title") or ""]

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join(t.strip() for t in self._text if t.strip())))
            self._href = None


def same_site(u, root_host):
    h = urlparse(u).hostname or ""
    base = root_host.split(".", 1)[-1] if root_host.count(".") >= 2 else root_host
    return h == root_host or h.endswith("." + base) or h == base


def run_site(args):
    s = requests.Session()
    s.headers["User-Agent"] = UA
    start_url = args.url
    root_host = urlparse(start_url).hostname
    pat = REPORT_PAT if args.include_esg else ANNUAL_ONLY_PAT
    out = Path(args.out) / safe_name(root_host)
    seen, found = {start_url}, {}
    queue = deque([(start_url, 0)])
    pages = 0

    while queue and pages < args.max_pages:
        url, depth = queue.popleft()
        try:
            r = s.get(url, timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"  打开失败 {url}：{e}")
            continue
        if "html" not in r.headers.get("Content-Type", "html"):
            continue
        pages += 1
        r.encoding = r.apparent_encoding if r.encoding in (None, "ISO-8859-1") else r.encoding
        print(f"[{pages}] 深度 {depth}：{url}")
        p = LinkParser()
        try:
            p.feed(r.text)
        except Exception:
            continue
        for href, text in p.links:
            if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue
            link = urldefrag(urljoin(url, href))[0]
            path = unquote(urlparse(link).path)
            is_pdf = path.lower().endswith(".pdf") or "pdf" in urlparse(link).query.lower()
            if is_pdf:
                if pat.search(text) or pat.search(path) or args.all_pdfs:
                    if link not in found:
                        found[link] = text or Path(path).name
                        print(f"    ✓ 发现：{found[link][:60]}")
                continue
            if depth < args.depth and link not in seen and same_site(link, root_host) \
                    and not SKIP_EXT.search(path):
                seen.add(link)
                queue.append((link, depth + 1))
        time.sleep(args.delay)

    if not found:
        print("\n没有找到年报 PDF。可以试试：把起点换成「投资者关系 / 定期报告」页面，"
              "加大 --depth，或加 --all-pdfs 先看看都有哪些 PDF。\n"
              "如果页面是 JavaScript 动态加载的，本脚本抓不到，需要改用浏览器自动化（Playwright）。")
        return

    print(f"\n共发现 {len(found)} 个文件，开始下载到 {out}")
    rows = []
    for link, text in found.items():
        name = Path(unquote(urlparse(link).path)).name or "report.pdf"
        label = safe_name(text)[:80]
        fname = f"{label}__{name}" if label and label not in name else name
        if not fname.lower().endswith(".pdf"):
            fname += ".pdf"
        dest = out / safe_name(fname)
        ok = download(s, link, dest)
        year = re.search(r"(19|20)\d{2}", text + " " + name)
        rows.append([year.group(0) if year else "", text, link, str(dest) if ok else "下载失败"])
        time.sleep(args.delay)
    write_index(out, ["年份（推测）", "链接文字", "原始链接", "本地文件"], rows)


def write_index(out, header, rows):
    if not rows:
        return
    out.mkdir(parents=True, exist_ok=True)
    path = out / "index.csv"
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerows(rows)
    print(f"\n清单已写入 {path}")


def main():
    ap = argparse.ArgumentParser(description="企业年报批量下载",
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    sub = ap.add_subparsers(dest="mode", required=True)

    c = sub.add_parser("cninfo", help="从巨潮资讯网下载 A 股上市公司年报")
    c.add_argument("stocks", nargs="*", help="股票代码或简称，可写多个")
    c.add_argument("--file", help="列表文件，每行一个代码或简称")
    c.add_argument("--start", type=int, help="起始报告年度（默认与 --end 相同）")
    c.add_argument("--end", type=int, help="截止报告年度（默认去年）")
    c.add_argument("--include-all", action="store_true",
                   help="不过滤，摘要、英文版、修订前版本等一并下载")
    c.add_argument("--out", default="年报", help="保存目录（默认 ./年报）")
    c.add_argument("--delay", type=float, default=1.0, help="请求间隔秒数（默认 1）")
    c.set_defaults(func=run_cninfo)

    w = sub.add_parser("site", help="从公司官网爬取年报 PDF")
    w.add_argument("url", help="起始网址，建议用投资者关系 / 定期报告页")
    w.add_argument("--depth", type=int, default=2, help="向下翻几层链接（默认 2）")
    w.add_argument("--max-pages", type=int, default=200, help="最多访问多少个网页（默认 200）")
    w.add_argument("--include-esg", action="store_true", help="同时下载 ESG / 社会责任报告")
    w.add_argument("--all-pdfs", action="store_true", help="下载站内找到的所有 PDF")
    w.add_argument("--out", default="年报", help="保存目录（默认 ./年报）")
    w.add_argument("--delay", type=float, default=0.5, help="请求间隔秒数（默认 0.5）")
    w.set_defaults(func=run_site)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
