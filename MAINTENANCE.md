# 主页维护说明

这份主页面向 `Allencc5658/Allencc5658` 公开仓库，默认分支为 `main`。`README.md` 是 GitHub 个人页中的内容，横幅与项目卡放在 `assets/`，每日生成的图片放在 `profile/`。

## 自动更新

[Update profile images](https://github.com/Allencc5658/Allencc5658/actions/workflows/update-profile.yml) 会一起生成并提交以下六张图：

| 文件 | 内容 |
| --- | --- |
| `profile/stats-light.svg` / `stats-dark.svg` | GitHub 活跃统计，浅色 / 深色 |
| `profile/languages-light.svg` / `languages-dark.svg` | 公开仓库语言分布，浅色 / 深色 |
| `profile/snake-light.svg` / `snake-dark.svg` | 蓝色贡献贪吃蛇，浅色 / 深色 |

- 计划在每天北京时间 08:23 运行；GitHub 调度可能延迟，因此这不是精确到分钟的保证。
- 首次上传工作流以及之后修改 README、本工作流或 `scripts/generate-stats.py` 时，也会自动生成一次。
- 可以随时进入仓库的 **Actions → Update profile images → Run workflow**，选择 `main` 手动刷新。
- README 的 `<picture>` 根据明暗主题选择对应图片；统计卡和贪吃蛇互不冲突。
- 统计脚本 `scripts/generate-stats.py` 只通过无认证的公开 REST API 读取数据，不读取密码、个人令牌或 `GITHUB_TOKEN`。Python 使用标准库，无需安装额外依赖。
- GitHub 自动提供的 `GITHUB_TOKEN` 仅用于仓库检出、贪吃蛇读取贡献日历以及提交图片。工作流只申请 `contents: write`，不需要创建个人访问令牌。

统计脚本只有在所有 API 请求、数据检查和四张图渲染成功后才写入临时目录。API 限流、权限错误、超时、非预期响应都会导致运行失败，不会被转换成零值或错误图片。六张图都生成并通过 SVG 检查后才替换和提交。某一步失败时保留上一版已发布图片；首次运行失败时，随初始提交提供的公开数据快照和贪吃蛇等待画面会保留。没有变化则不创建新提交。自动提交只包含这六张图，不会修改 README、横幅或项目说明。

更新不会递归触发：推送触发器只关注 README、工作流和统计脚本，生成提交仅修改 `profile/`；此外使用 `GITHUB_TOKEN` 的推送本身不会触发新的 `push` 工作流。

## 首版公开快照

首次交付已包含完整的六张图片，README 无需等待 Actions 才能正常显示。四张统计图来自 **2026-09-22 09:38 UTC（北京时间 17:38）** 无凭据读取的公开 GitHub API：3 个公开仓库、这些仓库合计 3 星、2 位关注者。没有在首版图片中填入未经核验的 commit、PR 或贡献总数。图内标有快照日期；这些数字不会在本地图片中自行变化。

语言图按 3 个公开、本人拥有且非 fork 的仓库聚合，共 **589,310 个代码字节**：Python 70.6%、HTML 15.5%、JavaScript 8.1%、CSS 3.4%、Batchfile 1.2%、Shell 1.2%。比值根据未舍入字节数计算，图例显示一位小数。数据来源是[公开仓库列表](https://api.github.com/users/Allencc5658/repos?type=owner&sort=full_name&per_page=100)、[公开用户信息](https://api.github.com/users/Allencc5658)，以及各仓库的 `languages_url` 接口。此次制作保留的原始响应位于本地工作目录的 `work/public-profile-snapshot.json`。

两张初始贪吃蛇图明确显示 **Waiting for first GitHub sync**。它们是等待状态，不是虚构的贡献图；真实贡献动画必须等首次 GitHub Actions 成功运行后生成。首次成功会将六张图一起替换成新生成结果，统计卡沿用相同的公开指标和排版。

日常自动更新中，仓库数和星标涵盖本人拥有的全部公开仓库，包含 fork；语言分布统计本人拥有的全部公开非 fork 仓库，包含归档仓库和本主页仓库。语言不超过 6 种时全部显示，超过 6 种时显示前 5 种和 `Other`，所有比例仍以完整代码字节数为分母。没有语言数据时明确显示空状态。

脚本处理仓库分页，最多读取 5 页、每页 100 个仓库。为控制无认证 API 的请求量，语言请求最多覆盖 45 个公开非 fork 仓库；超出这些上限会明确失败，需调整方案，不会悄悄截断数据。目前账号规模远低于上限。

## 日常修改

1. **修改介绍**：编辑 `README.md` 的自我介绍与研究兴趣。只写已经确认的项目、工作和成果。
2. **新增具身项目**：更新项目卡的标题、简介、链接与图片；优先加入能展示实际效果的短演示，再根据需要调整仓库置顶。
3. **调整天蓝色**：横幅及项目卡的颜色在各自 SVG 内；统计图主题在 `scripts/generate-stats.py` 的 `THEMES` 中、语言条颜色在 `COLORS` 中；贪吃蛇颜色在工作流的 `outputs` 中。这些十六进制颜色都带 `#`。
4. **更新统计范围**：语言图来自公开仓库的代码字节分布，不表示研究能力、使用时间或技术熟练程度。当前未配置私有仓库统计，不应为了装饰主页而扩大访问范围。

浅色以 `#0284c7` 为强调色、`#334155` 为正文、白色为底；深色以 `#7dd3fc` 为标题、`#cbd5e1` 为正文、`#0d1117` 为底。贪吃蛇保留五档贡献颜色，颜色越深或越亮代表贡献量越高。

## 显示或更新异常

| 情况 | 检查方法 |
| --- | --- |
| 仍显示 Waiting for first GitHub sync | 在 Actions 查看首次运行是否完成，必要时手动运行一次；当前画面不表示没有贡献。 |
| 新数据还没出现 | 先看工作流最后一次成功时间；GitHub 图片缓存和贡献数据本身也可能延迟。 |
| 工作流显示红色 | 打开失败步骤查看日志，API 限流或临时网络错误可稍后重跑；已发布图片会保留。 |
| `git push` 权限错误 | 确认仓库允许 GitHub Actions 运行且组织/仓库策略允许工作流写入。分支保护要求 PR 时不能直接推送，需要相应调整发布流程。 |
| 长时间没有自动运行 | 检查 Actions 是否被禁用。公开仓库长期无活动时，GitHub 可能停用定时工作流，可在 Actions 页面重新启用。 |
| 深色模式不切换 | 检查 README `<picture>` 的 `source` 和 `img` 路径，确认两版文件均存在。 |

不要直接改 `profile/` 里的图来调整配色，下次自动运行会覆盖这些改动。应该修改统计脚本主题或贪吃蛇工作流参数。图片更新提交保留在 Git 历史里，需要回退时可以恢复之前的图片与参数。

## 依赖和版本

本版将使用的 Actions 固定到完整提交 SHA，统计渲染脚本直接维护在本仓库中。

| 组件 | 版本 / 固定值 |
| --- | --- |
| [actions/checkout](https://github.com/actions/checkout/releases/tag/v6.0.2) | `v6.0.2` / `de0fac2e4500dabe0009e67214ff5f5447ce83dd` |
| 统计渲染器 | 本仓库 `scripts/generate-stats.py`，Python 3 标准库 |
| [Platane/snk SVG Action](https://github.com/Platane/snk/tree/d8f6715049803e982ee5ff501b6b9b7d5deeb09b/svg-only) | `v3.5.0` / `d8f6715049803e982ee5ff501b6b9b7d5deeb09b` |

升级 Actions 时先核对上游发布说明，更新 SHA 后手动运行，并检查明暗两版图片。统计卡不使用远程渲染服务或第三方 Python 包。

参考：[GitHub 公开 REST API](https://docs.github.com/en/rest)、[贪吃蛇用法及配色](https://github.com/Platane/snk#usage)、[GitHub 工作流触发规则](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)、[GitHub 定时事件说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)。
