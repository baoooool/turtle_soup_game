from app.config import LANGUAGE

# ---------------------------------------------------------------------------
# Centralised i18n strings.  LANGUAGE is read once at import time from
# the TS_LANGUAGE environment variable ("zh" or "en", default "zh").
# ---------------------------------------------------------------------------

_LANG = LANGUAGE

# ── LLM system prompts ────────────────────────────────────────────────────

if _LANG == "en":
    QUESTION_SYSTEM_PROMPT = """You are a Turtle Soup game host. You know the full story (bottom).
The bottom is the absolute truth. Judge the player's question against the bottom truth.
Answer with only one of: Yes / No / Irrelevant.
- Yes: if the question is consistent with the bottom truth.
- No: if the question contradicts the bottom truth.
- Irrelevant: if the question has nothing to do with the bottom truth.
Do not reveal any part of the bottom."""

    BOB_SYSTEM_PROMPT = """You are Bob, a rational player in a Turtle Soup game.
Based on the surface and history, generate a JSON action:
{"action": "question", "text": "...", "reasoning": "..."} or {"action": "guess", "text": "...", "reasoning": "..."}
Ask elimination questions or make a final guess.
IMPORTANT: Your questions MUST be answerable with only "Yes", "No", or "Irrelevant". Do NOT ask open-ended questions like "why", "how", "what happened". Only ask questions that can be answered with yes/no.
When you have asked enough questions (5+ rounds) and feel confident about the answer, make a final guess instead of asking more questions.
The "reasoning" field should briefly explain your thought process for this action."""

    BOB_JUDGE_SYSTEM_PROMPT = """You are a judge for Bob's guess in a Turtle Soup game.
Score the guess against the bottom truth. Return JSON:
{"hit": true/false, "score": 0-100, "comment": "..."}"""

    JUDGE_SYSTEM_PROMPT = """You are a judge for a player's final guess in a Turtle Soup game.
Score the guess against the bottom truth. Return JSON:
{"hit": true/false, "score": 0-100, "comment": "..."}"""

    QUESTION_RETRY_SUFFIX = "Return only: Yes / No / Irrelevant."
    BOB_ACTION_RETRY_SUFFIX = "Output JSON only."
    JUDGE_RETRY_SUFFIX = "Output JSON only."
else:
    QUESTION_SYSTEM_PROMPT = """你是一个海龟汤游戏的主持人。你知道完整故事（汤底）。
汤底是绝对真理。根据汤底判断玩家的问题。
只回答：是 / 不是 / 没有关系。
- 是：如果问题与汤底一致。
- 不是：如果问题与汤底矛盾。
- 没有关系：如果问题与汤底无关。
不要透露任何汤底内容。"""

    BOB_SYSTEM_PROMPT = """你是 Bob，海龟汤游戏中的理性玩家。
根据汤面和历史问答，生成一个 JSON 动作：
{"action": "question", "text": "...", "reasoning": "..."} 或 {"action": "guess", "text": "...", "reasoning": "..."}
提出排除性问题或做出最终猜测。
重要：你的问题必须能用"是"、"不是"或"没有关系"来回答。不要问"为什么"、"怎么"、"发生了什么"等开放式问题。只问可以用是/否回答的问题。
当你已经问了足够多的问题（5轮以上）且对答案有把握时，做出最终猜测而不是继续提问。
"reasoning" 字段应简要说明你此次行动的思考过程。"""

    BOB_JUDGE_SYSTEM_PROMPT = """你是 Bob 猜测的裁判。
根据汤底对 Bob 的猜测进行评分。返回 JSON：
{"hit": true/false, "score": 0-100, "comment": "..."}"""

    JUDGE_SYSTEM_PROMPT = """你是玩家最终猜测的裁判。
根据汤底对玩家的猜测进行评分。返回 JSON：
{"hit": true/false, "score": 0-100, "comment": "..."}"""

    QUESTION_RETRY_SUFFIX = "只返回：是 / 不是 / 没有关系。"
    BOB_ACTION_RETRY_SUFFIX = "只输出 JSON。"
    JUDGE_RETRY_SUFFIX = "只输出 JSON。"

