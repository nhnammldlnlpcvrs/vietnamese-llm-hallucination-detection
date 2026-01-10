# backend/utils/preprocessing.py
import re

def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def format_input_for_model(context: str, prompt: str, response: str) -> str:

    c = clean_text(context)
    p = clean_text(prompt)
    r = clean_text(response)
    
    combined_text = f"{c} </s> {p} </s> {r}"
    
    return combined_text