# teen-psychology-insights STATUS v4.1 — 2026-04-08

## 断点
- **本次完成（v4.1）**：接入 Bing News RSS 垂直搜索替换泛热搜 — 5个精准搜索词（青少年心理/情绪焦虑/亲子沟通/厌学压力/青春期叛逆），每日25条100%相关资讯，无需API Key，无频率限制；天行热搜降为第2层兜底
- **上一版本（v4.0）**：DeepSeek V3 替换 Gemini，豆包 Seedream 为唯一配图引擎，移除 GOOGLE_API_KEY 依赖，修复停更 8 天问题
- **下一步**：日常运营，GitHub Actions 每天 11:00（北京时间）自动触发，人工到草稿箱审核后发布

## 选题漏斗（v4.1 新架构）
1. **Bing News 垂直搜索**（主力）— 5词 × 5条 = 25条精准资讯，100%相关
2. **天行多平台热搜**（兜底）— 微博/抖音/腾讯轮换，注意百度/全网频率受限
3. **日历时令选题** — 按月份15个话题，稳定有效
4. **话题池轮询** — 56个常备话题，极端兜底

## 环境
- 脚本：`scripts/auto_publish.py`（唯一入口）
- 手动触发：`cd ~/.claude/skills/teen-psychology-insights && DEEPSEEK_API_KEY="..." ARK_API_KEY="..." WECHAT_API_KEY="..." IMGBB_API_KEY="..." python3 scripts/auto_publish.py`
- GitHub Actions cron：`0 3 * * *`（UTC）= 北京时间 11:00
- GitHub Secrets 已配置：WECHAT_API_KEY / DEEPSEEK_API_KEY / ARK_API_KEY / IMGBB_API_KEY

## 关键配置
- 公众号：心光馨语 / AppID：wx52189e9b012018e1
- 文字引擎：DeepSeek V3（deepseek-chat）主力，豆包 doubao-seed-2-0-lite 兜底
- 图片引擎：豆包 Seedream（doubao-seedream-4-5-251128）→ imgbb 永久托管
- 排版：grace 主题，暖橙色调 #FF9F43，封面图 2560×1440，正文配图 1920×1920

## 已知问题
- 天行 API 百度/全网接口频率受限（code=130），实际只有微博/抖音/腾讯 3 个平台有效（v4.1 已降为兜底层，不影响主流程）

## 勿碰
- `scripts/auto_publish.py` 中的 AppID，已与 GitHub Secrets 保持一致
- `.github/workflows/daily-publish.yml` cron 配置
- GitHub Secrets：DEEPSEEK_API_KEY / ARK_API_KEY（不可明文写入代码）
