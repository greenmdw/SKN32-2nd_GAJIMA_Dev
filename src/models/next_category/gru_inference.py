"""Realtime inference helper for the trained next-category GRU."""
import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import torch

from src.models.next_category.gru_model import CategoryGRU

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MODEL_DIR = ROOT / "models" / "next_category" / "gru"
EVENT_INDEX = {"view": 0, "cart": 1, "remove_from_cart": 2, "purchase": 3}


class NextCategoryPredictor:
    """Load the model once and return ranked category IDs for session events."""

    def __init__(self, model_dir=DEFAULT_MODEL_DIR, device=None):
        self.model_dir = Path(model_dir)
        self.config = json.loads(
            (self.model_dir / "model_config.json").read_text(encoding="utf-8")
        )
        mapping = json.loads(
            (self.model_dir / "category_index_map.json").read_text(encoding="utf-8")
        )
        self.index_to_category = mapping["index_to_category_id"]
        self.category_to_index = {
            int(category_id): int(index)
            for index, category_id in self.index_to_category.items()
            if int(index) >= 2
        }
        self.unknown_index = int(mapping["unknown_index"])
        self.seq_len = int(self.config.get("sequence_length", 10))
        self.device = torch.device(
            device or ("cuda" if torch.cuda.is_available() else "cpu")
        )
        params = self.config["hyperparameters"]
        self.model = CategoryGRU(
            vocab_size=int(mapping["vocab_size"]),
            embedding_dim=int(params["embedding_dim"]),
            numeric_dim=int(params["numeric_dim"]),
            hidden_size=int(params["hidden_size"]),
            num_layers=int(params["num_layers"]),
            dropout=float(params["dropout"]),
        ).to(self.device)
        state = torch.load(
            self.model_dir / "model.pt", map_location=self.device, weights_only=True
        )
        self.model.load_state_dict(state)
        self.model.eval()

    @staticmethod
    def _timestamp(value):
        if isinstance(value, datetime):
            return value.timestamp()
        text = str(value).strip().replace(" UTC", "+00:00").replace("Z", "+00:00")
        return datetime.fromisoformat(text).timestamp()

    def _encode(self, events):
        if not events:
            raise ValueError("At least one session event is required")
        recent = events[-self.seq_len :]
        x_cat = np.zeros((1, self.seq_len), dtype=np.int64)
        x_num = np.zeros((1, self.seq_len, 6), dtype=np.float32)
        previous_time = None
        for position, event in enumerate(recent):
            event_type = str(event["event_type"])
            if event_type not in EVENT_INDEX:
                raise ValueError(f"Unsupported event_type: {event_type}")
            category_id = int(event["category_id"])
            timestamp = self._timestamp(event["event_time"])
            gap = max(0.0, timestamp - previous_time) if previous_time is not None else 0.0
            price = max(0.0, float(event.get("price", 0.0)))
            x_cat[0, position] = self.category_to_index.get(
                category_id, self.unknown_index
            )
            x_num[0, position, EVENT_INDEX[event_type]] = 1.0
            x_num[0, position, 4] = math.log1p(gap)
            x_num[0, position, 5] = math.log1p(price)
            previous_time = timestamp
        lengths = np.asarray([len(recent)], dtype=np.int64)
        return x_cat, x_num, lengths

    @torch.inference_mode()
    def predict(self, events, top_k=4):
        x_cat, x_num, lengths = self._encode(events)
        logits = self.model(
            torch.from_numpy(x_cat).to(self.device),
            torch.from_numpy(x_num).to(self.device),
            torch.from_numpy(lengths).to(self.device),
        )
        probabilities = torch.softmax(logits, dim=1)
        # Padding and unknown categories are internal tokens, not recommendations.
        probabilities[:, :2] = 0
        scores, indices = torch.topk(probabilities, k=min(top_k, logits.shape[1] - 2), dim=1)
        return [
            {
                "category_id": int(self.index_to_category[str(int(index))]),
                "score": float(score),
            }
            for index, score in zip(indices[0].cpu(), scores[0].cpu())
        ]
