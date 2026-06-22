"""data2 clean 이벤트에서 Category-GRU용 시간 분할 데이터셋을 생성한다.

입력은 전역 시간순 CSV이므로 세션별 최근 이벤트 deque만 유지하면 외부 정렬 없이
다음 카테고리 window를 스트리밍 생성할 수 있다.

분할:
  train = 2019-10 ~ 2019-12
  val   = 2020-01
  test  = 2020-02

출력:
  data/processed/next_category/category_gru_v1.npz
  data/processed/next_category/category_index_map.json
  data/processed/next_category/category_gru_v1_meta.json
"""
import argparse
import csv
import hashlib
import heapq
import json
import math
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = ROOT / "data2" / "clean" / "all_months_clean_core.csv"
DEFAULT_TEST_INPUT = ROOT / "data2" / "2020-Feb.csv"
DEFAULT_OUT = ROOT / "data" / "processed" / "next_category"
EVENT_INDEX = {"view": 0, "cart": 1, "remove_from_cart": 2, "purchase": 3}
SPLIT_INDEX = {"train": 0, "val": 1, "test": 2}


def _month_split(event_time):
    month = event_time[:7]
    if month in {"2019-10", "2019-11", "2019-12"}:
        return "train"
    if month == "2020-01":
        return "val"
    if month == "2020-02":
        return "test"
    return None


def _fast_epoch_seconds(value, day_cache):
    """고정 형식 YYYY-MM-DD HH:MM:SS를 빠르게 epoch seconds로 변환."""
    day = value[:10]
    base = day_cache.get(day)
    if base is None:
        base = int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
        day_cache[day] = base
    return base + int(value[11:13]) * 3600 + int(value[14:16]) * 60 + int(value[17:19])


class Reservoir:
    def __init__(self, capacity, seq_len, rng):
        self.capacity = capacity
        self.seq_len = seq_len
        self.rng = rng
        self.seen = 0
        self.size = 0
        self.x_cat = np.zeros((capacity, seq_len), dtype=np.int32)
        self.x_num = np.zeros((capacity, seq_len, 6), dtype=np.float32)
        self.lengths = np.zeros(capacity, dtype=np.int16)
        self.y = np.zeros(capacity, dtype=np.int32)
        self.user_id = np.zeros(capacity, dtype=np.int64)

    def add(self, cats, nums, target, user_id):
        self.seen += 1
        if self.size < self.capacity:
            index = self.size
            self.size += 1
        else:
            index = int(self.rng.integers(0, self.seen))
            if index >= self.capacity:
                return
        length = min(len(cats), self.seq_len)
        self.x_cat[index].fill(0)
        self.x_num[index].fill(0)
        self.x_cat[index, :length] = cats[-length:]
        self.x_num[index, :length] = nums[-length:]
        self.lengths[index] = length
        self.y[index] = target
        self.user_id[index] = user_id

    def arrays(self):
        n = self.size
        return {
            "X_cat": self.x_cat[:n],
            "X_num": self.x_num[:n],
            "lengths": self.lengths[:n],
            "y": self.y[:n],
            "user_id": self.user_id[:n],
        }


