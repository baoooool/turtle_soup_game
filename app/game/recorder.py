"""
海龟汤游戏记录器
记录每次游戏的完整流程，并自动生成训练数据
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class QARecord:
    """单条问答记录"""
    question: str
    answer: str
    turn_number: int
    player_type: str  # "player" or "bob"


@dataclass
class GameRecord:
    """完整游戏记录"""
    timestamp: str
    story_title: str
    story_surface: str
    story_bottom: str
    player_name: str
    host_difficulty: str
    qa_records: list[QARecord]
    total_turns: int
    bob_won: bool
    player_won: bool
    final_score: int


class GameRecorder:
    """游戏记录器"""
    
    def __init__(self, records_dir: str = "game_records"):
        self.records_dir = Path(records_dir)
        self.records_dir.mkdir(exist_ok=True)
        
        self.current_game: Optional[GameRecord] = None
        self.current_qa_list: list[QARecord] = []
        
        # 训练数据文件
        self.training_data_file = self.records_dir / "training_data.jsonl"
    
    def start_game(
        self,
        story_title: str,
        story_surface: str,
        story_bottom: str,
        player_name: str,
        host_difficulty: str = "normal"
    ) -> None:
        """开始新游戏"""
        self.current_qa_list = []
        self.current_game = GameRecord(
            timestamp=datetime.now().isoformat(),
            story_title=story_title,
            story_surface=story_surface,
            story_bottom=story_bottom,
            player_name=player_name,
            host_difficulty=host_difficulty,
            qa_records=[],
            total_turns=0,
            bob_won=False,
            player_won=False,
            final_score=0
        )
    
    def record_question(
        self,
        question: str,
        answer: str,
        turn_number: int,
        player_type: str = "player"
    ) -> None:
        """记录一次问答"""
        if self.current_game is None:
            return
        
        qa = QARecord(
            question=question,
            answer=answer,
            turn_number=turn_number,
            player_type=player_type
        )
        self.current_qa_list.append(qa)
    
    def end_game(
        self,
        bob_won: bool = False,
        player_won: bool = False,
        final_score: int = 0
    ) -> str:
        """结束游戏并保存记录"""
        if self.current_game is None:
            return ""
        
        # 更新游戏记录
        self.current_game.qa_records = self.current_qa_list
        self.current_game.total_turns = len(self.current_qa_list)
        self.current_game.bob_won = bob_won
        self.current_game.player_won = player_won
        self.current_game.final_score = final_score
        
        # 生成文件名（按时间命名）
        timestamp = datetime.fromisoformat(self.current_game.timestamp)
        filename = f"game_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.records_dir / filename
        
        # 保存游戏记录
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.current_game), f, ensure_ascii=False, indent=2)
        
        # 追加到训练数据
        self._append_to_training_data()
        
        # 重置当前游戏
        game_info = f"{self.current_game.story_title} - {self.current_game.player_name}"
        self.current_game = None
        self.current_qa_list = []
        
        return str(filepath)
    
    def _append_to_training_data(self) -> None:
        """将当前游戏转换为训练数据并追加"""
        if self.current_game is None:
            return
        
        training_samples = []
        
        # 为每个问答生成训练样本
        for qa in self.current_qa_list:
            # 基础问答样本
            sample = {
                "messages": [
                    {
                        "role": "system",
                        "content": f"你是海龟汤游戏的主持人。难度模式：{self.current_game.host_difficulty}"
                    },
                    {
                        "role": "user",
                        "content": qa.question
                    },
                    {
                        "role": "assistant",
                        "content": qa.answer
                    }
                ]
            }
            training_samples.append(sample)
        
        # 追加到训练数据文件
        with open(self.training_data_file, 'a', encoding='utf-8') as f:
            for sample in training_samples:
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')
    
    def get_training_data_count(self) -> int:
        """获取训练数据总数"""
        if not self.training_data_file.exists():
            return 0
        
        count = 0
        with open(self.training_data_file, 'r', encoding='utf-8') as f:
            for _ in f:
                count += 1
        return count
    
    def export_training_data(self, output_file: str = "train_data.jsonl") -> None:
        """导出训练数据到指定文件"""
        if not self.training_data_file.exists():
            print("暂无训练数据")
            return
        
        # 复制文件
        import shutil
        shutil.copy(self.training_data_file, output_file)
        print(f"已导出 {self.get_training_data_count()} 条训练数据到 {output_file}")
    
    def list_records(self) -> list[str]:
        """列出所有游戏记录"""
        if not self.records_dir.exists():
            return []
        
        files = sorted([
            f.name for f in self.records_dir.iterdir()
            if f.suffix == '.json' and f.name != 'training_data.jsonl'
        ])
        return files
    
    def get_record(self, filename: str) -> Optional[GameRecord]:
        """读取指定游戏记录"""
        filepath = self.records_dir / filename
        if not filepath.exists():
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return GameRecord(**data)


# 全局记录器实例
recorder = GameRecorder()


# 装饰器：自动记录游戏
def record_game(func):
    """装饰器：记录游戏完整流程"""
    def wrapper(*args, **kwargs):
        # 开始游戏
        recorder.start_game(
            story_title=kwargs.get('story_title', 'Unknown'),
            story_surface=kwargs.get('story_surface', ''),
            story_bottom=kwargs.get('story_bottom', ''),
            player_name=kwargs.get('player_name', 'Player'),
            host_difficulty=kwargs.get('host_difficulty', 'normal')
        )
        
        # 执行游戏
        result = func(*args, **kwargs)
        
        # 结束游戏
        recorder.end_game(
            bob_won=kwargs.get('bob_won', False),
            player_won=kwargs.get('player_won', False),
            final_score=kwargs.get('final_score', 0)
        )
        
        return result
    return wrapper
