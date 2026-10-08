# 企业年报批量下载

```bash
pip install requests
```

## 模式一：巨潮资讯网（A 股上市公司，推荐）

巨潮资讯网是证监会指定的信息披露网站，沪、深、北交所所有上市公司的年报都在上面，比逐家翻公司官网稳定得多。

```bash
# 按代码或简称，可一次写多家
python fetch_reports.py cninfo 600519 000858 --start 2019 --end 2024
python fetch_reports.py cninfo 贵州茅台 宁德时代 --start 2020

# 公司多时写进文件，每行一个
python fetch_reports.py cninfo --file codes.txt --start 2018 --end 2024
```

- 报告年度：`--start 2020 --end 2024` 指 2020—2024 **财年**的年报（实际在次年披露，脚本已处理）。只写 `--start` 时截止到去年；两个都不写时只下载去年的年报。
- 默认只保留正式年报全文：剔除摘要、英文版、半年报、更正／提示性公告；同一年度有修订版时只留最新一版。要全部下载加 `--include-all`。
- 文件存到 `./年报/代码_简称/`，同时生成 `./年报/index.csv`（代码、年度、标题、披露日期、原始链接、本地路径）。
- 已下载的文件会跳过，中断后重跑即可续传。

## 模式二：公司官网（港股、未上市、海外公司）

```bash
python fetch_reports.py site https://ir.example.com/zh/reports
python fetch_reports.py site https://www.example.com --depth 3 --include-esg
```

从起始网址开始在同一网站内逐层翻链接，链接文字或文件名里有「年报／年度报告／Annual Report」且指向 PDF 的就下载。

- 起点最好直接填「投资者关系 → 定期报告／年度报告」那一页，命中率最高。
- `--depth` 翻几层（默认 2），`--max-pages` 最多访问多少页（默认 200）。
- `--include-esg` 同时下载 ESG／社会责任报告；`--all-pdfs` 下载找到的所有 PDF，适合先摸清网站结构。
- 局限：页面内容靠 JavaScript 动态加载的网站，这个脚本抓不到，需要改用 Playwright 等浏览器自动化。

## 注意

- 默认每次请求间隔 1 秒（`--delay`），请不要调得太低，以免被封 IP。
- 「国家企业信用信息公示系统」里的工商年报有滑块验证码，不在本脚本范围内。