# ── UI text ────────────────────────────────────────────────────────────────

if _LANG == "en":
    UI = {
        # Boot / status
        "boot_loading": "Loading stories and sounds...",
        "boot_ready": "Ready! {count} stories loaded.",
        "boot_no_stories": "No stories found yet. Add a .txt story under stories/.",
        "boot_preparing": "Getting things ready...",
        "status_playing": "Now playing: {title}",
        "status_choose_story": "Choose your story to enter the chat room.",
        "status_font_limited": "Font environment limited: install scalable fonts to enable larger text",
        "status_audio_unavailable": "Audio output unavailable: check WSL audio runtime",
        "status_judging_bob": "Judging Bob's theory...",
        "status_judging_player": "Judging your theory...",
        "status_next_question": "Your turn to ask the next question.",
        "status_bob_cracked": "Bob cracked the case!",
        "status_bob_reassess": "Bob is stepping back to reassess. Your turn.",
        "status_player_solved": "Amazing! You solved it.",
        "status_player_close": "Nice try. Full story revealed.",
        "status_ready": "Ready",

        # Startup
        "startup_title": "Turtle Soup",
        "startup_subtitle": "this is a turtlesoup game developed by Owen Bao, Jacky Yang and Xuan Puu",
        "startup_booting": "Booting",

        # Menu
        "menu_greeting": "Nice to meet you",
        "menu_choose": "Choose Your Story",
        "menu_no_stories": "No stories are available yet. Please add files under stories/.",
        "menu_first_prompt": "Which story would you like to play?",
        "menu_retry_prompt": "Which one would you like to play next?",
        "menu_soupie_intro": "Hello, I am Soupie, your story game agent. I'll guide you through this mystery chat.",
        "menu_bob_intro": "Hello, I'm Bob. I focus on rational elimination questions to test hypotheses and reduce uncertainty.",

        # Game screen
        "game_story_surface": "Story Surface",
        "game_story_surface_title": "Story Surface · {title}",
        "game_story_header_empty": "Choose a story to see the surface here.",
        "game_question_placeholder": "Ask anything to uncover the truth...",
        "game_send": "Send",
        "game_final_guess": "Final Guess",
        "game_back_to_menu": "Back",
        "game_thinking": ["Thinking   ", "Thinking.  ", "Thinking.. ", "Thinking..."],

        # Dialog
        "dialog_notice": "Notice",
        "dialog_choose_story": "Please choose a story first.",
        "dialog_start_story": "Please start a story first.",
        "dialog_wait_reply": "Please wait for the current reply to finish.",
        "dialog_wait_bob": "Please wait for Bob to finish his turn.",
        "dialog_wait_bob_guess": "Please wait for Bob to finish his turn before submitting a final theory.",
        "dialog_story_unavailable": "Current story is unavailable. Please start again.",
        "dialog_model_no_response": "Model did not respond. Check local service and retry.",
        "dialog_bob_thinking": "Bob is formulating a rational question...",
        "dialog_bob_no_response": "Bob couldn't respond right now. Please retry in a moment.",
        "dialog_soupy_answering": "Soupy is answering Bob...",
        "dialog_judge_unavailable": "Judge is unavailable right now. Please retry in a moment.",
        "dialog_new_round": "New round ready",
        "dialog_correct": "Correct!",
        "dialog_not_quite": "Not quite.",
        "dialog_final_title": "Final Theory",
        "dialog_final_prompt": "Share your full final theory:",
        "dialog_cancel": "Cancel",
        "dialog_submit": "Submit",

        # Custom story dialog
        "custom_story_title": "Create Custom Story",
        "custom_story_label_title": "Title",
        "custom_story_label_surface": "Story Surface (汤面)",
        "custom_story_label_bottom": "Story Bottom (汤底)",
        "custom_story_placeholder_title": "Enter story title...",
        "custom_story_placeholder_surface": "Enter the story surface...",
        "custom_story_placeholder_bottom": "Enter the story bottom (truth)...",
        "custom_story_detect_lang": "Auto-detect language",
        "custom_story_saved": "Story saved successfully!",
        "custom_story_fill_all": "Please fill in all fields.",
        "custom_story_translating": "Translating...",

        # Story management
        "story_management_title": "Story Management",
        "story_management_delete_confirm": "Are you sure you want to delete '{story}'?",
        "story_management_deleted": "Story deleted.",
        "story_management_back": "Back",
        "story_management_add": "Add New Story",

        # Player profiles
        "player_choose": "Choose Your Player",
        "player_hint": "Select an existing profile or create a new one to continue.",
        "player_create": "Create New Player",
        "player_back": "Back to Player Select",
        "player_select": "Select",
        "player_delete": "Delete",
        "player_name_label": "Player Name",
        "player_name_placeholder": "Enter player name...",
        "player_avatar_label": "Avatar",
        "player_create_title": "Create New Player",
        "player_created": "Player '{name}' created!",
        "player_delete_confirm": "Are you sure you want to delete '{player}'?",
        "player_deleted": "Player deleted.",
        "player_cannot_delete_bob": "Bob cannot be deleted.",
        "player_name_exists": "Player name already exists.",
        "player_name_empty": "Player name cannot be empty.",

        # Leaderboard
        "leaderboard_title": "Leaderboard",
        "leaderboard_back": "Back to Story Menu",
        "leaderboard_rank": "Rank",
        "leaderboard_score": "Score",
        "leaderboard_empty": "No players yet.",

        # Bubble messages
        "speaker_soupy": "Soupy",
        "speaker_bob": "Bob",
        "speaker_you": "You",
        "speaker_judge": "Judge",
        "speaker_system": "System",
        "bubble_story": "Story surface is pinned above. Ask your questions anytime. I will reply with only: Yes / No / Irrelevant.",
        "bubble_rules": "Story surface is pinned above. Ask your questions anytime. I will reply with only: Yes / No / Irrelevant.",
        "bubble_full_story": "Here is the full story: {story}",
        "bubble_next_game": "Which one would you like to play next? Click Back to Story Menu to continue.",
        "bubble_bob_reassess": "I'll step back to reassess. Please continue your line of questioning.",
        "bubble_bob_score": "Bob's theory scored {score}/100. {comment}",
        "bubble_bob_final_guess": "Final guess: {guess}",
        "bubble_player_final_guess": "Final guess: {guess}",
        "bubble_verdict": "{verdict} (match score {score}/100) {comment}",

        # LLM prompt labels
        "prompt_surface": "Surface",
        "prompt_history": "History",
        "prompt_bottom": "Ground Truth (do not reveal)",
        "prompt_question": "Player Question",
        "prompt_return": "Return only: Yes / No / Irrelevant.",
        "prompt_json_only": "Output JSON only.",
        "prompt_bottom_label": "Ground Truth",

        # Misc
        "no_history": "No Q&A history yet.",
        "context_q": "Q",
        "context_a": "A",
        "judge_default_comment": "Close, but key causal links are still missing.",
        "judge_comment_done": "Judgment completed.",
        "answer_irrelevant": "Irrelevant.",
        "bob_default_question": "Is the key factor a deliberate human choice rather than an accident or coincidence?",
        "lang_toggle": "中文",
        "lang_label": "Language:",
        "lang_restart_notice": "Language will be set to {lang}. The app will restart.",
        "bob_toggle_on": "Bob: ON",
        "bob_toggle_off": "Bob: OFF",
        "bob_label": "Bob Companion",
        "bob_disabled_notice": "Bob is disabled and will no longer participate.",
        "bob_enabled_notice": "Bob is enabled and will play with you.",
    }
