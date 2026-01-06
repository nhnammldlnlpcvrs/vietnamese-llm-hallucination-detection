# backend/utils/preprocessing.py
import re

def clean_text(text: str) -> str:
    """Làm sạch văn bản cơ bản"""
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def format_input_for_model(context: str, prompt: str, response: str) -> str:
    """
    Chuẩn hóa đầu vào cho PhoBERT.
    Quan trọng: Cần thêm token </s> để ngăn cách các phần.
    Format chuẩn thường dùng: Context </s> Prompt </s> Response
    """
    # Làm sạch từng phần
    c = clean_text(context)
    p = clean_text(prompt)
    r = clean_text(response)
    
    # Nối chuỗi với token ngăn cách của PhoBERT (</s>)
    # Lưu ý: Tokenizer sẽ tự thêm <s> ở đầu và </s> ở cuối cùng.
    # Chúng ta chỉ cần thêm cái ở giữa.
    combined_text = f"{c} </s> {p} </s> {r}"
    
    return combined_text