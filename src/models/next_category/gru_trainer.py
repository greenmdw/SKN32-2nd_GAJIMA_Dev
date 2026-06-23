"""Category-GRU 학습 및 평가.

실행:
  python -m src.models.next_category.gru_trainer
"""
import argparse
import json
import random
import shutil
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from src.models.next_category.gru_model import CategoryGRU

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET = ROOT / "data" / "processed" / "next_category" / "category_gru_v1.npz"
MODEL_DIR = ROOT / "models" / "next_category" / "gru"
EVAL_DIR = ROOT / "data" / "processed" / "evaluation" / "next_category" / "gru"
SEED = 42


class SequenceDataset(Dataset):
    def __init__(self, archive, split):
        self.x_cat = archive[f"X_cat_{split}"]
        self.x_num = archive[f"X_num_{split}"]
        self.lengths = archive[f"lengths_{split}"]
        self.y = archive[f"y_{split}"]
        self.user_id = archive[f"user_id_{split}"]

    def __len__(self):
        return len(self.y)

    def __getitem__(self, index):
        return (
            torch.from_numpy(self.x_cat[index].astype(np.int64, copy=False)),
            torch.from_numpy(self.x_num[index]),
            torch.tensor(int(self.lengths[index]), dtype=torch.long),
            torch.tensor(int(self.y[index]), dtype=torch.long),
            torch.tensor(int(self.user_id[index]), dtype=torch.long),
        )


def ranking_metrics(y_true, logits, top_k=10):
    k = min(top_k, logits.shape[1])
    top = torch.topk(logits, k=k, dim=1).indices
    target = y_true[:, None]
    match = top.eq(target)
    top1 = match[:, :1].any(dim=1).float().mean().item()
    hit4 = match[:, : min(4, k)].any(dim=1).float().mean().item()
    hit10 = match.any(dim=1).float().mean().item()
    positions = torch.arange(1, k + 1, device=logits.device, dtype=torch.float32)
    reciprocal = (match.float() / positions).max(dim=1).values.mean().item()
    return top1, hit4, hit10, reciprocal, top


@torch.no_grad()
def evaluate(model, loader, device, criterion, collect=False):
    model.eval()
    total_loss = total_n = 0
    sums = np.zeros(4, dtype=np.float64)
    predictions = []
    seen_categories = set()
    started = time.perf_counter()
    for x_cat, x_num, lengths, y, uid in loader:
        x_cat, x_num, lengths, y = (
            x_cat.to(device),
            x_num.to(device),
            lengths.to(device),
            y.to(device),
        )
        logits = model(x_cat, x_num, lengths)
        loss = criterion(logits, y)
        n = len(y)
        total_loss += loss.item() * n
        total_n += n
        values = ranking_metrics(y, logits)
        sums += np.asarray(values[:4]) * n
        top = values[4]
        seen_categories.update(top.detach().cpu().numpy().ravel().tolist())
        if collect:
            probability = torch.softmax(logits, dim=1)
            top_score, top_index = torch.topk(probability, k=min(10, probability.shape[1]), dim=1)
            predictions.append(
                (
                    uid.numpy(),
                    y.cpu().numpy(),
                    top_index.cpu().numpy(),
                    top_score.cpu().numpy(),
                )
            )
    elapsed = time.perf_counter() - started
    result = {
        "loss": total_loss / total_n,
        "top1": sums[0] / total_n,
        "hit_at_4": sums[1] / total_n,
        "hit_at_10": sums[2] / total_n,
        "mrr_at_10": sums[3] / total_n,
        "coverage_at_10": len(seen_categories),
        "samples": total_n,
        "inference_ms_per_sample": elapsed * 1000 / total_n,
    }
    return result, predictions


def last_category_baseline(train_dataset, test_dataset, vocab_size):
    """Last category first, then fill remaining slots with train popularity."""
    y = test_dataset.y
    last = np.asarray(
        [test_dataset.x_cat[i, test_dataset.lengths[i] - 1] for i in range(len(y))]
    )
    popularity = np.argsort(
        -np.bincount(train_dataset.y, minlength=vocab_size), kind="stable"
    )
    popularity = popularity[popularity >= 2]
    top10 = np.empty((len(y), 10), dtype=np.int64)
    for index, last_category in enumerate(last):
        fallback = popularity[popularity != last_category][:9]
        top10[index, 0] = last_category
        top10[index, 1:] = fallback
    match = top10 == y[:, None]
    reciprocal = np.where(match, 1.0 / np.arange(1, 11), 0.0).max(axis=1)
    return {
        "name": "last_category_plus_train_popularity",
        "top1": float(match[:, :1].any(axis=1).mean()),
        "hit_at_4": float(match[:, :4].any(axis=1).mean()),
        "hit_at_10": float(match.any(axis=1).mean()),
        "mrr_at_10": float(reciprocal.mean()),
        "samples": int(len(y)),
        "coverage_at_10": int(len(np.unique(top10))),
    }


