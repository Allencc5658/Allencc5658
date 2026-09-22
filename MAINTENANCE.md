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
- 首次上传工作流以及之后修改 README 或本工作流时，也会自动生成一次。
- 可以随时进入仓库的 **Actions → Update profile images → Run workflow**，选择 `main` 手动刷新。
- README 的 `<picture>` 根据明暗主题选择对应图片；统计卡和贪吃蛇互不冲突。
- 公开统计使用 GitHub 自动提供的 `GITHUB_TOKEN`，不需要填写密码或创建个人访问令牌。工作流只申请 `contents: write`，用于提交图片。

四次统计生成均启用 `fail_on_error`。所有图片先写入临时目录，六张图都生成并通过 SVG 检查后才替换和提交。某一步失败时保留上一版已发布图片；首次运行失败时，随初始提交提供的公开数据快照和贪吃蛇等待画面会保留。没有变化则不创建新提交。自动提交只包含这六张图，不会修改 README、横幅或项目说明。

更新不会递归触发：推送触发器只关注 README 和工作流，生成提交仅修改 `profile/`；此外使用 `GITHUB_TOKEN` 的推送本身不会触发新的 `push` 工作流。

## 首版公开快照

首次交付已包含完整的六张图片，README 无需等待 Actions 才能正常显示。四张统计图来自 **2026-09-22 09:38 UTC（北京时间 17:38）** 无凭据读取的公开 GitHub API：3 个公开仓库、这些仓库合计 3 星、2 位关注者。没有在首版图片中填入未经核验的 commit、PR 或贡献总数。图内标有快照日期；这些数字不会在本地图片中自行变化。

语言图按 3 个公开、本人拥有且非 fork 的仓库聚合，共 **589,310 个代码字节**：Python 70.6%、HTML 15.5%、JavaScript 8.1%、CSS 3.4%、Batchfile 1.2%、Shell 1.2%。比值根据未舍入字节数计算，图例显示一位小数。数据来源是[公开仓库列表](https://api.github.com/users/Allencc5658/repos?type=owner&sort=full_name&per_page=100)、[公开用户信息](https://api.github.com/users/Allencc5658)，以及各仓库的 `languages_url` 接口。此次制作保留的原始响应位于本地工作目录的 `work/public-profile-snapshot.json`。

两张贪吃蛇图明确显示 **Waiting for first GitHub sync**。它们是等待状态，不是虚构的贡献图；真实贡献动画必须等首次 GitHub Actions 成功运行后生成。首次成功会将六张图一起替换成上游组件的真实生成结果，统计卡也会从首次公开快照切换为该组件提供的统计项目。

## 日常修改

1. **修改介绍**：编辑 `README.md` 的自我介绍与研究兴趣。只写已经确认的项目、工作和成果。
2. **新增具身项目**：更新项目卡的标题、简介、链接与图片；优先加入能展示实际效果的短演示，再根据需要调整仓库置顶。
3. **调整天蓝色**：横幅及项目卡的颜色在各自 SVG 内；统计图颜色在工作流的 `options` 中；贪吃蛇颜色在 `outputs` 中。统计参数的十六进制颜色不带 `#`，贪吃蛇颜色带 `#`。
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

不要直接改 `profile/` 里的图来调整配色，下次自动运行会覆盖这些改动。应该修改工作流参数。图片更新提交保留在 Git 历史里，需要回退时可以恢复之前的图片与参数。

## 依赖和版本

本版将直接使用的 Actions 固定到完整提交 SHA，并固定统计渲染器版本，避免浮动标签悄悄改变效果。

| 组件 | 版本 / 固定值 |
| --- | --- |
| [actions/checkout](https://github.com/actions/checkout/releases/tag/v6.0.2) | `v6.0.2` / `de0fac2e4500dabe0009e67214ff5f5447ce83dd` |
| [GitHub Readme Stats Action](https://github.com/stats-organization/github-readme-stats-action/tree/e856fc8de9d7729b463c468911e232cfbdc3d55e) | `v2.0.2` / `e856fc8de9d7729b463c468911e232cfbdc3d55e` |
| 统计渲染器 | `@stats-organization/github-readme-stats-core@2.1.3` |
| [Platane/snk SVG Action](https://github.com/Platane/snk/tree/d8f6715049803e982ee5ff501b6b9b7d5deeb09b/svg-only) | `v3.5.0` / `d8f6715049803e982ee5ff501b6b9b7d5deeb09b` |

升级依赖时先核对上游发布说明，更新 SHA 后手动运行，并检查明暗两版图片。统计 Action 在运行时通过包管理器安装渲染器和依赖，固定直接版本并不等于所有间接依赖均锁定。

参考：[统计 Action 输入说明](https://github.com/stats-organization/github-readme-stats-action#inputs)、[贪吃蛇用法及配色](https://github.com/Platane/snk#usage)、[GitHub 工作流触发规则](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)、[GitHub 定时事件说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)。
