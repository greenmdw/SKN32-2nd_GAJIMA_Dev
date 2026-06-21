"""ML 학습 CLI (19-3 §4.1).

사용법 (레포 루트에서):
    python -m src.train_ml --model decisiontree
    python -m src.train_ml --model xgboost --run-tag xgb_d8_lr03 --set max_depth=8 --set learning_rate=0.03

--run-tag 없으면 정식 경로(제출용)에 저장, 있으면 runs/{tag}/에 저장 + 리더보드 누적.
"""
import argparse

from src.models.churn import decisiontree_trainer, xgboost_trainer

TRAINERS = {
    "decisiontree": decisiontree_trainer.train,
    "xgboost": xgboost_trainer.train,
}


def parse_overrides(items):
    """['max_depth=8','learning_rate=0.03'] -> {'max_depth':8,'learning_rate':0.03}."""
    out = {}
    for item in items or []:
        key, _, val = item.partition("=")
        for cast in (int, float):
            try:
                out[key] = cast(val)
                break
            except ValueError:
                continue
        else:
            out[key] = val
    return out


def main():
    parser = argparse.ArgumentParser(description="Churn ML trainer")
    parser.add_argument("--model", required=True, choices=list(TRAINERS))
    parser.add_argument("--run-tag", default=None, help="실험 태그 (없으면 정식 경로)")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VAL",
                        help="하이퍼파라미터 오버라이드 (반복 가능)")
    args = parser.parse_args()
    TRAINERS[args.model](run_tag=args.run_tag, **parse_overrides(args.set))


if __name__ == "__main__":
    main()
