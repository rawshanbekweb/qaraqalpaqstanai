"""
Qwen3-8B QLoRA Fine-tuning — Windows lokal (Unsloth siz)
=========================================================
GPU: RTX 4050 6GB VRAM
Metod: QLoRA (4-bit bitsandbytes + LoRA)

Ishlatiw:
    python finetune.py
    python finetune.py --epochs 5 --output ./mening_modelim
"""

import os, sys, json, argparse, warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
warnings.filterwarnings("ignore")

import io
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except AttributeError:
        pass

import torch
import logging
logging.basicConfig(level=logging.WARNING)

from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    TrainingArguments,
    DataCollatorForSeq2Seq,
)
from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig


# ─────────────────────────────────────────────────────────────
#  KONFIGURATSIYA
# ─────────────────────────────────────────────────────────────
MODEL_NAME      = "Qwen/Qwen2.5-3B-Instruct"   # 3B — 6GB VRAM uchun optimal
DATA_PATH       = "results/karakalpak_training_data.json"
DEFAULT_OUTPUT  = "models/qwen25_karakalpak_qlora"
MAX_SEQ_LEN     = 1024    # 3B model — ko'proq seq len sig'adi
LORA_R          = 32      # 3B uchun r ni oshirdik
LORA_ALPHA      = 64
LORA_DROPOUT    = 0.05
LORA_TARGETS    = ["q_proj", "k_proj", "v_proj", "o_proj",
                   "gate_proj", "up_proj", "down_proj"]

SYSTEM_PROMPT = """Sen Qaraqalpaqstan Respublikasınıń ekonomika ekspertisen.
Barlıq sorawlarga tek Qaraqalpaq tilinde, anıq statistikalıq maǵlıwmatlarǵa
tiykarlanıp professional ekonomikalıq stilde juwap beriw kerek.
Juwap strukturası: Statistika → Analiz → Muammo → Usınıs → Juwmaq."""


# ─────────────────────────────────────────────────────────────
#  MAǴLÍWMAT TAYARLAW
# ─────────────────────────────────────────────────────────────
def load_dataset(data_path: str, tokenizer) -> Dataset:
    with open(data_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    texts = []
    for sample in raw:
        convs = sample["conversations"]
        system = next((c["value"] for c in convs if c["from"] == "system"), SYSTEM_PROMPT)
        human  = next((c["value"] for c in convs if c["from"] == "human"), "")
        gpt    = next((c["value"] for c in convs if c["from"] == "gpt"),   "")

        messages = [
            {"role": "system",    "content": system},
            {"role": "user",      "content": human},
            {"role": "assistant", "content": gpt},
        ]
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )
        texts.append({"text": text})

    dataset = Dataset.from_list(texts)
    print(f"  Dataset: {len(dataset)} namuna yuklandi")
    print(f"  Namuna uzunligi: ~{len(texts[0]['text'].split())} so'z")
    return dataset


# ─────────────────────────────────────────────────────────────
#  MODEL YUKLAW (4-bit QLoRA)
# ─────────────────────────────────────────────────────────────
def load_model_and_tokenizer(model_name: str):
    print(f"  Model yuklanıwda: {model_name}")
    print(f"  VRAM: {torch.cuda.get_device_properties(0).total_memory/1024**3:.1f} GB")

    # 4-bit quantizatsiya
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True,
        padding_side="right",
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 6GB VRAM uchun max_memory chegarasi
    max_mem = {0: "5GiB", "cpu": "16GiB"}
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        max_memory=max_mem,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        attn_implementation="eager",   # sliding window xatosini tuzatish
    )

    # QLoRA uchun model tayyorlash
    model = prepare_model_for_kbit_training(model)

    used_vram = torch.cuda.memory_allocated() / 1024**3
    print(f"  Model yuklandi. VRAM islatildi: {used_vram:.1f} GB")
    return model, tokenizer


# ─────────────────────────────────────────────────────────────
#  LORA QOSHISH
# ─────────────────────────────────────────────────────────────
def add_lora(model):
    lora_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        target_modules=LORA_TARGETS,
        lora_dropout=LORA_DROPOUT,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    return model