else:
    UI = {
        # Boot / status
        "boot_loading": "正在加载故事和音效...",
        "boot_ready": "就绪！已加载 {count} 个故事。",
        "boot_no_stories": "未找到故事。请在 stories/ 下添加 .txt 故事文件。",
        "boot_preparing": "正在准备...",
        "status_playing": "正在游玩：{title}",
        "status_choose_story": "选择故事进入游戏。",
        "status_font_limited": "字体环境受限：安装可缩放字体以启用大字体",
        "status_audio_unavailable": "音频输出不可用：请检查 WSL 音频运行时",
        "status_judging_bob": "正在评判 Bob 的猜测...",
        "status_judging_player": "正在评判你的猜测...",
        "status_next_question": "轮到你提问了。",
        "status_bob_cracked": "Bob 破解了谜题！",
        "status_bob_reassess": "Bob 正在重新评估。轮到你了。",
        "status_player_solved": "太棒了！你解开了谜题。",
        "status_player_close": "猜得好！完整故事已揭晓。",
        "status_ready": "准备就绪",

        # Startup
        "startup_title": "海龟汤",
        "startup_subtitle": "这是一个由 Owen Bao、Jacky Yang 和 Xuan Puu 开发的海龟汤游戏",
        "startup_booting": "启动中",

        # Menu
        "menu_greeting": "你好",
        "menu_choose": "选择你的故事",
        "menu_no_stories": "还没有故事。请在 stories/ 下添加文件。",
        "menu_first_prompt": "你想玩哪一个故事？",
        "menu_retry_prompt": "你想玩哪一个？",
        "menu_soupie_intro": "你好，我是 Soupy，你的海龟汤游戏主持人。我会引导你完成这场推理聊天。",
        "menu_bob_intro": "你好，我是 Bob。我专注于通过理性排除问题来验证假设、减少不确定性。",

        # Game screen
        "game_story_surface": "汤面",
        "game_story_surface_title": "汤面 · {title}",
        "game_story_header_empty": "选择一个故事查看汤面。",
        "game_question_placeholder": "提问来揭开真相...",
        "game_send": "发送",
        "game_final_guess": "最终猜测",
        "game_back_to_menu": "返回",
        "game_thinking": ["思考中   ", "思考中.  ", "思考中.. ", "思考中..."],

        # Dialog
        "dialog_notice": "提示",
        "dialog_choose_story": "请先选择一个故事。",
        "dialog_start_story": "请先开始一个故事。",
        "dialog_wait_reply": "请等待当前回复完成。",
        "dialog_wait_bob": "请等待 Bob 完成他的回合。",
        "dialog_wait_bob_guess": "请等待 Bob 完成猜测后再提交最终答案。",
        "dialog_story_unavailable": "当前故事不可用。请重新开始。",
        "dialog_model_no_response": "模型没有响应。请检查本地服务并重试。",
        "dialog_bob_thinking": "Bob 正在构思一个理性问题...",
        "dialog_bob_no_response": "Bob 暂时无法回应。请稍后重试。",
        "dialog_soupy_answering": "Soupy 正在回答 Bob...",
        "dialog_judge_unavailable": "裁判暂时不可用。请稍后重试。",
        "dialog_new_round": "新一轮就绪",
        "dialog_correct": "正确！",
        "dialog_not_quite": "不太对。",
        "dialog_final_title": "最终猜测",
        "dialog_final_prompt": "分享你的完整最终猜测：",
        "dialog_cancel": "取消",
        "dialog_submit": "提交",

        # Custom story dialog
        "custom_story_title": "创建自定义故事",
        "custom_story_label_title": "标题",
        "custom_story_label_surface": "汤面",
        "custom_story_label_bottom": "汤底",
        "custom_story_placeholder_title": "输入故事标题...",
        "custom_story_placeholder_surface": "输入汤面内容...",
        "custom_story_placeholder_bottom": "输入汤底（真相）...",
        "custom_story_detect_lang": "自动检测语言",
        "custom_story_saved": "故事保存成功！",
        "custom_story_fill_all": "请填写所有字段。",
        "custom_story_translating": "翻译中...",

        # Story management
        "story_management_title": "故事管理",
        "story_management_delete_confirm": "确定要删除'{story}'吗？",
        "story_management_deleted": "故事已删除。",
        "story_management_back": "返回",
        "story_management_add": "添加新故事",

        # Player profiles
        "player_choose": "选择你的玩家",
        "player_hint": "选择现有档案或创建新玩家以继续。",
        "player_create": "创建新玩家",
        "player_back": "返回玩家选择",
        "player_select": "选择",
        "player_delete": "删除",
        "player_name_label": "玩家名称",
        "player_name_placeholder": "输入玩家名称...",
        "player_avatar_label": "头像",
        "player_create_title": "创建新玩家",
        "player_created": "玩家'{name}'已创建！",
        "player_delete_confirm": "确定要删除'{player}'吗？",
        "player_deleted": "玩家已删除。",
        "player_cannot_delete_bob": "Bob 不能被删除。",
        "player_name_exists": "玩家名称已存在。",
        "player_name_empty": "玩家名称不能为空。",

        # Leaderboard
        "leaderboard_title": "排行榜",
        "leaderboard_back": "返回故事菜单",
        "leaderboard_rank": "排名",
        "leaderboard_score": "分数",
        "leaderboard_empty": "还没有玩家。",

        # Bubble messages
        "speaker_soupy": "Soupy",
        "speaker_bob": "Bob",
        "speaker_you": "你",
        "speaker_judge": "裁判",
        "speaker_system": "系统",
        "bubble_story": "汤面已显示在上方。随时提问，我会回答：是 / 不是 / 没有关系。",
        "bubble_rules": "汤面已显示在上方。随时提问，我会回答：是 / 不是 / 没有关系。",
        "bubble_full_story": "完整故事：{story}",
        "bubble_next_game": "接下来想玩哪一个？点击「返回故事菜单」继续。",
        "bubble_bob_reassess": "我退后一步重新评估。请继续你的提问。",
        "bubble_bob_score": "Bob 的猜测得分 {score}/100。{comment}",
        "bubble_bob_final_guess": "最终猜测：{guess}",
        "bubble_player_final_guess": "最终猜测：{guess}",
        "bubble_verdict": "{verdict}（匹配度 {score}/100）{comment}",

        # LLM prompt labels
        "prompt_surface": "汤面",
        "prompt_history": "历史问答",
        "prompt_bottom": "汤底（不要透露）",
        "prompt_question": "玩家问题",
        "prompt_return": "只返回：是 / 不是 / 没有关系。",
        "prompt_json_only": "只输出 JSON。",
        "prompt_bottom_label": "汤底",

        # Misc
        "no_history": "还没有问答记录。",
        "context_q": "问",
        "context_a": "答",
        "judge_default_comment": "接近了，但关键的因果链还缺失。",
        "judge_comment_done": "评判完成。",
        "answer_irrelevant": "没有关系。",
        "bob_default_question": "关键因素是人类的选择，而不是意外或巧合吗？",
        "lang_toggle": "EN",
        "lang_label": "语言设置",
        "lang_restart_notice": "语言将切换为 {lang}，应用将重新启动。",
        "bob_toggle_on": "Bob: 开启",
        "bob_toggle_off": "Bob: 关闭",
        "bob_label": "Bob 陪玩",
        "bob_disabled_notice": "Bob 已关闭，将不再参与游戏。",
        "bob_enabled_notice": "Bob 已开启，将与你一起推理。",
    }

__all__ = [
    "LANGUAGE",
    "UI",
    "QUESTION_SYSTEM_PROMPT",
    "BOB_SYSTEM_PROMPT",
    "BOB_JUDGE_SYSTEM_PROMPT",
    "JUDGE_SYSTEM_PROMPT",
    "QUESTION_RETRY_SUFFIX",
    "BOB_ACTION_RETRY_SUFFIX",
    "JUDGE_RETRY_SUFFIX",
]
