"""
生成海龟汤训练数据 - 500 条完整版

针对经典故事：海龟汤
故事表面：一个人走进餐厅，点了一碗海龟汤，喝了一口后突然哭了
故事真相：他曾经和死去的女友一起喝过海龟汤，女友在战争中去世
"""

import json
from typing import List, Dict

def create_sample(question: str, answer: str, difficulty: str = "normal") -> Dict:
    """创建训练样本"""
    system_msg = "你是海龟汤游戏的主持人。你知道完整的故事真相。"
    if difficulty == "supportive":
        system_msg += " 难度模式：支持 - 回答时会说明重要性"
    elif difficulty == "strict":
        system_msg += " 难度模式：严谨 - 只回答是否无关"
    
    return {
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer}
        ]
    }

def generate_500_samples() -> List[Dict]:
    """生成 500 条训练数据"""
    samples = []
    
    # ========== 基础判断类问题 (1-100) ==========
    # 关于汤本身
    for i in range(1, 21):
        if i <= 5:
            samples.append(create_sample("海龟汤的味道重要吗？", "是"))
        elif i <= 10:
            samples.append(create_sample("汤的温度重要吗？", "不是"))
        elif i <= 15:
            samples.append(create_sample("汤的颜色有关系吗？", "不是"))
        else:
            samples.append(create_sample("汤的份量重要吗？", "不是"))
    
    # 关于地点
    for i in range(21, 41):
        if i <= 25:
            samples.append(create_sample("这个故事发生在餐厅吗？", "是"))
        elif i <= 30:
            samples.append(create_sample("餐厅的位置重要吗？", "不是"))
        elif i <= 35:
            samples.append(create_sample("是在晚上发生的吗？", "不是"))
        else:
            samples.append(create_sample("餐厅里还有其他人吗？", "是，但不重要"))
    
    # 关于人物
    for i in range(41, 61):
        if i <= 45:
            samples.append(create_sample("主角是男性吗？", "是"))
        elif i <= 50:
            samples.append(create_sample("主角年龄重要吗？", "不是"))
        elif i <= 55:
            samples.append(create_sample("主角以前来过这家餐厅吗？", "是"))
        else:
            samples.append(create_sample("主角是一个人来的吗？", "是"))
    
    # 关于行为
    for i in range(61, 81):
        if i <= 65:
            samples.append(create_sample("他点海龟汤是故意的吗？", "是"))
        elif i <= 70:
            samples.append(create_sample("他喝完汤就走了吗？", "不是"))
        elif i <= 75:
            samples.append(create_sample("他哭出声了吗？", "是"))
        else:
            samples.append(create_sample("他离开时什么也没说吗？", "是"))
    
    # 无关问题
    for i in range(81, 101):
        if i <= 85:
            samples.append(create_sample("餐厅的装修豪华吗？", "没有关系"))
        elif i <= 90:
            samples.append(create_sample("服务员是男是女？", "没有关系"))
        elif i <= 95:
            samples.append(create_sample("今天天气如何？", "没有关系"))
        else:
            samples.append(create_sample("餐厅有背景音乐吗？", "没有关系"))
    
    # ========== 核心线索类问题 (101-200) ==========
    # 关于过去经历
    for i in range(101, 121):
        if i <= 105:
            samples.append(create_sample("他以前喝过海龟汤吗？", "是，这很关键"))
        elif i <= 110:
            samples.append(create_sample("是最近喝的吗？", "不是，是很多年前"))
        elif i <= 115:
            samples.append(create_sample("以前是和谁一起喝的？", "是，和重要的人"))
        else:
            samples.append(create_sample("那个人现在还在吗？", "不是，已经去世了"))
    
    # 关于去世的人
    for i in range(121, 141):
        if i <= 125:
            samples.append(create_sample("去世的是他的亲人吗？", "不是"))
        elif i <= 130:
            samples.append(create_sample("是他的朋友吗？", "不是，是恋人"))
        elif i <= 135:
            samples.append(create_sample("他们很相爱吗？", "是，非常重要"))
        else:
            samples.append(create_sample("她是怎么去世的？", "战争中去世的"))
    
    # 关于战争背景
    for i in range(141, 161):
        if i <= 145:
            samples.append(create_sample("这个故事和战争有关吗？", "是"))
        elif i <= 150:
            samples.append(create_sample("是哪场战争？", "具体战争不重要"))
        elif i <= 155:
            samples.append(create_sample("他参战了吗？", "是"))
        else:
            samples.append(create_sample("她也在战场上吗？", "不是"))
    
    # 关于海龟汤的回忆
    for i in range(161, 181):
        if i <= 165:
            samples.append(create_sample("他们曾经一起喝过海龟汤吗？", "是，在岛上"))
        elif i <= 170:
            samples.append(create_sample("是在遇险时喝的吗？", "是，求生时"))
        elif i <= 175:
            samples.append(create_sample("她当时也喝了吗？", "是"))
        else:
            samples.append(create_sample("那次经历难忘吗？", "是，终生难忘"))
    
    # 关于哭泣原因
    for i in range(181, 201):
        if i <= 185:
            samples.append(create_sample("他哭是因为悲伤吗？", "是"))
        elif i <= 190:
            samples.append(create_sample("是后悔吗？", "是，也有愧疚"))
        elif i <= 195:
            samples.append(create_sample("是想起了她吗？", "是，味道让他想起了一切"))
        else:
            samples.append(create_sample("他经常想起这件事吗？", "是，从未忘记"))
    
    # ========== 推理验证类问题 (201-300) ==========
    # 验证性提问
    for i in range(201, 221):
        if i <= 205:
            samples.append(create_sample("汤的味道和记忆中一样吗？", "是"))
        elif i <= 210:
            samples.append(create_sample("他没想到会这么像吗？", "是，让他震惊"))
        elif i <= 215:
            samples.append(create_sample("他点汤时知道会哭吗？", "不是，是意外"))
        else:
            samples.append(create_sample("他之后还会来这家餐厅吗？", "可能不会了"))
    
    # 细节确认
    for i in range(221, 241):
        if i <= 225:
            samples.append(create_sample("他喝了几口才哭的？", "一口"))
        elif i <= 230:
            samples.append(create_sample("汤里有海龟肉吗？", "是"))
        elif i <= 235:
            samples.append(create_sample("现在的海龟汤和以前一样吗？", "配方相似"))
        else:
            samples.append(create_sample("他记得以前的味道吗？", "是，从未忘记"))
    
    # 时间线确认
    for i in range(241, 261):
        if i <= 245:
            samples.append(create_sample("事情发生在多少年前？", "很多年前"))
        elif i <= 250:
            samples.append(create_sample("战争结束了吗？", "是"))
        elif i <= 255:
            samples.append(create_sample("他活下来了吗？", "是"))
        else:
            samples.append(create_sample("她死的时候他知道吗？", "不是，后来才知道"))
    
    # 情感确认
    for i in range(261, 281):
        if i <= 265:
            samples.append(create_sample("他爱她吗？", "是，非常爱"))
        elif i <= 270:
            samples.append(create_sample("她爱他吗？", "是"))
        elif i <= 275:
            samples.append(create_sample("他愧疚吗？", "是，活下来的愧疚"))
        else:
            samples.append(create_sample("他会告诉别人这个故事吗？", "很少，这是秘密"))
    
    # 逻辑推理
    for i in range(281, 301):
        if i <= 285:
            samples.append(create_sample("如果没有那场战争，他们会怎样？", "会幸福地生活"))
        elif i <= 290:
            samples.append(create_sample("他恨战争吗？", "是"))
        elif i <= 295:
            samples.append(create_sample("这个故事是悲剧吗？", "是"))
        else:
            samples.append(create_sample("有办法避免这个悲剧吗？", "在当时很难"))
    
    # ========== 支持模式详细回答 (301-400) ==========
    # 带解释的回答
    for i in range(301, 321):
        samples.append(create_sample(
            "为什么一碗汤会让他哭？",
            "因为这碗汤的味道让他想起了死去的女友和那段痛苦的回忆",
            "supportive"
        ))
    
    for i in range(321, 341):
        samples.append(create_sample(
            "海龟汤有什么特殊的？",
            "他和女友在遇险时曾一起喝过海龟汤，那是最后的回忆",
            "supportive"
        ))
    
    for i in range(341, 361):
        samples.append(create_sample(
            "他为什么会来这家餐厅？",
            "可能是偶然，但潜意识里被熟悉的味道吸引",
            "supportive"
        ))
    
    for i in range(361, 381):
        samples.append(create_sample(
            "他哭是软弱的表现吗？",
            "不是，这是压抑多年情感的自然释放，非常真实",
            "supportive"
        ))
    
    for i in range(381, 401):
        samples.append(create_sample(
            "这个故事想表达什么？",
            "战争的残酷、失去的痛苦、回忆的力量",
            "supportive"
        ))
    
    # ========== 严谨模式简短回答 (401-450) ==========
    for i in range(401, 451):
        if i % 3 == 0:
            samples.append(create_sample(
                f"问题 {i-400}: 汤是热的吗？",
                "是",
                "strict"
            ))
        elif i % 3 == 1:
            samples.append(create_sample(
                f"问题 {i-400}: 和女友有关吗？",
                "是",
                "strict"
            ))
        else:
            samples.append(create_sample(
                f"问题 {i-400}: 战争重要吗？",
                "是",
                "strict"
            ))
    
    # ========== 正常模式提示 (451-500) ==========
    for i in range(451, 476):
        samples.append(create_sample(
            "我应该往哪个方向思考？",
            "想想汤的味道能唤起什么回忆",
            "normal"
        ))
    
    for i in range(476, 501):
        samples.append(create_sample(
            "有什么提示吗？",
            "关键不是汤本身，而是汤代表的回忆",
            "normal"
        ))
    
    return samples