# ─────────────────────────────────────────────────────────────
#  OQITIW
# ─────────────────────────────────────────────────────────────
def train(model, tokenizer, dataset, output_dir: str, epochs: int = 3):
    sft_config = SFTConfig(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        warmup_ratio=0.1,
        learning_rate=2e-4,
        bf16=True,
        fp16=False,
        logging_steps=1,
        optim="paged_adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        save_steps=30,
        save_total_limit=2,
        report_to="none",
        dataloader_pin_memory=False,
        remove_unused_columns=False,
        gradient_checkpointing=True,
        max_seq_length=MAX_SEQ_LEN,
        dataset_text_field="text",
        seed=42,
    )

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
        args=sft_config,
    )

    print("\n  Oqitiw baslandı...")
    stats = trainer.train()
    print(f"\n  Oqitiw tamamlandı!")
    print(f"  Jámi epoch: {epochs}")
    print(f"  Jámi loss:  {stats.metrics['train_loss']:.4f}")
    print(f"  Waqıt:      {stats.metrics['train_runtime']:.1f} sek")

    # LoRA saqlash
    trainer.model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"\n  Model saqlandı: {output_dir}/")
    return trainer


# ─────────────────────────────────────────────────────────────
#  INFERENCE (fine-tuned modeldan soraw)
# ─────────────────────────────────────────────────────────────
def ask(question: str, model, tokenizer, max_tokens: int = 512) -> str:
    messages = [
        {"role": "system",  "content": SYSTEM_PROMPT},
        {"role": "user",    "content": question},
    ]
    inputs = tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True, return_tensors="pt"
    ).to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            input_ids=inputs,
            max_new_tokens=max_tokens,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.eos_token_id,
        )

    response = tokenizer.decode(
        outputs[0][inputs.shape[-1]:], skip_special_tokens=True
    )
    return response.strip()


def run_inference_test(model, tokenizer):
    print("\n" + "=" * 55)
    print("  SINAW SORAWLAR")
    print("=" * 55)

    test_questions = [
        "2025-jılda JAÓ kórsetkishi qansha?",
        "Jumıssızlıq eń joqarı qaysı rayonda?",
        "Eksport kólemi nege beqarar?",
        "Investitsiya ósiminin sebepleri neler?",
    ]

    for q in test_questions:
        print(f"\nSORAW: {q}")
        answer = ask(q, model, tokenizer)
        print(f"JUWAP:\n{answer}")
        print("-" * 50)


# ─────────────────────────────────────────────────────────────
#  BASLAWSHI FUNKSIYA
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Qwen3-8B QLoRA Fine-tuning")
    parser.add_argument("--model",   default=MODEL_NAME,     help="HuggingFace model nomi")
    parser.add_argument("--data",    default=DATA_PATH,       help="Training data JSON")
    parser.add_argument("--output",  default=DEFAULT_OUTPUT,  help="Saqlash manzili")
    parser.add_argument("--epochs",  default=3,  type=int,   help="Epoch soni")
    parser.add_argument("--test",    action="store_true",     help="Faqat sinaw (oqitmasdan)")
    parser.add_argument("--lora-r",  default=LORA_R, type=int)
    args = parser.parse_args()

    print("=" * 55)
    print("  QWEN2.5-3B QARAQALPAQSHA FINETUNE")
    print("=" * 55)
    print(f"  GPU:    {torch.cuda.get_device_name(0)}")
    print(f"  VRAM:   {torch.cuda.get_device_properties(0).total_memory/1024**3:.1f} GB")
    print(f"  Model:  {args.model}")
    print(f"  Data:   {args.data}")
    print(f"  Output: {args.output}")
    print(f"  Epoch:  {args.epochs}")

    if not os.path.exists(args.data):
        print(f"\n  QATE: {args.data} fayl topilmadi!")
        print("  Avval training data yarating:")
        print("  python -u -c \"from src.training_data_generator import generate_all; generate_all()\"")
        sys.exit(1)

    os.makedirs(args.output, exist_ok=True)

    print("\n[1/4] Model va tokenizer yuklanıwda...")
    model, tokenizer = load_model_and_tokenizer(args.model)

    if args.test:
        print("\n[TEST REJIMI — oqitmasdan sinaw]")
        run_inference_test(model, tokenizer)
        return

    print("\n[2/4] LoRA qo'shilıwda...")
    model = add_lora(model)

    print("\n[3/4] Dataset tayyarlanıwda...")
    dataset = load_dataset(args.data, tokenizer)

    print("\n[4/4] Oqitiw baslanıwda...")
    trainer = train(model, tokenizer, dataset, args.output, args.epochs)

    print("\n[BONUS] Sinaw sorawlar...")
    run_inference_test(model, tokenizer)


if __name__ == "__main__":
    main()
