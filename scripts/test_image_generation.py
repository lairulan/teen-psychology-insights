#!/usr/bin/env python3
"""
快速测试脚本 - 验证配图生成功能
"""

import os
import sys

# 添加脚本目录到路径
script_dir = os.path.expanduser("~/.claude/skills/teen-psychology-insights/scripts")
sys.path.insert(0, script_dir)

from generate_image import generate_cover_image, extract_image_placeholders

def test_cover_generation():
    """测试封面图生成"""
    print("=" * 60)
    print("测试 1: 封面图生成")
    print("=" * 60)

    generate_cover_image(
        title="考前焦虑：读懂孩子心中的那座山",
        style="warm",
        size="1792x1024"
    )

    print("\n✅ 封面图生成测试完成\n")


def test_placeholder_extraction():
    """测试占位符提取"""
    print("=" * 60)
    print("测试 2: 占位符提取")
    print("=" * 60)

    # 创建测试Markdown文件
    test_content = """---
title: 测试文章
---

# 测试文章

## 第一章节

这是第一段文字。

<!-- IMG_PLACEHOLDER: {主体: "一个独自坐在教室角落的中学生", 动作/状态: "低头看书，眼神躲闪", 场景/环境: "��室里其他同学在热闹交谈，光线柔和", 风格: "温暖治愈系插画，柔和色调"} -->

这是第二段文字。

## 第二章节

这是第三段文字。

<!-- IMG_PLACEHOLDER: {主体: "母子对话场景", 动作/状态: "母亲蹲下与孩子平视交流", 场景/环境: "温馨的家庭客厅", 风格: "温暖治愈系插画"} -->

这是第四段文字。
"""

    test_file = "/tmp/test_article.md"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)

    print(f"创建测试文件: {test_file}")

    placeholders = extract_image_placeholders(test_file)

    print(f"\n找到 {len(placeholders)} 个占位符:\n")

    for i, p in enumerate(placeholders, 1):
        print(f"占位符 {i}:")
        for key, value in p['info'].items():
            print(f"  {key}: {value}")
        print()

    print("✅ 占位符提取测试完成\n")


def test_full_workflow():
    """测试完整工作流"""
    print("=" * 60)
    print("测试 3: 完整工作流")
    print("=" * 60)

    # 创建完整测试文章
    test_content = """---
title: 考前焦虑：读懂孩子心中的那座山
date: 2026-02-02
category: 热点解读
tags: [青少年心理, 考试焦虑, 学业压力]
word_count: 2600
heat_index: 🔥🔥🔥🔥🔥
target_audience: 家长
age_range: 10-18岁
---

# 考前焦虑：读懂孩子心中的那座山

## 引子：真实场景描述

晚上十点，小雨妈妈推开女儿的房门...

## 这背后的心理真相

考前焦虑不是"不够努力"的表现...

<!-- IMG_PLACEHOLDER: {主体: "一个中学生坐在书桌前", 动作/状态: "双手抱头，周围堆满复习资料", 场景/环境: "深夜的书房，台灯昏黄", 风格: "温暖治愈系插画，表达压力感"} -->

## 真实案例：小雨的故事

小雨是一个成绩优秀的初三学生...

<!-- IMG_PLACEHOLDER: {主体: "母女对话场景", 动作/状态: "母亲温柔地搂着女儿的肩膀", 场景/环境: "温馨的客厅沙发", 风格: "温暖治愈系插画，表达理解和支持"} -->

## 家长可以这样做

### 理解孩子的内心世界

从孩子的视角看问题...

### 具体应对策略

1. 建立科学的复习计划...
2. 进行渐进式放松训练...
3. 营造支持性的家庭氛围...

<!-- IMG_PLACEHOLDER: {主体: "一家人围坐在餐桌前", 动作/状态: "轻松愉快地交谈", 场景/环境: "温馨的家庭餐厅", 风格: "温暖治愈系插画，表达家庭支持"} -->

## 写在最后

每个孩子都是独一无二的...
"""

    test_file = "/tmp/full_test_article.md"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)

    print(f"创建完整测试文章: {test_file}\n")

    # 测试封面图
    print("生成封面图:")
    generate_cover_image(
        title="考前焦虑：读懂孩子心中的那座山",
        style="warm"
    )

    print("\n" + "-" * 60 + "\n")

    # 测试正文配图
    print("提取并生成正文配图:")
    from generate_image import generate_article_images
    generate_article_images(test_file, max_images=3)

    print("\n✅ 完整工作流测试完成\n")


def main():
    print("\n" + "=" * 60)
    print("青少年心理洞察 Skill - 配图功能测试")
    print("=" * 60 + "\n")

    try:
        test_cover_generation()
        test_placeholder_extraction()
        test_full_workflow()

        print("=" * 60)
        print("🎉 所有测试完成！")
        print("=" * 60)
        print("\n📝 注意事项:")
        print("1. 这些脚本提供了配图生成的框架和逻辑")
        print("2. 实际图片生成需要接入图片生成API")
        print("3. 建议使用: OpenAI DALL-E 3, Midjourney, 或 Stable Diffusion")
        print("4. 配置好API后，替换脚本中的图片生成部分即可\n")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