def train(args):
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    archive = np.load(args.dataset, mmap_mode="r")
    train_ds = SequenceDataset(archive, "train")
    val_ds = SequenceDataset(archive, "val")
    test_ds = SequenceDataset(archive, "test")
    vocab_size = int(max(train_ds.y.max(), val_ds.y.max(), test_ds.y.max())) + 1

    loaders = {
        "train": DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0),
        "val": DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0),
        "test": DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=0),
    }
    model = CategoryGRU(
        vocab_size=vocab_size,
        embedding_dim=args.embedding_dim,
        numeric_dim=args.numeric_dim,
        hidden_size=args.hidden_size,
        num_layers=args.num_layers,
        dropout=args.dropout,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    criterion = nn.CrossEntropyLoss()
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    history = []
    best_hit4 = -1.0
    best_epoch = 0
    stale = 0

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = total_n = 0
        started = time.perf_counter()
        for x_cat, x_num, lengths, y, _ in loaders["train"]:
            x_cat, x_num, lengths, y = (
                x_cat.to(device),
                x_num.to(device),
                lengths.to(device),
                y.to(device),
            )
            optimizer.zero_grad(set_to_none=True)
            logits = model(x_cat, x_num, lengths)
            loss = criterion(logits, y)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            total_loss += loss.item() * len(y)
            total_n += len(y)
        val_metrics, _ = evaluate(model, loaders["val"], device, criterion)
        row = {
            "epoch": epoch,
            "train_loss": total_loss / total_n,
            "val_loss": val_metrics["loss"],
            "val_top1": val_metrics["top1"],
            "val_hit_at_4": val_metrics["hit_at_4"],
            "val_hit_at_10": val_metrics["hit_at_10"],
            "val_mrr_at_10": val_metrics["mrr_at_10"],
            "seconds": time.perf_counter() - started,
        }
        history.append(row)
        print(json.dumps(row), flush=True)
        if val_metrics["hit_at_4"] > best_hit4 + 1e-6:
            best_hit4 = val_metrics["hit_at_4"]
            best_epoch = epoch
            stale = 0
            torch.save(model.state_dict(), MODEL_DIR / "model.pt")
        else:
            stale += 1
            if stale >= args.patience:
                break

    model.load_state_dict(torch.load(MODEL_DIR / "model.pt", map_location=device, weights_only=True))
    test_metrics, predictions = evaluate(model, loaders["test"], device, criterion, collect=True)
    baseline = last_category_baseline(train_ds, test_ds, vocab_size)
    metrics = {
        "model_name": "CategoryGRU_v1",
        "task": "next_category",
        "device": str(device),
        "vocab_size": vocab_size,
        "n_train": len(train_ds),
        "n_val": len(val_ds),
        "n_test": len(test_ds),
        "best_epoch": best_epoch,
        "selection_metric": "val_hit_at_4",
        "test": test_metrics,
        "last_category_baseline": baseline,
    }
    (EVAL_DIR / "metrics_summary.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (EVAL_DIR / "training_history.json").write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    uid = np.concatenate([p[0] for p in predictions])
    y_true = np.concatenate([p[1] for p in predictions])
    top_index = np.concatenate([p[2] for p in predictions])
    top_score = np.concatenate([p[3] for p in predictions])
    frame = pd.DataFrame({"user_id": uid, "y_true": y_true})
    for index in range(top_index.shape[1]):
        frame[f"top{index + 1}_category_index"] = top_index[:, index]
        frame[f"top{index + 1}_score"] = top_score[:, index]
    frame.to_parquet(EVAL_DIR / "eval_predictions.parquet", index=False)

    config = {
        "model_name": "CategoryGRU_v1",
        "dataset": str(Path(args.dataset).resolve().relative_to(ROOT)).replace("\\", "/"),
        "seed": SEED,
        "best_epoch": best_epoch,
        "selection_metric": "val_hit_at_4",
        "sequence_length": int(train_ds.x_cat.shape[1]),
        "hyperparameters": {
            "embedding_dim": args.embedding_dim,
            "numeric_dim": args.numeric_dim,
            "hidden_size": args.hidden_size,
            "num_layers": args.num_layers,
            "dropout": args.dropout,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "weight_decay": args.weight_decay,
            "epochs_max": args.epochs,
            "patience": args.patience,
        },
    }
    (MODEL_DIR / "model_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    source_mapping = Path(args.dataset).with_name("category_index_map.json")
    if source_mapping.exists():
        shutil.copy2(source_mapping, MODEL_DIR / "category_index_map.json")
    feature_schema = {
        "task": "next_category",
        "sequence_length": 10,
        "minimum_events_for_training_window": 2,
        "inference_minimum_events": 1,
        "categorical_feature": {
            "name": "category_id",
            "padding_index": 0,
            "unknown_index": 1,
            "mapping_file": "category_index_map.json",
        },
        "numeric_features_in_order": [
            "is_view",
            "is_cart",
            "is_remove_from_cart",
            "is_purchase",
            "log1p_gap_seconds",
            "log1p_price",
        ],
        "supported_event_types": ["view", "cart", "remove_from_cart", "purchase"],
        "padding_side": "right",
        "truncation_side": "left_keep_recent",
    }
    (MODEL_DIR / "feature_schema.json").write_text(
        json.dumps(feature_schema, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Train Category-GRU")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--patience", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--embedding-dim", type=int, default=64)
    parser.add_argument("--numeric-dim", type=int, default=16)
    parser.add_argument("--hidden-size", type=int, default=128)
    parser.add_argument("--num-layers", type=int, default=1)
    parser.add_argument("--dropout", type=float, default=0.2)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()
