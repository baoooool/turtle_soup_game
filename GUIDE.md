# 🎮 海龟汤游戏 - 完整功能指南

> 本指南包含游戏的所有高级功能：主持人难度选择、游戏自动记录、专属模型训练

---

## 📋 目录

1. [主持人难度设置](#1-主持人难度设置)
2. [游戏自动记录](#2-游戏自动记录)
3. [训练专属模型](#3-训练专属模型)
4. [快速使用流程](#4-快速使用流程)
5. [常见问题解答](#5-常见问题解答)

---

## 1. 主持人难度设置

### 🎯 功能说明

游戏支持三种主持人难度模式，可以在 BOB 属性界面中切换：

| 难度 | 特点 | 适合人群 |
|------|------|----------|
| **严谨** | 只回答"是"/"不是"/"没有关系" | 高手、挑战者 |
| **正常** ⭐ | 连续 3 个无关问题或每 10 轮给提示 | 大多数玩家 |
| **支持** | 说明答案重要性，给予更多指导 | 新手玩家 |

### 🔧 设置方法

#### 方法 1：游戏内设置（推荐）

1. 启动游戏
2. 点击主界面的 **"BOB 属性"** 按钮
3. 在"主持人难度"区域选择：
   - **严谨** - 只回答是否无关
   - **正常** - 适度提示
   - **支持** - 详细说明

#### 方法 2：修改配置文件

打开 `app/llm/config.py`，找到第 15 行：

```python
HOST_DIFFICULTY: Literal["strict", "normal", "supportive"] = "normal"
```

修改为：
- `"strict"` - 严谨模式
- `"normal"` - 正常模式
- `"supportive"` - 支持模式

### 📊 效果对比

**严谨模式**：
```
玩家：海龟汤的味道重要吗？
BOB: 是
```

**正常模式**：
```
玩家：海龟汤的味道重要吗？
BOB: 是

[连续 3 个无关问题后]
BOB: 没有关系。想想看，岛上的条件有什么特殊？
```

**支持模式**：
```
玩家：海龟汤的味道重要吗？
BOB: 是，这很关键！

[连续 3 个无关问题后]
BOB: 没有关系。你忽略了关键信息，想想他当年的经历
```

---

## 2. 游戏自动记录

### 🎯 功能说明

游戏会**自动记录**每一次游玩的完整流程，包括：
- ✅ 所有玩家问答
- ✅ 所有 BOB 问答
- ✅ 游戏结果（轮数、得分、胜负）
- ✅ 主持人难度设置
- ✅ 故事信息（汤面、汤底）

**完全自动**，不需要任何额外操作！

### 📁 记录位置

```
game_records/
├── game_20260526_175720.json    # 单场游戏记录（按时间命名）
├── game_20260526_181230.json
├── ...
└── training_data.jsonl          # 自动生成的训练数据
```

### 🔍 查看记录

#### 方法 1：使用管理工具

```bash
D:\Anaconda\envs\turtle\python.exe view_records.py
```

**菜单**：
```
1. 查看所有记录      # 列出所有游戏
2. 查看指定记录      # 查看单场详情
3. 导出训练数据      # 导出到 train_data.jsonl
4. 显示统计信息      # 游戏数据统计
5. 退出
```

#### 方法 2：直接打开文件

用文本编辑器打开 `game_records/game_*.json`：

```json
{
  "timestamp": "2026-05-26T17:57:20",
  "story_title": "海龟汤",
  "story_surface": "一个人走进餐厅，点了一碗海龟汤...",
  "story_bottom": "他曾经和死去的女友一起喝过海龟汤...",
  "player_name": "Alice",
  "host_difficulty": "normal",
  "qa_records": [
    {
      "question": "海龟汤的味道重要吗？",
      "answer": "是",
      "turn_number": 1,
      "player_type": "player"
    },
    {
      "question": "他以前喝过吗？",
      "answer": "是",
      "turn_number": 2,
      "player_type": "player"
    }
  ],
  "total_turns": 15,
  "bob_won": false,
  "player_won": true,
  "final_score": 85
}
```

### 📊 统计信息示例

```
============================================================
游戏统计
============================================================
总游戏数：25
玩家获胜：18 (72.0%)
BOB 获胜：5 (20.0%)
平均轮数：12.4
平均得分：78.5
训练数据：310 条
```

---

## 3. 训练专属模型

### 🎯 功能说明

使用 **LoRA 微调技术**，基于你的游戏记录训练专属的海龟汤模型：

- ✅ 显存需求低（2-4GB 即可）
- ✅ 训练速度快（30-60 分钟）
- ✅ 模型文件小（仅几 MB）
- ✅ 效果好（接近全量微调）

### 📋 准备工作

#### 3.1 安装依赖

```bash
pip install peft transformers datasets accelerate bitsandbytes -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 3.2 准备训练数据

**方法 1：从游戏记录导出（推荐）**

```bash
D:\Anaconda\envs\turtle\python.exe view_records.py
# 选择 3. 导出训练数据
```

会自动导出到 `train_data.jsonl`

**方法 2：手动编写**

编辑 `train_data.jsonl`，添加训练数据（每行一个 JSON）：

```json
{"messages": [
    {"role": "system", "content": "你是海龟汤游戏的主持人。"},
    {"role": "user", "content": "海龟汤的味道重要吗？"},
    {"role": "assistant", "content": "是"}
]}
{"messages": [
    {"role": "system", "content": "你是海龟汤游戏的主持人。"},
    {"role": "user", "content": "他是在岛上喝的吗？"},
    {"role": "assistant", "content": "是，这很关键"}
]}
```

**数据量建议**：
- 最小：100 条
- 推荐：500-1000 条
- 理想：2000+ 条

### 🚀 开始训练

#### 步骤 1：配置模型

打开 `train_turtle_lora.py`，修改第 23 行：

```python
# 根据你的显存选择模型

# 低配版（2GB 显存）
BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"

# 推荐版（4GB 显存）⭐
BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"

# 高配版（8GB 显存）
BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
```

#### 步骤 2：启动训练

```bash
D:\Anaconda\envs\turtle\python.exe train_turtle_lora.py
```

#### 步骤 3：观察训练进度

```
============================================================
海龟汤 LLM 微调训练
============================================================

1. 加载训练数据...
   数据集大小：500 条

2. 加载基础模型...
   使用 4-bit 量化

3. 配置 LoRA...
trainable params: 1,234,567 || all params: 500,000,000 || trainable%: 0.25%

4. 数据预处理...

5. 开始训练...
{'loss': 0.5234, 'learning_rate': 0.0002, 'epoch': 1.0}
{'loss': 0.3456, 'learning_rate': 0.0002, 'epoch': 2.0}
{'loss': 0.2123, 'learning_rate': 0.0002, 'epoch': 3.0}

6. 保存模型...

============================================================
训练完成！
模型已保存到：./turtle_soup_lora
============================================================
```

### 🧪 测试模型

创建测试脚本 `test_model.py`：

```python
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

# 加载模型
base_model = "Qwen/Qwen2.5-0.5B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(base_model)
model = AutoModelForCausalLM.from_pretrained(base_model)
model = PeftModel.from_pretrained(model, "./turtle_soup_lora")

# 测试
def test(question):
    prompt = f"System: 你是海龟汤游戏的主持人\nUser: {question}\nAssistant: "
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, max_new_tokens=50)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

print(test("海龟汤的味道重要吗？"))
print(test("他是自杀的吗？"))
```

运行测试：

```bash
D:\Anaconda\envs\turtle\python.exe test_model.py
```

### 🔧 集成到游戏

修改 `app/llm/local_engine.py`，添加 LoRA 支持：

```python
from peft import PeftModel
import os

class LocalEngine(BaseLLMEngine):
    def __init__(self, model_name, use_lora=True):
        # 加载基础模型
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        
        # 加载 LoRA 权重
        if use_lora and os.path.exists("./turtle_soup_lora"):
            self.model = PeftModel.from_pretrained(
                self.model, 
                "./turtle_soup_lora"
            )
            print("✅ 已加载海龟汤专属模型")
```

然后修改 `app/llm/config.py`：

```python
LLM_ENGINE_TYPE = "local"  # 从 "ollama" 改为 "local"
```

---

## 4. 快速使用流程

### 🎯 完整工作流

```
1. 设置主持人难度
   → 游戏内点击"BOB 属性"
   → 选择难度（推荐"正常"）
   ↓
2. 开始玩游戏 🎮
   → 自动记录所有问答
   → 自动保存到 game_records/
   ↓
3. 查看游戏记录 📊
   → python view_records.py
   → 查看统计信息
   ↓
4. 导出训练数据 📝
   → python view_records.py → 选择 3
   → 导出到 train_data.jsonl
   ↓
5. 训练专属模型 🚀
   → 数据达到 500+ 条
   → python train_turtle_lora.py
   → 等待 30-60 分钟
   ↓
6. 获得专属模型！🎉
   → 集成到游戏中
   → 享受更智能的 BOB
```

### ⏱️ 时间规划

| 步骤 | 时间 | 说明 |
|------|------|------|
| 设置难度 | 1 分钟 | 游戏内设置 |
| 玩游戏 | 10-20 分钟/场 | 自动记录 |
| 导出数据 | 1 分钟 | 一键导出 |
| 训练模型 | 30-60 分钟 | 自动完成 |
| **总计** | **2-3 小时** | 物超所值！ |

### 📊 资源需求

| 配置 | 显存 | 训练时间 | 推荐度 |
|------|------|----------|--------|
| 0.5B | 2 GB | 30 分钟 | ⭐⭐⭐ |
| 1.5B | 4 GB | 45 分钟 | ⭐⭐⭐⭐⭐ |
| 3B | 8 GB | 60 分钟 | ⭐⭐⭐⭐ |

---

## 5. 常见问题解答

### Q1: 显存不足怎么办？

**方案 1**：使用更小的模型
```python
BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"  # 仅需 2GB
```

**方案 2**：降低 batch_size
```python
TRAIN_CONFIG = {"batch_size": 1}  # 在 train_turtle_lora.py 第 37 行
```

**方案 3**：使用 CPU 训练（慢但可行）
```python
# 在 train_turtle_lora.py 第 91 行添加
device_map="cpu"
```

### Q2: 训练数据不够怎么办？

**方案 1**：多玩游戏
- 每场游戏自动生成 10-30 条数据
- 玩 20 场就有 200-600 条

**方案 2**：数据增强
```python
# 同义句替换
原句："海龟汤的味道重要吗？"
变体："汤的味道有关系吗？"
变体："味道是关键因素吗？"
```

**方案 3**：先训练小数据集
- 先用 100-200 条试训
- 熟悉流程后再收集更多

### Q3: 训练效果不好怎么办？

1. **增加数据量**：500 → 1000 条
2. **提高数据质量**：确保问答准确
3. **调整学习率**：尝试 1e-4 到 5e-4
4. **增加训练轮数**：3 → 5-10 轮

### Q4: 如何切换回 Ollama 模型？

修改 `app/llm/config.py`：

```python
LLM_ENGINE_TYPE = "ollama"  # 从 "local" 改回 "ollama"
```

### Q5: 游戏记录太多怎么办？

**定期清理**：
```bash
# 删除 30 天前的记录
# Windows PowerShell
Get-ChildItem game_records\game_*.json | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | Remove-Item
```

**备份重要记录**：
```bash
# 复制到备份目录
xcopy /E /I game_records game_records_backup
```

---

## 📚 附录

### A. 文件结构

```
turtle_soup_game/
├── app/
│   ├── game/
│   │   ├── recorder.py          # 游戏记录器
│   │   └── manager.py           # 游戏管理器（已集成记录）
│   ├── llm/
│   │   ├── config.py            # 配置（含难度设置）
│   │   ├── ollama_engine.py     # Ollama 引擎
│   │   └── local_engine.py      # 本地引擎（可加载 LoRA）
│   └── ui/
│       └── main_window.py       # 主界面（含 BOB 属性）
│
├── game_records/                 # 游戏记录目录
│   ├── game_*.json              # 单场游戏记录
│   └── training_data.jsonl      # 训练数据
│
├── train_turtle_lora.py         # 训练脚本
├── view_records.py              # 记录管理工具
├── generate_training_data.py    # 数据生成工具
└── GUIDE.md                     # 本文档
```

### B. 关键代码位置

| 功能 | 文件 | 说明 |
|------|------|------|
| 主持人难度配置 | `app/llm/config.py` | 第 15 行 |
| BOB 属性界面 | `app/ui/main_window.py` | 第 758-797 行 |
| 游戏记录器 | `app/game/recorder.py` | 完整实现 |
| 训练脚本 | `train_turtle_lora.py` | 完整实现 |
| 记录管理 | `view_records.py` | 完整实现 |

### C. 训练数据格式

**标准格式**（JSONL，每行一个）：
```json
{"messages": [
    {"role": "system", "content": "你是海龟汤游戏的主持人。难度模式：normal"},
    {"role": "user", "content": "你的问题"},
    {"role": "assistant", "content": "是/不是/没有关系"}
]}
```

### D. 快速命令参考

```bash
# 查看游戏记录
python view_records.py

# 导出训练数据
python view_records.py  # 选择 3

# 开始训练
python train_turtle_lora.py

# 测试模型
python test_model.py

# 查看训练数据数量
python -c "from app.game.recorder import recorder; print(f'{recorder.get_training_data_count()} 条')"
```

---

## 🎉 总结

### 核心功能

1. **主持人难度** - 三种难度，适合不同玩家
2. **自动记录** - 玩游戏自动收集训练数据
3. **专属模型** - 用你的数据训练更智能的 BOB

### 优势对比

| 功能 | 传统方式 | 本游戏 |
|------|----------|--------|
| 难度设置 | 固定 | 三档可调 ✅ |
| 数据收集 | 手动 | 自动记录 ✅ |
| 数据质量 | 虚构 | 真实游戏 ✅ |
| 模型训练 | 复杂 | 一键训练 ✅ |
| 个性化 | 无 | 专属模型 ✅ |

### 下一步

1. ✅ 设置主持人难度（游戏内"BOB 属性"）
2. ✅ 开始玩游戏（自动记录）
3. ✅ 定期查看统计（`python view_records.py`）
4. ✅ 数据足够后训练模型（500+ 条）
5. ✅ 享受专属智能 BOB！

---

## 📞 技术支持

如有问题，请查看：
1. 本文档的 [常见问题解答](#5-常见问题解答)
2. 各功能的详细说明文件
3. 代码注释

---

**祝你游戏愉快，训练顺利！** 🎮🚀
