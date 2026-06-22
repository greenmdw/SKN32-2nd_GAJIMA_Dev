# Neon catalog seed files

These files are generated from the REES46 cosmetics recommendation catalog.

Generation:

```powershell
cd C:\Users\playdata2\Documents\ml_workspace\SKN32-2nd_GAJIMA_Dev
.venv\Scripts\python.exe simulation_site\neon\export_rees46_catalog.py
```

Upload order:

1. `schema_neon.sql`
2. `categories.csv`
3. `brands.csv`
4. `products.csv`
5. `category_similarity.csv`

The import helper is `simulation_site/neon/catalog_import.sql`.

