# 对话记录：GitHub 新建仓库，以及让 Claude 往仓库存档

日期：2026-10-21

## 1. 怎么新建仓库

在 GitHub 首页：

1. 点右上角 **「+ ▾」** →「新建仓库」（New repository），或直接打开 https://github.com/new
2. 填写信息：
   - **Owner**：默认 `brinnaecker-del`
   - **Repository name**：只能用英文、数字、`-`、`_`
   - **Public / Private**：公开 / 私有
   - 建议勾选 **Add a README file**
3. 点 **Create repository**

## 2. 仓库建好后能做什么

新仓库是 `brinnaecker-del/Kris`（私有，带一个 README，描述「学习」）。

> 注意：浏览器开着网页翻译时，仓库名也会被翻成中文（「Kris」显示成「克里斯」）。真实名字以地址栏为准。

- **网页上加文件**：Add file → Create new file / Upload files → Commit changes
- **改 README**：点 README 右边的铅笔图标 → Commit changes
- **下载到电脑**：Code → 复制 HTTPS 地址 → `git clone 地址`；改完运行 `git add .` → `git commit -m "说明"` → `git push`
- **让 Claude 写代码**：把仓库地址发给 Claude

## 3. 把对话存进仓库：遇到的问题和解决办法

| 尝试 | 结果 | 原因 |
| --- | --- | --- |
| 存到 `CANGKKUA1` | 失败 | 没有叫这个名字的仓库 |
| 存到 `Kris` | 失败 | 会话没有这个仓库的权限 |
| 存到 `123` | 能读不能推 | 会话没有选中这个仓库 |

GitHub 上的 Claude App 已经安装，权限也是「所有仓库」，这一步没有问题。

**解决办法：** 在 https://claude.ai/connect-github **断开 GitHub 再重新连接**。之后 Claude 就能把仓库加进会话，并克隆、推送。

## 4. 以后每次对话都存进仓库

- 新建会话时选中 `brinnaecker-del/123`
- 可以在仓库根目录放一个 `CLAUDE.md`，写上规则：「每次对话结束前，把对话整理成 Markdown 存到 `对话记录/日期-主题.md`，并提交推送。」这样 Claude 每次都会照做
- 如果 Claude 忘了，说一句「存档」就行
