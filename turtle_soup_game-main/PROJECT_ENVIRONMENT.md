# Turtle Soup Game 项目环境说明

本文面向准备在本地运行本项目的同学，介绍运行环境、依赖、目录约定与常见问题。

## 1. 项目定位与运行方式

- **类型**：Python 桌面 GUI 游戏（Turtle Soup / 海龟汤问答）
- **入口**：`main.py`
- **UI 框架**：`customtkinter`（基于 Tk）
- **音频**：`pygame.mixer`
- **图片资源**：`Pillow` + 项目内像素素材
- **LLM 接入**：兼容 OpenAI API 协议的接口（默认连接本地 `http://127.0.0.1:11434/v1`）

## 2. 推荐系统环境

- **操作系统**：Linux / macOS / Windows（建议 Linux 或 WSL）
- **Python 版本**：3.11（项目当前环境已使用 3.11）
- **显示环境**：需要可用图形界面（GUI），纯无头终端无法直接打开窗口

> 在 WSL/Linux 下如果字体异常，项目内有提示安装 X11 字体包。

## 3. Python 依赖

`requirements.txt` 中依赖如下：

- `customtkinter==5.2.2`
- `openai==1.82.0`
- `pygame==2.6.1`
- `pillow==10.4.0`

安装方式：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 4. 关键环境变量（LLM 与界面）

项目会读取以下环境变量（来自 `app/config.py` 和 `app/ui/main_window.py`）：

| 变量名 | 默认值 | 说明 |
| --- | --- | --- |
| `TS_BASE_URL` | `http://127.0.0.1:11434/v1` | LLM API Base URL（OpenAI 兼容） |
| `TS_API_KEY` | `local-key` | LLM API Key |
| `TS_MODEL` | `qwen2.5:7b-instruct` | 使用的模型名 |
| `TS_TEMPERATURE` | `0.2` | 问答温度参数 |
| `TS_CONTEXT_WINDOW` | `8` | 对话历史保留轮数 |
| `TS_FONT_SCALE` | `1.0` | UI 字体缩放倍率 |

示例（bash）：

```bash
export TS_BASE_URL="http://127.0.0.1:11434/v1"
export TS_API_KEY="local-key"
export TS_MODEL="qwen2.5:7b-instruct"
export TS_TEMPERATURE="0.2"
export TS_CONTEXT_WINDOW="8"
export TS_FONT_SCALE="1.0"
```

## 5. 目录与资源约定

- `stories/`：剧情文本目录，读取 `*.txt`
- `assets/sfx/`：音效目录（如 `click.wav`、`reply.wav`、`success.wav`、`fail.wav`、`thinking.wav`）
- `PixelPete'sArtAssets/`：像素风美术资源（UI 和角色图片）
- `app/`：核心代码（UI、LLM、音频、故事加载、状态管理）

### Story 文件格式

每个故事文本必须包含以下标签段：

```text
[Title]
...

[Surface]
...

[Bottom]
...
```

缺少任一段会被跳过，不会加载到游戏中。

## 6. 启动方式

在项目根目录执行：

```bash
python main.py
```

启动后会异步加载故事与音频；如果 `stories/` 下没有可用故事，界面会提示没有可用剧情。

## 7. 常见问题

1. **无法连接模型接口**  
   检查 `TS_BASE_URL / TS_API_KEY / TS_MODEL` 是否与本地或远端模型服务一致。

2. **没有声音**  
   `assets/sfx/` 缺少音频文件时会静默跳过；部分环境会自动降级为 `SDL_AUDIODRIVER=dummy`。

3. **字体放大不生效（Linux/WSL）**  
   若仅识别 `fixed` 字体，安装：
   `sudo apt update && sudo apt install -y xfonts-base xfonts-75dpi xfonts-100dpi`