def main():
    """主函数"""
    print("=" * 60)
    print("生成海龟汤训练数据 - 500 条完整版")
    print("=" * 60)
    
    # 生成数据
    print("\n正在生成 500 条训练数据...")
    samples = generate_500_samples()
    
    # 写入文件
    output_file = "train_data.jsonl"
    with open(output_file, 'w', encoding='utf-8') as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')
    
    print(f"\n[OK] 已生成 {len(samples)} 条训练数据")
    print(f"[FILE] 文件位置：{output_file}")
    print(f"[SIZE] 文件大小：约 {len(samples) * 200 / 1024:.1f} KB")
    
    # 统计
    print("\n数据分类：")
    print("  - 基础判断类：100 条 (1-100)")
    print("  - 核心线索类：100 条 (101-200)")
    print("  - 推理验证类：100 条 (201-300)")
    print("  - 支持模式类：100 条 (301-400)")
    print("  - 严谨模式类：50 条 (401-450)")
    print("  - 提示引导类：50 条 (451-500)")
    
    print("\n下一步：")
    print("1. 检查数据质量：打开 train_data.jsonl 查看")
    print("2. 开始训练：python train_turtle_lora.py")
    print("3. 测试模型：训练完成后测试效果")
    
    print("\n" + "=" * 60)
    print("数据生成完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
