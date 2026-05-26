# 🎮 海龟汤游戏

一个基于大语言模型的海龟汤游戏，支持多种 LLM 引擎和智能游戏记录。

---

## 🚀 快速开始

### 1. 启动游戏

```bash
D:\Anaconda\envs\turtle\python.exe main.py
```

### 2. 设置主持人难度

游戏内点击 **"BOB 属性"** 按钮，选择难度：
- **严谨** - 只回答"是"/"不是"/"没有关系"
- **正常** ⭐ - 连续 3 个无关问题或每 10 轮给提示（推荐）
- **支持** - 说明答案重要性，给予更多指导

---

## 📚 功能文档

详细功能说明请查看 [`GUIDE.md`](GUIDE.md)，包含：

1. **主持人难度设置** - 三种难度详解
2. **游戏自动记录** - 自动记录所有游戏数据
3. **训练专属模型** - 使用 LoRA 微调技术
4. **快速使用流程** - 完整工作流
5. **常见问题解答** - Q&A

---

## 🎯 核心功能

### 1. 游戏自动记录

每次游戏自动记录：
- ✅ 所有玩家问答
- ✅ 所有 BOB 问答
- ✅ 游戏结果（轮数、得分、胜负）
- ✅ 自动生成训练数据

**记录位置**：`game_records/`

**查看工具**：
```bash
python view_records.py
```

### 2. 训练专属模型

当游戏记录达到 **500+ 条** 时，可以训练专属模型：

```bash
# 1. 导出训练数据
python view_records.py  # 选择 3. 导出训练数据

# 2. 开始训练
python train_turtle_lora.py

# 3. 获得专属模型！
```

**训练时间**：30-60 分钟  
**显存需求**：2-4GB

---

## 📁 项目结构

```
turtle_soup_game/
├── app/                      # 核心代码
│   ├── game/
│   │   ├── manager.py        # 游戏管理器
│   │   └── recorder.py       # 游戏记录器
│   ├── llm/
│   │   ├── config.py         # 配置
│   │   ├── ollama_engine.py  # Ollama 引擎
│   │   └── local_engine.py   # 本地引擎
│   └── ui/
│       └── main_window.py    # 主界面
│
├── game_records/             # 游戏记录（自动生成）
│   ├── game_*.json          # 单场游戏记录
│   └── training_data.jsonl  # 训练数据
│
├── GUIDE.md                  # 完整功能指南
├── main.py                   # 游戏入口
├── view_records.py           # 记录管理工具
├── train_turtle_lora.py      # 训练脚本
└── generate_training_data.py # 数据生成工具
```

---

## 🛠️ 依赖安装

### 基础依赖

```bash
pip install customtkinter pillow -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 训练依赖（可选）

```bash
pip install peft transformers datasets accelerate bitsandbytes -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 🎮 使用说明

### 开始游戏

1. 运行 `main.py`
2. 选择或创建故事
3. 开始提问（玩家）
4. BOB 回答（是/不是/没有关系）
5. 猜测真相

### 查看游戏记录

```bash
python view_records.py
```

菜单：
1. 查看所有记录
2. 查看指定记录
3. 导出训练数据
4. 显示统计信息

### 训练模型

1. 玩游戏收集数据（建议 500+ 条）
2. 运行 `python view_records.py` 导出数据
3. 运行 `python train_turtle_lora.py` 开始训练

---

## 📊 统计信息

查看游戏统计：

```bash
python view_records.py  # 选择 4
```

示例输出：
```
总游戏数：25
玩家获胜：18 (72.0%)
BOB 获胜：5 (20.0%)
平均轮数：12.4
平均得分：78.5
训练数据：310 条
```

---

## 💡 常见问题

### Q: 显存不足怎么办？

使用更小的模型（在 `train_turtle_lora.py` 中修改）：
```python
BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"  # 仅需 2GB
```

### Q: 训练数据不够？

多玩游戏！每场游戏自动生成 10-30 条数据。

### Q: 如何切换回 Ollama？

修改 `app/llm/config.py`：
```python
LLM_ENGINE_TYPE = "ollama"  # 从 "local" 改回
```

---

## 📖 更多帮助

- 详细功能说明：[`GUIDE.md`](GUIDE.md)
- 游戏记录管理：`python view_records.py`
- 训练脚本：`train_turtle_lora.py`

---

## 🎉 总结

**核心优势**：
- ✅ 三种主持人难度，适合不同玩家
- ✅ 自动记录游戏，收集训练数据
- ✅ 一键训练专属模型
- ✅ 低显存需求（2-4GB 即可）

**下一步**：
1. 启动游戏
2. 设置难度
3. 开始玩（自动记录）
4. 数据足够后训练模型

**祝你游戏愉快！** 🎮
