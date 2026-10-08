# 企业年报批量下载

```bash
pip install requests openpyxl   # openpyxl 只在用 Excel 名单时需要
```

## 最简单的用法：问答模式

装好 Python 和依赖后，**直接双击 `fetch_reports.py`**（或命令行运行 `python fetch_reports.py`，或把全部代码粘贴进 Jupyter / PyCharm 运行），按提示输入：

```
股票代码或简称（多个用空格隔开），
或者把名单文件（Excel / CSV / TXT）拖进这个窗口后回车：600519 000858 宁德时代
起始报告年度（2025）：2024
截止报告年度（2025）：2025
```

公司多时把名单文件拖进窗口（或粘贴文件路径）即可。名单文件里有「代码」列就按代码查，没有就按「简称／名称／公司」列查；Excel 把 000858 存成 858、写成 600519.SH 都能识别。

年报下载到脚本旁边的 `年报` 文件夹（Jupyter 里是当前工作目录下的 `年报`），同时生成：

- `index.csv`：每份年报的代码、年度、标题、披露日期、链接；
- `未完成清单.csv`：找不到的公司、缺失的年度、下载失败的条目。网络问题直接重跑，已下载的会跳过。

### 第一次使用的准备（Windows）

1. 到 https://www.python.org/downloads/ 下载安装 Python，安装时**勾选 “Add python.exe to PATH”**。
2. 按 Win+R，输入 `cmd` 回车，在黑色窗口里运行：`pip install requests openpyxl`
   （下载慢可以换清华镜像：`pip install requests openpyxl -i https://pypi.tuna.tsinghua.edu.cn/simple`）
3. 双击 `fetch_reports.py` 即可。

## 模式一：巨潮资讯网（A 股上市公司，推荐）

巨潮资讯网是证监会指定的信息披露网站，沪、深、北交所所有上市公司的年报都在上面，比逐家翻公司官网稳定得多。

```bash
# 按代码或简称，可一次写多家
python fetch_reports.py cninfo 600519 000858 --start 2019 --end 2024
python fetch_reports.py cninfo 贵州茅台 宁德时代 --start 2020

# 公司多时用名单文件（Excel / CSV / TXT 均可）
python fetch_reports.py cninfo --file 名单.xlsx --start 2024 --end 2025
```

- 报告年度：`--start 2020 --end 2024` 指 2020—2024 **财年**的年报（实际在次年披露，脚本已处理）。只写 `--start` 时截止到去年；两个都不写时只下载去年的年报。
- 默认只保留正式年报全文：剔除摘要、英文版、半年报、更正／提示性公告；同一年度有修订版时只留最新一版。要全部下载加 `--include-all`。
- 文件存到 `./年报/代码_简称/`，同时生成 `index.csv` 和 `未完成清单.csv`。
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