def build_dataset(
    input_path,
    output_dir,
    *,
    test_input_path=DEFAULT_TEST_INPUT,
    seq_len=10,
    min_history=2,
    max_windows_per_session=20,
    train_samples=300_000,
    val_samples=75_000,
    test_samples=100_000,
    seed=42,
):
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    reservoirs = {
        "train": Reservoir(train_samples, seq_len, rng),
        "val": Reservoir(val_samples, seq_len, rng),
        "test": Reservoir(test_samples, seq_len, rng),
    }

    # 0=padding, 1=unknown. 실제 카테고리는 train에서 처음 등장한 순서로 2부터 부여.
    cat_to_index = {}
    index_to_cat = {"0": None, "1": "UNK"}
    sessions = {}
    expiry_heap = []
    day_cache = {}
    stats = {
        "rows_read": 0,
        "rows_skipped": 0,
        "unknown_target": {"val": 0, "test": 0},
        "expired_sessions": 0,
    }
    session_ttl_seconds = 24 * 3600

    with input_path.open("r", encoding="utf-8-sig", newline="", buffering=1024 * 1024) as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            stats["rows_read"] += 1
            event_time = row["event_time"]
            split = _month_split(event_time)
            event_type = row["event_type"]
            session_id = row["user_session"]
            if split is None or event_type not in EVENT_INDEX or not session_id:
                stats["rows_skipped"] += 1
                continue
            try:
                user_id = int(row["user_id"])
                category_id = int(row["category_id"])
                price = max(0.0, float(row["price"]))
                timestamp = _fast_epoch_seconds(event_time, day_cache)
            except (TypeError, ValueError):
                stats["rows_skipped"] += 1
                continue

            # 오래 끝난 세션을 제거해 메모리 사용을 제한한다.
            if stats["rows_read"] % 100_000 == 0:
                cutoff = timestamp - session_ttl_seconds
                while expiry_heap and expiry_heap[0][0] < cutoff:
                    old_ts, old_session = heapq.heappop(expiry_heap)
                    state = sessions.get(old_session)
                    if state is not None and state["last_ts"] == old_ts:
                        del sessions[old_session]
                        stats["expired_sessions"] += 1
                print(
                    f"rows={stats['rows_read']:,} active_sessions={len(sessions):,} "
                    f"samples=" + ",".join(f"{k}:{v.size:,}" for k, v in reservoirs.items()),
                    flush=True,
                )

            if split == "train":
                encoded_category = cat_to_index.get(category_id)
                if encoded_category is None:
                    encoded_category = len(cat_to_index) + 2
                    cat_to_index[category_id] = encoded_category
                    index_to_cat[str(encoded_category)] = category_id
            else:
                encoded_category = cat_to_index.get(category_id, 1)

            state = sessions.get(session_id)
            if state is None:
                state = {
                    "cats": deque(maxlen=seq_len),
                    "nums": deque(maxlen=seq_len),
                    "last_ts": timestamp,
                    "windows": 0,
                    "split": split,
                    "user_id": user_id,
                }
                sessions[session_id] = state
            elif state["split"] != split:
                # 월 경계를 넘는 비정상/장기 세션은 새 세션처럼 취급한다.
                state["cats"].clear()
                state["nums"].clear()
                state["windows"] = 0
                state["split"] = split

            if (
                len(state["cats"]) >= min_history
                and state["windows"] < max_windows_per_session
            ):
                if encoded_category != 1:
                    reservoirs[split].add(
                        list(state["cats"]),
                        list(state["nums"]),
                        encoded_category,
                        user_id,
                    )
                    state["windows"] += 1
                elif split != "train":
                    stats["unknown_target"][split] += 1

            gap = max(0, timestamp - state["last_ts"]) if state["cats"] else 0
            numeric = np.zeros(6, dtype=np.float32)
            numeric[EVENT_INDEX[event_type]] = 1.0
            numeric[4] = math.log1p(gap)
            numeric[5] = math.log1p(price)
            state["cats"].append(encoded_category)
            state["nums"].append(numeric)
            state["last_ts"] = timestamp
            state["user_id"] = user_id
            heapq.heappush(expiry_heap, (timestamp, session_id))

    # clean 통합본이 Jan까지만 존재하는 경우 원본 Feb를 동일 규칙으로 OOT test 처리한다.
    test_input_path = Path(test_input_path) if test_input_path else None
    if reservoirs["test"].seen == 0 and test_input_path and test_input_path.exists():
        sessions.clear()
        expiry_heap.clear()
        external_rows = external_skipped = external_unknown = 0
        with test_input_path.open("r", encoding="utf-8-sig", newline="", buffering=1024 * 1024) as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                external_rows += 1
                event_type = row["event_type"]
                session_id = row["user_session"]
                if event_type not in EVENT_INDEX or not session_id:
                    external_skipped += 1
                    continue
                try:
                    user_id = int(row["user_id"])
                    category_id = int(row["category_id"])
                    price = max(0.0, float(row["price"]))
                    timestamp = _fast_epoch_seconds(row["event_time"], day_cache)
                except (TypeError, ValueError):
                    external_skipped += 1
                    continue

                if external_rows % 100_000 == 0:
                    cutoff = timestamp - session_ttl_seconds
                    while expiry_heap and expiry_heap[0][0] < cutoff:
                        old_ts, old_session = heapq.heappop(expiry_heap)
                        state = sessions.get(old_session)
                        if state is not None and state["last_ts"] == old_ts:
                            del sessions[old_session]
                    print(
                        f"external_test_rows={external_rows:,} active_sessions={len(sessions):,} "
                        f"samples=test:{reservoirs['test'].size:,}",
                        flush=True,
                    )

                encoded_category = cat_to_index.get(category_id, 1)
                state = sessions.get(session_id)
                if state is None:
                    state = {
                        "cats": deque(maxlen=seq_len),
                        "nums": deque(maxlen=seq_len),
                        "last_ts": timestamp,
                        "windows": 0,
                        "user_id": user_id,
                    }
                    sessions[session_id] = state

                if len(state["cats"]) >= min_history and state["windows"] < max_windows_per_session:
                    if encoded_category != 1:
                        reservoirs["test"].add(
                            list(state["cats"]),
                            list(state["nums"]),
                            encoded_category,
                            user_id,
                        )
                        state["windows"] += 1
                    else:
                        external_unknown += 1

                gap = max(0, timestamp - state["last_ts"]) if state["cats"] else 0
                numeric = np.zeros(6, dtype=np.float32)
                numeric[EVENT_INDEX[event_type]] = 1.0
                numeric[4] = math.log1p(gap)
                numeric[5] = math.log1p(price)
                state["cats"].append(encoded_category)
                state["nums"].append(numeric)
                state["last_ts"] = timestamp
                heapq.heappush(expiry_heap, (timestamp, session_id))
        stats["external_test"] = {
            "source": str(test_input_path.relative_to(ROOT)).replace("\\", "/"),
            "rows_read": external_rows,
            "rows_skipped": external_skipped,
            "unknown_target": external_unknown,
        }

    split_arrays = {name: reservoir.arrays() for name, reservoir in reservoirs.items()}
    payload = {}
    for split, arrays in split_arrays.items():
        for key, value in arrays.items():
            payload[f"{key}_{split}"] = value
    dataset_path = output_dir / "category_gru_v1.npz"
    np.savez_compressed(dataset_path, **payload)

    map_path = output_dir / "category_index_map.json"
    map_path.write_text(
        json.dumps(
            {
                "padding_index": 0,
                "unknown_index": 1,
                "n_categories_train": len(cat_to_index),
                "vocab_size": len(cat_to_index) + 2,
                "index_to_category_id": index_to_cat,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    meta = {
        "source": str(input_path.relative_to(ROOT)).replace("\\", "/"),
        "dataset": str(dataset_path.relative_to(ROOT)).replace("\\", "/"),
        "split": {
            "train": "2019-10~2019-12",
            "val": "2020-01",
            "test": "2020-02",
        },
        "seq_len": seq_len,
        "min_history": min_history,
        "max_windows_per_session": max_windows_per_session,
        "numeric_features": [
            "is_view",
            "is_cart",
            "is_remove",
            "is_purchase",
            "gap_log",
            "price_log",
        ],
        "sample_capacity": {
            "train": train_samples,
            "val": val_samples,
            "test": test_samples,
        },
        "eligible_windows_seen": {
            name: reservoir.seen for name, reservoir in reservoirs.items()
        },
        "saved_samples": {
            name: reservoir.size for name, reservoir in reservoirs.items()
        },
        "vocab_size": len(cat_to_index) + 2,
        "category_count": len(cat_to_index),
        "seed": seed,
        "stats": stats,
    }
    meta_path = output_dir / "category_gru_v1_meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return dataset_path


def main():
    parser = argparse.ArgumentParser(description="Build Category-GRU dataset from data2 clean CSV")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--test-input", default=str(DEFAULT_TEST_INPUT))
    parser.add_argument("--seq-len", type=int, default=10)
    parser.add_argument("--min-history", type=int, default=2)
    parser.add_argument("--max-windows-per-session", type=int, default=20)
    parser.add_argument("--train-samples", type=int, default=300_000)
    parser.add_argument("--val-samples", type=int, default=75_000)
    parser.add_argument("--test-samples", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    build_dataset(
        args.input,
        args.output_dir,
        test_input_path=args.test_input,
        seq_len=args.seq_len,
        min_history=args.min_history,
        max_windows_per_session=args.max_windows_per_session,
        train_samples=args.train_samples,
        val_samples=args.val_samples,
        test_samples=args.test_samples,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
