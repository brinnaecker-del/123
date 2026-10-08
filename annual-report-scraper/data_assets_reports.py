"""
数据资产入表公司年报批量下载（数据来源：巨潮资讯网）

用法：在 PyCharm 里右键本文件 → 运行，看一眼提示后按回车开始。
  · 公司名单写在下面的 COMPANIES 里，写简称或 6 位股票代码都行；
  · 年报按年度分文件夹保存到 SAVE_DIR；
  · 跑完生成「公司核对表.xlsx」：每家公司匹配到的股票代码、各年度年报是否下载成功。
中途断了直接重跑，已下载的文件会自动跳过。
需要先安装：pip install requests openpyxl
"""

import csv
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("缺少 requests 库，请先在终端运行：pip install requests")
    input("按回车键退出…")
    sys.exit(1)

# ============================ 需要改的只有这里 ============================
SAVE_DIR = r"E:\数据资产入表年报"   # 保存位置
YEARS = [2024, 2025]               # 下载哪几个报告年度的年报

# 《中国企业数据资产入表情况跟踪报告》2025 年度，表 2.8「136 家数据资源入表公司一览表」，按原表顺序。
# 2024 年名单中另有 6 家不在本表，拿到后加在末尾即可（简称或股票代码都行，用空格或换行隔开）。
COMPANIES = """
中国移动 中国联通 中国电信 科大讯飞 同方股份 合合信息 每日互动 *ST航图 拓尔思 卓创资讯
九州通 广联达 开普云 南钢股份 圆通速递 山鹰国际 中国交建 小商品城 航天发展 宁夏建材
神州数码 数字政通 孩子王 三钢闽光 中材国际 华大基因 美年健康 航天信息 中信银行 北汽蓝谷
爱尔眼科 万兴科技 东湖高新 南方航空 淘天瑞声 韵达股份 龙源电力 国源科技 中顺洁柔 健之佳
金域医学 国泰海通 上海钢联 中远海科 山东黄金 捷顺科技 东方证券 广弘控股 招商港口 设计总院
申通快递 杭州银行 招商证券 山东高速 中信证券 人民网 物产中大 蓝色光标 日照港 中公教育
佳华科技 中文在线 吉视传媒 金盘科技 宁波银行 中泰证券 山东钢铁 北京建材 泰达股份 新希望
广电运通 泸州老窖 何氏眼科 齐鲁银行 泰尔股份 粤高速A 世纪恒通 西部证券 皖通高速 光启技术
中信建投 五芳斋 山金国际 药易购 蕾奥规划 新疆天业 渝农商行 天威视讯 浙江交科 首创环保
南京公用 首钢股份 创业环保 济南中拓 财通证券 通行宝 上海建工 镇洋发展 东华软件 郑州煤电
王力安防 海格通信 零点有数 方正科技 航天工程 长江证券 广电计量 轻纺城 南方传媒 青岛啤酒
大西洋 金隅集团 金圆股份 顺控发展 中原环保 山东玻纤 中百集团 华设集团 吉大通信 浙江建投
中原高速 武商集团 凌云光 信达证券 绿城水务 上港集团 兴通股份 青拓技术 隧道股份 金房能源
上海电气 青岛港 天亿马 合百集团 厦门港务 北辰实业
"""
# ========================================================================

DELAY = 1.0  # 每次请求间隔（秒），别调太小，以免被网站限制

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
CNINFO = "https://www.cninfo.com.cn"
CNINFO_STATIC = "https://static.cninfo.com.cn/"

# 标题含这些词的公告不要：摘要、英文版、H 股版（港股口径，非 A 股年报）、各类附属公告
EXCLUDE_WORDS = ["半年度", "季度", "摘要", "英文", "English", "H股", "海外监管", "已取消", "取消",
                 "提示性公告", "更正公告", "补充公告", "审核意见", "说明", "披露", "问询", "回复"]


def safe_name(s):
    return re.sub(r'[\\/:*?"<>|\s]+', "_", s).strip("_")


def norm(s):
    """统一全角半角、大小写和空格，用于比较简称。"""
    return unicodedata.normalize("NFKC", s or "").replace(" ", "").upper()


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


class Cninfo:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": UA,
            "Referer": CNINFO + "/new/commonUrl/pageOfSearch?url=disclosure/list/search",
            "Origin": CNINFO,
            "X-Requested-With": "XMLHttpRequest",
        })

    def lookup(self, keyword):
        """简称或代码 -> ((代码, orgId, 简称), 候选列表)。

        只接受代码或简称完全一致的结果，避免把名字相近的公司当成同一家；
        对不上时返回候选，写进核对表供人工确认。
        """
        r = self.s.post(CNINFO + "/new/information/topSearch/query",
                        data={"keyWord": keyword, "maxNum": 10}, timeout=30)
        r.raise_for_status()
        items = r.json() or []
        items = [x for x in items if x.get("category") == "A股"] or items
        for x in items:
            if norm(keyword) in (norm(x.get("code")), norm(x.get("zwjc"))):
                return (x["code"], x["orgId"], x["zwjc"]), []
        return None, [f"{x.get('zwjc')}({x.get('code')})" for x in items[:5]]

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
                time.sleep(DELAY)
            if results:
                return results
        return []


