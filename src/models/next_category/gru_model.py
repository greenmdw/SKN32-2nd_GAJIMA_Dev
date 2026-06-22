"""Category-GRU 모델 정의."""
import torch
from torch import nn


class CategoryGRU(nn.Module):
    def __init__(
        self,
        *,
        vocab_size,
        numeric_size=6,
        embedding_dim=64,
        numeric_dim=16,
        hidden_size=128,
        num_layers=1,
        dropout=0.2,
    ):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.numeric_projection = nn.Sequential(
            nn.Linear(numeric_size, numeric_dim),
            nn.ReLU(),
        )
        self.gru = nn.GRU(
            embedding_dim + numeric_dim,
            hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.dropout = nn.Dropout(dropout)
        self.output = nn.Linear(hidden_size, vocab_size)

    def forward(self, x_cat, x_num, lengths):
        category = self.embedding(x_cat)
        numeric = self.numeric_projection(x_num)
        sequence = torch.cat([category, numeric], dim=-1)
        packed = nn.utils.rnn.pack_padded_sequence(
            sequence,
            lengths.cpu(),
            batch_first=True,
            enforce_sorted=False,
        )
        _, hidden = self.gru(packed)
        logits = self.output(self.dropout(hidden[-1]))
        # padding class는 추천 대상이 아니다.
        logits[:, 0] = torch.finfo(logits.dtype).min
        return logits

