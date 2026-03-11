# teen-psychology-insights 开发断点
> 更新：2026-03-12

## 当前版本：v3.0 🟢 投产运营

## 完成状态
- [x] v1.0 初始版本
- [x] v2.0 全面升级：公众号改"心光馨语"，闺蜜聊天式，grace排版+暖橙色调
- [x] v2.1 API升级：Gemini 2.5 Flash + 豆包兜底，修复 GOOGLE_API_KEY 配置
- [x] v2.2 排版优化：H2颜色统一(#FF8C42)，列表flex布局，图片占位块
- [x] v2.3 选题增强：5平台热搜轮换 + Gemini实时搜索兜底，清理冗余脚本
- [x] v3.0 首次投产：修复发布bug，更新凭证，GitHub Actions 北京11:00定时运营

## 下一步：日常运营
- GitHub Actions 每天 11:00 自动触发，文章进草稿箱，人工审核后发布
- 如需手动触发：`WECHAT_API_KEY=xxx python3 scripts/auto_publish.py`

## 技术架构
- **选题**：4层漏斗 → 微博/腾讯热搜 → Gemini实时搜索 → 日历时令 → 话题池
- **内容生成**：Gemini 2.5 Flash（豆包 1.5 Pro 兜底）
- **配图**：暂无（Imagen API 模型名称需更新，不影响发布）
- **排版**：暖橙色调 #FF9F43，内联 HTML
- **发布**：wx.limyai.com API → 公众号「心光馨语」草稿箱

## 关键配置
- AppID：`wx5f15d70a0882dc9b`
- WECHAT_API_KEY：`xhs_f8b7a51a40b4df34429014e228018417`
- GitHub Secrets：WECHAT_API_KEY / GOOGLE_API_KEY 已配置
- cron：`0 3 * * *`（UTC）= 北京时间 11:00

## 关键文件
- `SKILL.md` — 主 Skill 文件（v3.0）
- `scripts/auto_publish.py` — 唯一脚本（整合全流程）
- `.github/workflows/daily-publish.yml` — 定时任务
- `logs/` — 运营日志