def pick_reports(anns, years):
    """每个年度挑一份正式年报全文；同一年度有修订版时取发布最晚的一份。"""
    best = {}
    for a in anns:
        title = re.sub(r"<[^>]+>", "", a.get("announcementTitle", ""))
        if any(w in title for w in EXCLUDE_WORDS):
            continue
        if "年度报告" not in title and "年报" not in title:
            continue
        m = re.search(r"(20\d{2})\s*年", title)
        if not m or int(m.group(1)) not in years:
            continue
        year = int(m.group(1))
        if year not in best or a.get("announcementTime", 0) > best[year].get("announcementTime", 0):
            best[year] = dict(a, title=title)
    return best


def write_table(path, header, rows):
    """优先存成 Excel（股票代码保持文本，不丢前导 0）；没装 openpyxl 时存 CSV。"""
    try:
        import openpyxl
    except ImportError:
        path = path.with_suffix(".csv")
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerows([header] + rows)
        return path
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(header)
    for row in rows:
        ws.append(row)
    for col in ws.columns:
        width = max(len(str(c.value or "")) for c in col)
        ws.column_dimensions[col[0].column_letter].width = min(max(8, width * 1.8), 60)
    ws.freeze_panes = "A2"
    wb.save(path)
    return path


def main():
    names = COMPANIES.split()
    years = sorted(set(YEARS))
    out = Path(SAVE_DIR)
    if out.anchor and not Path(out.anchor).exists():
        sys.exit(f"电脑上没有 {out.anchor} 这个盘，请把代码里的 SAVE_DIR 改成存在的位置，比如 D:\\数据资产入表年报")
    print(f"名单共 {len(names)} 家公司，下载 {'、'.join(map(str, years))} 年度年报")
    print(f"保存到：{out}")
    input("\n按回车开始…")
    out.mkdir(parents=True, exist_ok=True)

    cn = Cninfo()
    table, detail, seen = [], [], {}
    for n, kw in enumerate(names, 1):
        print(f"\n== [{n}/{len(names)}] {kw} ==")
        row = {"序号": n, "名单写法": kw, "股票代码": "", "巨潮简称": ""}
        row.update({f"{y}年报": "" for y in years})
        row["备注"] = ""
        table.append(row)
        try:
            hit, cands = cn.lookup(kw)
        except requests.RequestException as e:
            row["备注"] = "查询失败（网络问题，重跑即可）"
            print(f"  查询失败：{e}")
            continue
        if not hit:
            row["备注"] = "巨潮上没有完全同名的公司，请核对简称"
            if cands:
                row["备注"] += "；候选：" + "、".join(cands)
            print("  " + row["备注"])
            continue
        code, org_id, name = hit
        row.update({"股票代码": code, "巨潮简称": name})
        if code in seen:
            row.update({f"{y}年报": f"同第{seen[code]}行" for y in years})
            row["备注"] = "名单里重复出现"
            print(f"  与第 {seen[code]} 行是同一家公司，跳过")
            continue
        seen[code] = n
        print(f"  {code} {name}")
        try:
            reports = pick_reports(cn.announcements(code, org_id, years[0], years[-1]), years)
        except requests.RequestException as e:
            row["备注"] = "获取公告列表失败（网络问题，重跑即可）"
            print(f"  获取公告列表失败：{e}")
            continue
        for y in years:
            a = reports.get(y)
            if not a:
                row[f"{y}年报"] = "没找到"
                print(f"  {y} 年度没找到年报")
                continue
            url = CNINFO_STATIC + a["adjunctUrl"]
            ext = Path(a["adjunctUrl"]).suffix or ".pdf"
            dest = out / f"{y}年报" / (safe_name(f"{code}_{name}_{a['title']}") + ext)
            ok = download(cn.s, url, dest)
            row[f"{y}年报"] = "已下载" if ok else "下载失败（重跑即可）"
            pub = datetime.fromtimestamp(a["announcementTime"] / 1000).strftime("%Y-%m-%d")
            detail.append([code, name, y, a["title"], pub, url, str(dest) if ok else "下载失败"])
            time.sleep(DELAY)

    header = list(table[0].keys())
    try:
        p1 = write_table(out / "公司核对表.xlsx", header, [list(r.values()) for r in table])
        p2 = write_table(out / "年报清单.xlsx",
                         ["股票代码", "简称", "报告年度", "公告标题", "披露日期", "原始链接", "本地文件"], detail)
    except PermissionError:
        sys.exit("写不进核对表：请先关掉 Excel 里打开的「公司核对表」或「年报清单」，再重新运行一次")

    got = sum(1 for r in table for y in years if r[f"{y}年报"] == "已下载")
    todo = [r for r in table
            if any(not (r[f"{y}年报"] == "已下载" or r[f"{y}年报"].startswith("同第")) for y in years)]
    print("\n" + "=" * 50)
    print(f"汇总：名单 {len(names)} 家，下载成功 {got} 份")
    print(f"核对表：{p1}")
    print(f"年报清单：{p2}")
    if todo:
        print(f"\n下面 {len(todo)} 家需要看一下（详情见核对表）：")
        for r in todo:
            status = "，".join(f"{y}：{r[f'{y}年报'] or '-'}" for y in years)
            print(f"  {r['序号']}. {r['名单写法']}  {r['股票代码']}  {status}  {r['备注']}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:  # 先显示原因，别让窗口一闪就关
        if e.code not in (None, 0):
            print(e)
    except Exception:
        import traceback
        traceback.print_exc()
        print("\n出错了，请把上面的报错信息截图发给我。")
    input("\n按回车键退出…")
