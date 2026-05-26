"""
海龟汤 LLM 微调训练脚本
使用 LoRA 技术微调 Qwen2.5 模型

依赖安装：
pip install peft transformers datasets accelerate bitsandbytes
"""

import json
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
    TaskType
)
import torch

# ==================== 配置 ====================

# 基础模型（从 Ollama 导出或使用 HuggingFace）
BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"  # 或 "Qwen/Qwen2.5-1.5B-Instruct"

# LoRA 配置
LORA_CONFIG = {
    "r": 8,  # LoRA 秩，越大效果越好但显存占用越高
    "lora_alpha": 32,  # LoRA 缩放系数
    "target_modules": ["q_proj", "v_proj"],  # 目标模块
    "lora_dropout": 0.1,
    "bias": "none",
    "task_type": TaskType.CAUSAL_LM,
}

# 训练配置
TRAIN_CONFIG = {
    "epochs": 3,
    "batch_size": 4,
    "learning_rate": 2e-4,
    "max_length": 512,
    "output_dir": "./turtle_soup_lora",
}

# ==================== 数据准备 ====================

def load_training_data(file_path: str = "train_data.jsonl") -> Dataset:
    """加载训练数据"""
    messages = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            messages.append(data["messages"])
    
    # 转换为训练格式
    texts = []
    for msg_list in messages:
        text = ""
        for msg in msg_list:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                text += f"System: {content}\n"
            elif role == "user":
                text += f"User: {content}\n"
            elif role == "assistant":
                text += f"Assistant: {content}\n"
        texts.append(text + "\n")
    
    return Dataset.from_dict({"text": texts})

# ==================== 模型加载 ====================

def load_model_and_tokenizer():
    """加载模型和分词器"""
    print(f"加载基础模型：{BASE_MODEL}")
    
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    tokenizer.pad_token = tokenizer.eos_token
    
    # 4-bit 量化加载（节省显存）
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        load_in_4bit=True,
        device_map="auto",
        torch_dtype=torch.float16,
    )
    
    # 准备 K-bit 训练
    model = prepare_model_for_kbit_training(model)
    
    return model, tokenizer

# ==================== LoRA 配置 ====================

def setup_lora(model):
    """配置 LoRA"""
    print("配置 LoRA...")
    
    peft_config = LoraConfig(
        r=LORA_CONFIG["r"],
        lora_alpha=LORA_CONFIG["lora_alpha"],
        target_modules=LORA_CONFIG["target_modules"],
        lora_dropout=LORA_CONFIG["lora_dropout"],
        bias=LORA_CONFIG["bias"],
        task_type=LORA_CONFIG["task_type"],
    )
    
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    
    return model

# ==================== 数据处理 ====================

def preprocess_function(examples, tokenizer, max_length):
    """数据预处理"""
    return tokenizer(
        examples["text"],
        truncation=True,
        max_length=max_length,
        padding="max_length",
    )

# ==================== 训练 ====================

def train():
    """主训练函数"""
    print("=" * 60)
    print("海龟汤 LLM 微调训练")
    print("=" * 60)
    
    # 1. 加载数据
    print("\n1. 加载训练数据...")
    dataset = load_training_data()
    print(f"   数据集大小：{len(dataset)} 条")
    
    # 2. 加载模型
    print("\n2. 加载基础模型...")
    model, tokenizer = load_model_and_tokenizer()
    
    # 3. 配置 LoRA
    print("\n3. 配置 LoRA...")
    model = setup_lora(model)
    
    # 4. 数据预处理
    print("\n4. 数据预处理...")
    tokenized_dataset = dataset.map(
        lambda x: preprocess_function(x, tokenizer, TRAIN_CONFIG["max_length"]),
        batched=True,
        remove_columns=["text"],
    )
    
    # 5. 训练配置
    training_args = TrainingArguments(
        output_dir=TRAIN_CONFIG["output_dir"],
        num_train_epochs=TRAIN_CONFIG["epochs"],
        per_device_train_batch_size=TRAIN_CONFIG["batch_size"],
        learning_rate=TRAIN_CONFIG["learning_rate"],
        fp16=True,
        logging_steps=10,
        save_strategy="epoch",
        evaluation_strategy="no",
        report_to="none",
    )
    
    # 6. 创建 Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=DataCollatorForLanguageModeling(
            tokenizer, 
            mlm=False
        ),
    )
    
    # 7. 开始训练
    print("\n5. 开始训练...")
    trainer.train()
    
    # 8. 保存模型
    print("\n6. 保存模型...")
    trainer.save_model(TRAIN_CONFIG["output_dir"])
    tokenizer.save_pretrained(TRAIN_CONFIG["output_dir"])
    
    print("\n" + "=" * 60)
    print("训练完成！")
    print(f"模型已保存到：{TRAIN_CONFIG['output_dir']}")
    print("=" * 60)

if __name__ == "__main__":
    train()
