# -*- coding: utf-8 -*-
"""Export REES46 cosmetics catalog files for Neon simulation DB.

Inputs:
  - data/processed/recommendation/{product_catalog,category_catalog,category_similar}.parquet
  - team_project_churn/src/2019-*.csv.zip, when available, for product-level brand mode

Outputs:
  - simulation_site/neon/seed/categories.csv
  - simulation_site/neon/seed/brands.csv
  - simulation_site/neon/seed/products.csv
  - simulation_site/neon/seed/category_similarity.csv
  - simulation_site/neon/seed/catalog_meta.json
"""
from __future__ import annotations

import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
REC_DIR = ROOT / "data" / "processed" / "recommendation"
RAW_DIR = WORKSPACE / "team_project_churn" / "src"
SEED_DIR = ROOT / "simulation_site" / "neon" / "seed"
SOURCE_DATASET = "REES46 cosmetics 2019-Oct..2020-Feb"
MONTHS = ["2019-Oct", "2019-Nov", "2019-Dec", "2020-Jan", "2020-Feb"]


def _display_category(row: pd.Series) -> str:
    code = row.get("category_code")
    if isinstance(code, str) and code.strip():
        return code.strip()
    return f"category_{row['category_id']}"


def _safe_brand(value) -> str:
    if value is None or pd.isna(value):
        return "UNK"
    brand = str(value).strip()
    return brand if brand else "UNK"


def load_raw_product_brand_counts() -> dict[str, Counter]:
    """Return product_id -> Counter(brand) from raw REES46 zips.

    This keeps memory small: only product-brand counts are retained, not raw rows.
    If raw zips are absent, callers can fall back to category top_brand.
    """
    counts: dict[str, Counter] = defaultdict(Counter)
    usecols = ["product_id", "brand"]
    dtype = {"product_id": "int64", "brand": "object"}

    for month in MONTHS:
        zip_path = RAW_DIR / f"{month}.csv.zip"
        if not zip_path.exists():
            print(f"[WARN] missing raw zip: {zip_path}")
            continue

        with zipfile.ZipFile(zip_path) as zf:
            csv_name = f"{month}.csv"
            if csv_name not in zf.namelist():
                csv_name = zf.namelist()[0]
            with zf.open(csv_name) as f:
                for chunk in pd.read_csv(f, usecols=usecols, dtype=dtype, chunksize=600_000):
                    chunk["brand"] = chunk["brand"].map(_safe_brand)
                    vc = chunk.groupby(["product_id", "brand"], observed=True).size()
                    for (product_id, brand), n in vc.items():
                        counts[str(int(product_id))][brand] += int(n)
        print(f"[OK] scanned brand counts: {month} ({len(counts):,} products)")

    return counts


