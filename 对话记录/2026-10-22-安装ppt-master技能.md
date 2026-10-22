# 对话记录：安装 ppt-master 技能

日期：2026-10-22

## 1. 安装 hugohe3/ppt-master 技能

**问题：** 安装 GitHub 上 hugohe3 的 ppt-master 技能（用 AI 生成可编辑 PPTX）。

**做法：**
- 下载 `hugohe3/ppt-master`（6.7.2 版），把 `skills/ppt-master` 复制到 `~/.claude/skills/ppt-master`
- 运行技能自带的完整性检查 `attribution_guard.py`：通过
- 安装 Python 依赖：`pip install -r ~/.claude/skills/ppt-master/requirements.txt`
  - 遇到问题：系统自带的 `blinker` 无法被 pip 卸载
  - 解决：加上 `--ignore-installed blinker` 重装，导入测试通过

**结论：** 技能已安装，但云端会话环境是临时的，**只在当次会话有效**，新会话需要重装。

## 2. 让以后的会话自动安装（未完成）

**计划：** 在仓库里加 `.claude/settings.json`（登记 ppt-master 插件源并启用）和一个启动钩子（自动装 Python 依赖）。

**结果：** 被安全检查拦下。原因是这样每次会话启动都会自动从外部仓库下载并运行代码，需要用户本人决定。

**以后如果想要：** 回复「同意自动安装」，或在 Claude Code 权限设置里允许此类操作。

## 3. 用 ppt-master 做开题汇报 PPT（中止）

- 加载了技能，完整性检查通过，按规则选定「Generate PPTX」流程
- 在仓库里找到论文《国家战略功能约束下西藏高质量发展的三元协调评价》的材料（`review/`、`workbook/` 等），可作为 PPT 素材
- 用户决定到此为止，没有生成 PPT

**下次继续：** 新会话里先重装技能（见第 1 节），再说「用 ppt-master 根据论文做开题汇报 PPT」。
