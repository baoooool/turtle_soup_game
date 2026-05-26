"""
查看和管理游戏记录
"""

import json
from pathlib import Path
from app.game.recorder import GameRecorder


def list_records():
    """列出所有游戏记录"""
    recorder = GameRecorder()
    records = recorder.list_records()
    
    print("=" * 60)
    print(f"游戏记录 (共 {len(records)} 场)")
    print("=" * 60)
    
    for i, filename in enumerate(records, 1):
        record = recorder.get_record(filename)
        if record:
            winner = "玩家" if record.player_won else ("BOB" if record.bob_won else "未结束")
            print(f"{i}. {filename}")
            print(f"   故事：{record.story_title}")
            print(f"   玩家：{record.player_name}")
            print(f"   难度：{record.host_difficulty}")
            print(f"   轮数：{record.total_turns}")
            print(f"   得分：{record.final_score}")
            print(f"   获胜：{winner}")
            print()


def view_record(filename: str):
    """查看指定游戏记录"""
    recorder = GameRecorder()
    record = recorder.get_record(filename)
    
    if not record:
        print(f"记录不存在：{filename}")
        return
    
    print("=" * 60)
    print(f"游戏记录：{filename}")
    print("=" * 60)
    
    print(f"\n故事：{record.story_title}")
    print(f"汤面：{record.story_surface[:100]}...")
    print(f"汤底：{record.story_bottom[:100]}...")
    print(f"玩家：{record.player_name}")
    print(f"难度：{record.host_difficulty}")
    print(f"总轮数：{record.total_turns}")
    print(f"最终得分：{record.final_score}")
    print(f"获胜：{'玩家' if record.player_won else ('BOB' if record.bob_won else '未结束')}")
    
    print("\n" + "=" * 60)
    print("问答记录")
    print("=" * 60)
    
    for qa in record.qa_records:
        player = "玩家" if qa.player_type == "player" else "BOB"
        print(f"\n第{qa.turn_number}轮 [{player}]")
        print(f"问：{qa.question}")
        print(f"答：{qa.answer}")


def export_training_data():
    """导出训练数据"""
    recorder = GameRecorder()
    count = recorder.get_training_data_count()
    
    if count == 0:
        print("暂无训练数据")
        return
    
    output_file = "train_data.jsonl"
    recorder.export_training_data(output_file)
    
    print("=" * 60)
    print("训练数据导出成功")
    print("=" * 60)
    print(f"文件：{output_file}")
    print(f"数据量：{count} 条")
    print(f"\n下一步：")
    print(f"1. 检查数据质量：打开 {output_file}")
    print(f"2. 补充数据到 500+ 条")
    print(f"3. 运行训练：python train_turtle_lora.py")


def statistics():
    """显示统计信息"""
    recorder = GameRecorder()
    records = recorder.list_records()
    
    if not records:
        print("暂无游戏记录")
        return
    
    total_games = len(records)
    player_wins = 0
    bob_wins = 0
    total_turns = 0
    total_score = 0
    
    for filename in records:
        record = recorder.get_record(filename)
        if record:
            if record.player_won:
                player_wins += 1
            elif record.bob_won:
                bob_wins += 1
            total_turns += record.total_turns
            total_score += record.final_score
    
    print("=" * 60)
    print("游戏统计")
    print("=" * 60)
    print(f"总游戏数：{total_games}")
    print(f"玩家获胜：{player_wins} ({player_wins/total_games*100:.1f}%)")
    print(f"BOB 获胜：{bob_wins} ({bob_wins/total_games*100:.1f}%)")
    print(f"平均轮数：{total_turns/total_games:.1f}")
    print(f"平均得分：{total_score/total_games:.1f}")
    print(f"训练数据：{recorder.get_training_data_count()} 条")


def main():
    print("海龟汤游戏记录管理器")
    print("=" * 60)
    print("1. 查看所有记录")
    print("2. 查看指定记录")
    print("3. 导出训练数据")
    print("4. 显示统计信息")
    print("5. 退出")
    print("=" * 60)
    
    while True:
        choice = input("\n请选择 (1-5): ").strip()
        
        if choice == '1':
            list_records()
        elif choice == '2':
            filename = input("输入文件名: ").strip()
            view_record(filename)
        elif choice == '3':
            export_training_data()
        elif choice == '4':
            statistics()
        elif choice == '5':
            print("再见！")
            break
        else:
            print("无效选择")


if __name__ == "__main__":
    main()