def main() -> int:
    SEED_DIR.mkdir(parents=True, exist_ok=True)

    product_path = REC_DIR / "product_catalog.parquet"
    category_path = REC_DIR / "category_catalog.parquet"
    similarity_path = REC_DIR / "category_similar.parquet"

    missing = [str(p) for p in [product_path, category_path, similarity_path] if not p.exists()]
    if missing:
        raise FileNotFoundError("missing recommendation catalog files: " + ", ".join(missing))

    products = pd.read_parquet(product_path)
    categories = pd.read_parquet(category_path)
    similarity = pd.read_parquet(similarity_path)

    for col in ["product_id", "category_id"]:
        products[col] = products[col].astype("int64").astype(str)
    for col in ["category_id"]:
        categories[col] = categories[col].astype("int64").astype(str)
    for col in ["category_id", "similar_category_id"]:
        similarity[col] = similarity[col].astype("int64").astype(str)

    categories["category_code"] = categories["category_code"].where(categories["category_code"].notna(), "")
    categories["display_name"] = categories.apply(_display_category, axis=1)
    categories["top_brand"] = categories["top_brand"].map(_safe_brand)
    categories["price_median"] = categories["price_median"].round(2)
    categories["price_sum"] = categories["price_sum"].round(2)
    categories["source_dataset"] = SOURCE_DATASET

    cat_brand = categories.set_index("category_id")["top_brand"].to_dict()
    brand_counts = load_raw_product_brand_counts()

    def product_brand(row: pd.Series) -> str:
        counter = brand_counts.get(row["product_id"])
        if counter:
            return counter.most_common(1)[0][0]
        return cat_brand.get(row["category_id"], "UNK")

    products["brand"] = products.apply(product_brand, axis=1).map(_safe_brand)
    products["price_median"] = products["price_median"].round(2)
    products["display_name"] = "Product " + products["product_id"].astype(str)
    products["is_active"] = True
    products["source_dataset"] = SOURCE_DATASET

    brands = (
        products.groupby("brand", dropna=False)
        .agg(
            n_products=("product_id", "nunique"),
            n_categories=("category_id", "nunique"),
            n_events=("n_events", "sum"),
            price_median=("price_median", "median"),
        )
        .reset_index()
    )
    brands["brand"] = brands["brand"].map(_safe_brand)
    brands["price_median"] = brands["price_median"].round(2)
    brands["source_dataset"] = SOURCE_DATASET

    similarity = similarity.copy()
    similarity["cosine"] = similarity["cosine"].round(4)
    similarity["source_dataset"] = SOURCE_DATASET

    categories_out = categories[
        [
            "category_id",
            "category_code",
            "display_name",
            "top_brand",
            "price_median",
            "n_products",
            "n_events",
            "price_sum",
            "source_dataset",
        ]
    ].sort_values(["n_events", "category_id"], ascending=[False, True])

    brands_out = brands[
        ["brand", "n_products", "n_categories", "n_events", "price_median", "source_dataset"]
    ].sort_values(["n_events", "brand"], ascending=[False, True])

    products_out = products[
        [
            "product_id",
            "category_id",
            "brand",
            "price_median",
            "n_events",
            "display_name",
            "is_active",
            "source_dataset",
        ]
    ].sort_values(["n_events", "product_id"], ascending=[False, True])

    similarity_out = similarity[
        ["category_id", "rank", "similar_category_id", "cosine", "source_dataset"]
    ].sort_values(["category_id", "rank"])

    categories_out.to_csv(SEED_DIR / "categories.csv", index=False, encoding="utf-8")
    brands_out.to_csv(SEED_DIR / "brands.csv", index=False, encoding="utf-8")
    products_out.to_csv(SEED_DIR / "products.csv", index=False, encoding="utf-8")
    similarity_out.to_csv(SEED_DIR / "category_similarity.csv", index=False, encoding="utf-8")

    meta = {
        "source_dataset": SOURCE_DATASET,
        "input_files": {
            "product_catalog": str(product_path.relative_to(ROOT)),
            "category_catalog": str(category_path.relative_to(ROOT)),
            "category_similarity": str(similarity_path.relative_to(ROOT)),
            "raw_dir_for_brand_mode": str(RAW_DIR),
        },
        "outputs": {
            "categories_csv": "simulation_site/neon/seed/categories.csv",
            "brands_csv": "simulation_site/neon/seed/brands.csv",
            "products_csv": "simulation_site/neon/seed/products.csv",
            "category_similarity_csv": "simulation_site/neon/seed/category_similarity.csv",
        },
        "counts": {
            "categories": int(len(categories_out)),
            "brands": int(len(brands_out)),
            "products": int(len(products_out)),
            "category_similarity_rows": int(len(similarity_out)),
            "products_with_raw_brand_mode": int(sum(1 for c in brand_counts.values() if c)),
        },
        "id_policy": "product_id/category_id are exported as TEXT to avoid JavaScript precision loss.",
    }
    (SEED_DIR / "catalog_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps(meta["counts"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

