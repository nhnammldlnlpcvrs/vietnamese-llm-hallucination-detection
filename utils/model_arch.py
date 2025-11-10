# model_arch.py
import torch
import torch.nn as nn
from transformers import AutoModel

def mean_pool(last_hidden_state, attention_mask):
    """
    Mean pooling over token embeddings using attention mask.
    """
    mask = attention_mask.unsqueeze(-1).float()
    return (last_hidden_state * mask).sum(1) / mask.sum(1).clamp(min=1e-9)

class CafeBERTNLIClassifier(nn.Module):
    """
    NLI classifier built on top of CafeBERT base model.
    """

    def __init__(self, num_labels=3):
        """
        Args:
            num_labels (int): Number of classes for classification
        """
        super().__init__()
        self.base = AutoModel.from_pretrained("uitnlp/CafeBERT")
        self.dropout = nn.Dropout(0.3)
        self.fc = nn.Linear(self.base.config.hidden_size, num_labels)

    def forward(self, input_ids, attention_mask, token_type_ids=None):
        """
        Forward pass
        """
        outputs = self.base(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids)
        x = mean_pool(outputs.last_hidden_state, attention_mask)
        x = self.dropout(x)
        return self.fc(x)