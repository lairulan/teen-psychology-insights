# 快速开始指南

## 🎉 恭喜！青少年心理洞察 Skill 已创建成功

你的新 skill 已经可以使用了。以下是快速上手指南。

## ✅ 已完成的配置

- ✅ Skill 核心文件（SKILL.md）
- ✅ 配图生成脚本（generate_image.py）
- ✅ 发布脚本（publish.py）
- ✅ Obsidian 输出目录
- ✅ 完整的 README 文档

## 📋 下一步操作

### 1. 测试 Skill（5分钟）

直接对 Claude 说：
```
青少年心理洞察
```

Claude 会自动：
1. 搜索青少年心理相关热点
2. 分析热度并选择最佳话题
3. 搜集信息和案例
4. 生成 2000-3000 字深度文章
5. 保存到 Obsidian

### 2. 测试配图功能（可选）

运行测试脚本：
```bash
python3 ~/.claude/skills/teen-psychology-insights/scripts/test_image_generation.py
```

这会展示配图生成的逻辑流程。

### 3. 配置图片生成 API（可选但推荐）

如需自动生成配图，编辑 `generate_image.py` 接入你的图片生成服务：

**选项 A - OpenAI DALL-E 3**
```python
import openai

def generate_image_with_dalle(prompt):
    response = openai.Image.create(
        model="dall-e-3",
        prompt=prompt,
        size="1792x1024",
        quality="standard",
        n=1,
    )
    return response.data[0].url
```

**选项 B - Stable Diffusion**
```python
import replicate

def generate_image_with_sd(prompt):
    output = replicate.run(
        "stability-ai/sdxl:...",
        input={"prompt": prompt}
    )
    return output[0]
```

### 4. 配置微信公众号发布（可选）

编辑 `SKILL.md` 的 Step 6 部分，填入你的公众号信息：
```yaml
公众号名称: [你的公众号名称]
AppID: [你的AppID]
```

设置环境变量：
```bash
export WECHAT_API_KEY='your_api_key'
```

### 5. 设置定时任务（可选）

每天晚上 21:00 自动生成文章：

1. 创建 LaunchAgent 配置：
```bash
nano ~/Library/LaunchAgents/com.user.teen-psychology-insights.plist
```

2. 粘贴内容（见 README.md）

3. 加载任务：
```bash
launchctl load ~/Library/LaunchAgents/com.user.teen-psychology-insights.plist
```

## 🎯 使用示例

### 基础用法
```bash
# 默认：基于热搜自动选题
claude "青少年心理洞察"

# 指定主题
claude "青少年心理 主题:考试焦虑"

# 指定字数
claude "写心理文章 字数:2500"
```

### 高级用法
```bash
# 跳过热搜分析，直接写特定主题
claude "青少年心理洞察 主题:校园霸凌 跳过热搜:是"

# 生成并发布
claude "青少年心理 发布:是"
```

## 📁 输出位置

所有生成的文章保存在：
```
~/Documents/Obsidian/青少年心理洞察/
├── [日期] 文章标题.md
└── images/
    ├── [日期]-封面.png
    └── [日期]-正文1.png
```

## 🎨 文章特点

- **面向家长**：实用、温暖、不说教
- **生活化语言**：避免术语，多用故事
- **具体建议**：3-5个可操作的方法
- **案例丰富**：2-3个真实案例
- **对话示范**：具体的话术示例

## 📊 覆盖领域

1. **学业压力**：考试焦虑、学习动力、成绩压力
2. **人际关系**：同伴交往、校园霸凌、社交恐惧
3. **情绪管理**：抑郁情绪、愤怒管理、挫折应对
4. **自我认知**：自我价值、身份认同、青春期困惑
5. **亲子沟通**：代际冲突、沟通技巧、边界设置
6. **行为问题**：网络成瘾、厌学逃学、叛逆行为

## 🔥 热搜驱动选题

Skill 会自动搜索以下平台：
- 知乎热榜（教育/心理话题）⭐⭐⭐⭐⭐
- 微博热搜 ⭐⭐⭐⭐⭐
- 百度热搜 ⭐⭐⭐⭐
- 抖音热搜（教育类）⭐⭐⭐
- 教育类媒体 ⭐⭐⭐⭐

## 💡 提示

1. **首次使用**：建议先不指定主题，让 skill 自动选择热点话题
2. **质量检查**：文章生成后，检查是否包含具体案例和可操作建议
3. **定期更新**：关注热搜变化，保持内容时效性
4. **读者反馈**：根据读者反应调整选题和写作风格

## ❓ 常见问题

**Q: 如何修改执行时间？**
A: 编辑 LaunchAgent plist 文件的 Hour 和 Minute 字段。

**Q: 文章质量如何保证？**
A: Skill 内置质量检查清单，确保包含案例、建议、对话示范等要素。

**Q: 可以自定义内容风格吗？**
A: 可以修改 SKILL.md 中的"写作要求"部分。

**Q: 配图是必需的吗？**
A: 不是必需的。即使不配置图片生成，文章依然会生成，只是没有配图。

## 📚 进阶学习

- 查看 `SKILL.md` 了解完整工作流程
- 查看 `README.md` 了解详细配置
- 运行测试脚本学习配图逻辑

## 🎓 最佳实践

1. **保持定期更新**：建议每天或每周固定时间生成
2. **积累案例库**：记录好的真实案例，持续丰富内容
3. **关注读者互动**：根据评论和反馈调整选题
4. **建立专题系列**：围绕某个主题连续创作多篇

## 🚀 立即开始

现在就试试你的新 skill：
```bash
claude "青少年心理洞察"
```

祝你创作愉快！如有问题，随时查看 README.md 或重新运行此指南。

---

**创建时间**: 2026-02-02
**Skill 版本**: 1.0
**位置**: ~/.claude/skills/teen-psychology-insights/
