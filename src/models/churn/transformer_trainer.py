"""Transformer 이탈 예측 학습기 (19-3: model_key=transformer, model_type=sequence).

입력: processed_5m/{train,test}_seq_DL_opt.npz  (raw, seq_len=4, n_features=3)
산출: models/churn/transformer/[runs/{tag}/]model.pt + 평가 9종 + manifest + 리더보드
17-5-1 결론 반영: DL 최적 = 정규화 없음(raw) + pos_weight 없음.
"""
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, TensorDataset

from src.common.data import DATA_DIR, SEQ_FEATURES, load_sequence
from src.common.evaluation import evaluate_and_save
from src.common.manifest import write_manifest
from src.common.registry import artifact_rel_path, log_run, resolve_dirs

MODEL_KEY = "transformer"
MODEL_NAME = "Transformer_Churn_v2"
MODEL_TYPE = "sequence"
SEED = 42
DEFAULTS = {
    "epochs": 30,
    "batch_size": 128,
    "lr": 5e-4,
    "weight_decay": 1e-4,
    "patience": 5,
    "d_model": 32,
    "nhead": 4,
    "num_layers": 2,
    "dropout": 0.2,
}


class ChurnTransformer(nn.Module):
    def __init__(self, n_features=3, d_model=32, nhead=4, num_layers=2, dropout=0.2, seq_len=4):
        super().__init__()
        self.input_proj = nn.Linear(n_features, d_model)
        self.pos = nn.Parameter(torch.zeros(1, seq_len, d_model))
        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=64,
            dropout=dropout, batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=num_layers)
        self.head = nn.Sequential(nn.LayerNorm(d_model), nn.Linear(d_model, 1))

    def forward(self, x):
        h = self.input_proj(x) + self.pos
        h = self.encoder(h)
        return self.head(h.mean(dim=1)).squeeze(-1)


def _predict_scores(model, X, device, batch_size=2048):
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(X), batch_size):
            xb = torch.from_numpy(X[i : i + batch_size]).to(device)
            out.append(torch.sigmoid(model(xb)).cpu().numpy())
    return np.concatenate(out)


def train(run_tag=None, **overrides):
    hp = dict(DEFAULTS)
    hp.update(overrides)
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[{MODEL_KEY}] device={device}")

    X_full, y_full, _ = load_sequence(DATA_DIR / "train_seq_DL_opt.npz")
    X_te, y_te, uid_te = load_sequence(DATA_DIR / "test_seq_DL_opt.npz")
    seq_len, n_features = X_full.shape[1], X_full.shape[2]
    X_tr, X_val, y_tr, y_val = train_test_split(
        X_full, y_full, test_size=0.15, stratify=y_full, random_state=SEED
    )

    train_loader = DataLoader(
        TensorDataset(torch.from_numpy(X_tr), torch.from_numpy(y_tr.astype("float32"))),
        batch_size=hp["batch_size"], shuffle=True,
    )
    val_loader = DataLoader(
        TensorDataset(torch.from_numpy(X_val), torch.from_numpy(y_val.astype("float32"))),
        batch_size=hp["batch_size"], shuffle=False,
    )

    model = ChurnTransformer(
        n_features=n_features, seq_len=seq_len,
        d_model=hp["d_model"], nhead=hp["nhead"],
        num_layers=hp["num_layers"], dropout=hp["dropout"],
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=hp["lr"], weight_decay=hp["weight_decay"])
    criterion = nn.BCEWithLogitsLoss()  # 17-5-1: DL 최적은 pos_weight 없음

    history = {"epoch": [], "train_loss": [], "val_loss": []}
    best_val, best_state, bad = float("inf"), None, 0
    for epoch in range(1, hp["epochs"] + 1):
        model.train()
        tr_loss = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()
            tr_loss += loss.item() * len(xb)
        tr_loss /= len(train_loader.dataset)

        model.eval()
        va_loss = 0.0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                va_loss += criterion(model(xb), yb).item() * len(xb)
        va_loss /= len(val_loader.dataset)

        history["epoch"].append(epoch)
        history["train_loss"].append(round(tr_loss, 6))
        history["val_loss"].append(round(va_loss, 6))

        if va_loss < best_val:
            best_val = va_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            bad = 0
        else:
            bad += 1
            if bad >= hp["patience"]:
                print(f"[{MODEL_KEY}] early stopping at epoch {epoch}")
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    y_score = _predict_scores(model, X_te, device)

    artifact_dir, eval_dir = resolve_dirs(MODEL_KEY, run_tag)
    torch.save(model.state_dict(), artifact_dir / "model.pt")

    base_auc = roc_auc_score(y_te, y_score)
    rng = np.random.default_rng(SEED)
    attrib = []
    for c in range(n_features):
        Xp = X_te.copy()
        Xp[:, :, c] = Xp[rng.permutation(len(Xp)), :, c]
        attrib.append(float(base_auc - roc_auc_score(y_te, _predict_scores(model, Xp, device))))
    order = np.argsort(-np.array(attrib))
    shap_summary = {
        "feature": [SEQ_FEATURES[i] for i in order],
        "mean_abs_shap": [attrib[i] for i in order],
        "rank": list(range(1, n_features + 1)),
        "note": "permutation AUC-drop attribution (Transformer); SHAP 대체",
    }

    metrics = evaluate_and_save(
        eval_dir,
        model_name=MODEL_NAME,
        model_key=MODEL_KEY,
        model_type=MODEL_TYPE,
        user_id=uid_te,
        y_true=y_te,
        y_score=y_score,
        n_train=len(y_tr),
        training_history=history,
        shap_summary=shap_summary,
    )

    write_manifest(
        eval_dir,
        model_name=MODEL_NAME,
        model_key=MODEL_KEY,
        model_type=MODEL_TYPE,
        input_train="processed_5m/train_seq_DL_opt.npz",
        input_test="processed_5m/test_seq_DL_opt.npz",
        artifact_path=artifact_rel_path(MODEL_KEY, run_tag, "model.pt"),
        metrics=metrics,
        preprocessing_config={
            "input_format": "npz",
            "scale": "none",
            "sequence_key": "X",
            "seq_len": int(seq_len),
            "n_features": int(n_features),
            "target_key": "churn",
            "id_key": "user_id",
            **hp,
        },
    )
    log_run(MODEL_KEY, run_tag, hp, metrics)
    print(f"[{MODEL_KEY}] run={run_tag or 'baseline'} hp={hp} "
          f"ROC-AUC={metrics['roc_auc']:.4f} PR-AUC={metrics['pr_auc']:.4f} F1={metrics['best_f1']:.4f}")
    return metrics


if __name__ == "__main__":
    train()
