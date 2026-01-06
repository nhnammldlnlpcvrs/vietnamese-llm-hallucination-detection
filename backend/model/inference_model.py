# backend/model/inference_model.py
import os
import torch
import numpy as np
import lightgbm as lgb
from transformers import (
    AutoTokenizer, 
    AutoModel, 
    AutoModelForCausalLM, 
    AutoModelForSequenceClassification, 
    pipeline, 
    BitsAndBytesConfig
)
from sklearn.metrics.pairwise import cosine_similarity
import torch.nn.functional as F
from dotenv import load_dotenv
from huggingface_hub import login

# Load Env
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PHOBERT_FINETUNED_PATH = os.path.join(BASE_DIR, "models/phobert_finetuned_model")
LGBM_PATH = os.path.join(BASE_DIR, "models/lgbm_final_fold_0.txt")

NLI_MODEL_NAME = "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli"
NER_MODEL_NAME = "undertheseanlp/vietnamese-ner-v1.4.0a2"
VISTRAL_MODEL_NAME = "Viet-Mistral/Vistral-7B-Chat"

# Các model nhỏ chạy trên CPU để nhường GPU cho Vistral
SMALL_MODEL_DEVICE = torch.device("cpu") 

class HallucinationPipeline:
    def __init__(self):
        print("Initializing Pipeline (Resource Optimized)...")

        # 1. Login HF
        hf_token = os.getenv("HF_TOKEN")
        if hf_token:
            print("Found HF_TOKEN, logging in...")
            login(token=hf_token)
        
        try:
            # Load Small Models (ON CPU)
            print(f"- Loading PhoBERT (CPU)...")
            self.embed_tokenizer = AutoTokenizer.from_pretrained(PHOBERT_FINETUNED_PATH)
            self.embed_model = AutoModel.from_pretrained(PHOBERT_FINETUNED_PATH).to(SMALL_MODEL_DEVICE).eval()

            print(f"- Loading NLI (CPU)...")
            self.nli_tokenizer = AutoTokenizer.from_pretrained(NLI_MODEL_NAME)
            self.nli_model = AutoModelForSequenceClassification.from_pretrained(NLI_MODEL_NAME).to(SMALL_MODEL_DEVICE).eval()

            print(f"- Loading NER (CPU)...")
            try:
                self.ner_pipeline = pipeline("ner", model=NER_MODEL_NAME, tokenizer=NER_MODEL_NAME, 
                                             device=-1, aggregation_strategy="simple") # device=-1 là CPU
            except:
                fallback = "NlpHUST/ner-bert-base"
                self.ner_pipeline = pipeline("ner", model=fallback, tokenizer=fallback, 
                                             device=-1, aggregation_strategy="simple")

            # Load VISTRAL 7B (ON GPU with Offload support)
            print(f"- Loading Vistral 7B (GPU/Offload)...")
            
            # Cấu hình nén 4-bit và cho phép tràn bộ nhớ sang RAM (CPU Offload)
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                llm_int8_enable_fp32_cpu_offload=True  # <--- FIX CRASH: Cho phép dùng RAM nếu VRAM đầy
            )
            
            self.vistral_tokenizer = AutoTokenizer.from_pretrained(VISTRAL_MODEL_NAME)
            self.vistral_model = AutoModelForCausalLM.from_pretrained(
                VISTRAL_MODEL_NAME,
                quantization_config=bnb_config,
                device_map="auto",       # Tự động chia layer GPU/CPU
                offload_folder="offload" # Thư mục tạm để chứa weight nếu tràn RAM
            )
            print("- Vistral Loaded!")

            # Load LightGBM
            print(f"- Loading LightGBM...")
            self.lgbm_model = lgb.Booster(model_file=LGBM_PATH)
            
            self.labels = {0: "Extrinsic Hallucination", 1: "No Hallucination", 2: "Intrinsic Hallucination"}
            print("System Ready!")

        except Exception as e:
            print(f"Critical Error: {e}")
            raise e

    # FEATURE ENGINEERING
    def _extract_embeddings(self, text_list):
        # Chạy trên CPU
        inputs = self.embed_tokenizer(text_list, padding=True, truncation=True, max_length=256, return_tensors="pt").to(SMALL_MODEL_DEVICE)
        with torch.no_grad():
            outputs = self.embed_model(**inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1).cpu().numpy()
        return embeddings

    def _feat_engineer_simple(self, context, prompt, response):
        feats = []
        for text in [context, prompt, response]:
            s = str(text) if text else ""
            feats.append(len(s))
            feats.append(len(s.split()))
        return np.array([feats])

    def _get_entity_set(self, text):
        if not text: return set()
        try:
            entities = self.ner_pipeline(text)
            return {e['word'].replace(" ", "").lower() for e in entities}
        except: return set()

    def _get_ner_features(self, context, response):
        c_ents = self._get_entity_set(context)
        r_ents = self._get_entity_set(response)
        new_entity_count = len(r_ents - c_ents)
        union = len(c_ents.union(r_ents))
        overlap_ratio = len(c_ents.intersection(r_ents)) / union if union > 0 else 0.0
        return np.array([[new_entity_count, overlap_ratio]])

    def _get_nli_features(self, context, response):
        premise = context if context else "no context"
        hypothesis = response if response else "no response"
        # Chạy trên CPU
        inputs = self.nli_tokenizer(premise, hypothesis, padding=True, truncation=True, max_length=512, return_tensors="pt").to(SMALL_MODEL_DEVICE)
        with torch.no_grad():
            outputs = self.nli_model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1).cpu().numpy()
        return probs

    # VISTRAL PROBABILITY EXTRACTION
    def _get_vistral_probs(self, context, prompt, response):
        sys_msg = """Bạn là chuyên gia thẩm định độ trung thực của AI (Hallucination Judge).
        Nhiệm vụ: Dựa vào 'Context', hãy phân loại 'Response' vào đúng 1 trong 3 nhãn: 0, 1, hoặc 2.
        
        === ĐỊNH NGHĨA NHÃN (HÃY TUÂN THỦ NGHIÊM NGẶT) ===
        
        1. NO Hallucination (Nhãn 1):
           Phản hồi là "no" KHI VÀ CHỈ KHI đáp ứng đủ cả 3 điều kiện:
           - Nó hoàn toàn nhất quán và đúng sự thật với thông tin được cung cấp trong context.
           - Nó không chứa bất kỳ thông tin nào sai lệch hoặc không thể suy luận trực tiếp từ context.
           - Nó trả lời đúng dựa trên context.
           
        2. EXTRINSIC Hallucination (Nhãn 0) - Lỗi Ngoại Lai:
           Phản hồi là "EXTRINSIC" khi đáp ứng tối thiểu 1 trong các điều kiện:
           - Nó bổ sung thông tin KHÔNG CÓ trong context.
           - Thông tin bổ sung không thể suy luận được từ context.
           - Thông tin bổ sung có thể đúng trong thế giới thực nhưng nó không được cung cấp trong context.
           - Phản hồi vẫn cố gắng trả lời prompt nhưng lại đưa thêm chi tiết không có nguồn gốc từ context.
           
        3. INTRINSIC Hallucination (Nhãn 2) - Lỗi Nội Tại:
           Phản hồi là "INTRINSIC" khi đáp ứng tối thiểu 1 trong các điều kiện:
           - Nó mâu thuẫn trực tiếp hoặc bóp méo thông tin đã được cung cấp rõ ràng trong context.
           - Nội dung của ảo giác vẫn dựa trên các thực thể hoặc khái niệm có trong context nhưng thông tin về chúng bị thay đổi, sai lệch.
           - LLM tạo ra một câu trả lời sai lệch nhưng nghe có vẻ khá hợp lý (plausible) trong ngữ cảnh đó.
        """

        # Thêm hướng dẫn định dạng trả về để tránh Vistral nói dài dòng
        user_msg = f"""Dựa vào các định nghĩa trên, hãy phân loại trường hợp sau:

        Context: {context}
        Prompt: {prompt}
        Response: {response}

        Chỉ trả lời duy nhất một con số đại diện cho nhãn (0, 1 hoặc 2):"""

        messages = [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": user_msg}
        ]
        
        input_text = self.vistral_tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.vistral_tokenizer(input_text, return_tensors="pt").to(self.vistral_model.device)

        with torch.no_grad():
            outputs = self.vistral_model(**inputs)
            next_token_logits = outputs.logits[0, -1, :]
            
            id_0 = self.vistral_tokenizer.encode("0", add_special_tokens=False)[-1]
            id_1 = self.vistral_tokenizer.encode("1", add_special_tokens=False)[-1]
            id_2 = self.vistral_tokenizer.encode("2", add_special_tokens=False)[-1]

            score_0 = next_token_logits[id_0].item()
            score_1 = next_token_logits[id_1].item()
            score_2 = next_token_logits[id_2].item()
            
            # Softmax
            probs = F.softmax(torch.tensor([score_0, score_1, score_2]), dim=0).numpy()
            
            # Mapping output chuẩn cho LightGBM: [prob_extrinsic, prob_intrinsic, prob_no]
            # Lưu ý: id_0 tương ứng Extrinsic, id_2 tương ứng Intrinsic, id_1 tương ứng No
            return np.array([[probs[0], probs[2], probs[1]]])

    def predict(self, context, prompt, response):
        print("\n--- PROCESSING REQUEST (GUARDRAIL V3: EXTRINSIC HUNTER) ---")
        c, p, r = str(context).strip(), str(prompt).strip(), str(response).strip()
        
        # 1. Base Features (CPU)
        f_embed = self._extract_embeddings([f"{c} {p} {r}"])
        f_simple = self._feat_engineer_simple(c, p, r)
        
        c_emb = self._extract_embeddings([c])
        r_emb = self._extract_embeddings([r])
        f_sim = cosine_similarity(c_emb, r_emb)
        
        # 2. NLI Features (QUAN TRỌNG NHẤT)
        # DeBERTa output: [Entailment, Neutral, Contradiction]
        f_nli = self._get_nli_features(c, r)
        p_entail, p_neutral, p_contra = f_nli[0]
        
        print(f"- [NLI Debug] Entail: {p_entail:.4f} | Neu (Ext): {p_neutral:.4f} | Contra (Int): {p_contra:.4f}")

        # 3. NER Features
        f_ner = self._get_ner_features(c, r)
        new_entity_count = f_ner[0][0]
        overlap_ratio = f_ner[0][1]
        print(f"- [NER Debug] New Entities: {new_entity_count} | Overlap: {overlap_ratio:.2f}")

        # 4. Vistral (GPU)
        print("- Asking Vistral...")
        f_vistral = self._get_vistral_probs(c, p, r)
        print(f"- [Vistral Debug] Ext: {f_vistral[0][0]:.4f} | Int: {f_vistral[0][1]:.4f} | No: {f_vistral[0][2]:.4f}")

        # 5. Combine & Predict LightGBM
        x_final = np.hstack([f_embed, f_simple, f_sim, f_nli, f_ner, f_vistral])
        
        preds = self.lgbm_model.predict(x_final)
        
        # Kết quả gốc từ LightGBM
        class_id = np.argmax(preds[0])
        confidence = preds[0][class_id]
        original_label = self.labels.get(int(class_id), "Unknown")
        print(f"- [LightGBM Opinion] Label: {original_label} ({confidence:.4f})")

        # GUARDRAILS: QUYỀN PHỦ QUYẾT (VETO POWER)

        # --- RULE 1: BẮT INTRINSIC (Ưu tiên cao nhất) ---
        # Nếu NLI báo mâu thuẫn > 0.5, chắc chắn là sai.
        if p_contra > 0.5:
            print("GUARDRAIL: NLI Contradiction cao -> Force Intrinsic")
            return {"label": "Intrinsic Hallucination", "confidence": float(p_contra)}

        # --- RULE 2: BẮT EXTRINSIC DỰA TRÊN NLI NEUTRAL ---
        # Nếu Neutral cao (> 0.45) VÀ Entailment thấp (< 0.5)
        # Nghĩa là: Câu này không mâu thuẫn, nhưng cũng không có trong Context -> Bịa đặt.
        if p_neutral > 0.45 and p_entail < 0.5:
            print("GUARDRAIL: NLI Neutral cao (Thông tin ngoài lề) -> Force Extrinsic")
            return {"label": "Extrinsic Hallucination", "confidence": float(p_neutral)}

        # --- RULE 3: BẮT EXTRINSIC DỰA TRÊN NER (Siết chặt hơn) ---
        # Code cũ: >= 3 mới bắt.
        # Code mới: Chỉ cần >= 1 từ lạ, VÀ LightGBM đang định bảo "No Hallucination"
        if new_entity_count >= 1 and class_id == 1:
            # Logic phụ: Nếu Entailment cực cao (> 0.9) thì có thể NER bắt nhầm (ví dụ: Mỹ vs Hoa Kỳ).
            # Nhưng nếu Entailment < 0.9 thì đáng ngờ.
            if p_entail < 0.9:
                print("GUARDRAIL: Có thực thể lạ & Entailment không tuyệt đối -> Force Extrinsic")
                return {"label": "Extrinsic Hallucination", "confidence": 0.85}

        # --- RULE 4: VISTRAL VETO ---
        # Nếu Vistral vote cho Extrinsic quá cao (nó nhận ra kiến thức sai lệch mà NLI không thấy)
        if f_vistral[0][0] > 0.6:
             print("GUARDRAIL: Vistral vote Extrinsic rất cao -> Force Extrinsic")
             return {"label": "Extrinsic Hallucination", "confidence": float(f_vistral[0][0])}

        # --- RULE 5: SAFETY NET (Lưới an toàn cho Intrinsic) ---
        if p_contra > 0.35 and class_id == 1:
             print("Soft Warning: Có tín hiệu mâu thuẫn nhẹ. Trả về Intrinsic.")
             return {"label": "Intrinsic Hallucination", "confidence": float(p_contra)}

        # Nếu vượt qua tất cả cửa ải -> Tin tưởng LightGBM
        return {
            "label": original_label,
            "confidence": float(confidence)
        }

hallu_model = HallucinationPipeline()