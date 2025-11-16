#!/usr/bin/env python
import sys
from pathlib import Path

import polars as pl


def main():
    # Dossier racine des parquets : par défaut ../data/clean/parquet
    # ou bien tu peux passer le chemin en argument : python check_parquets.py /data/clean/parquet
    if len(sys.argv) > 1:
        root = Path(sys.argv[1])
    else:
        root = Path("../../data/clean/parquet")

    if not root.exists():
        print(f"[ERR] Dossier inexistant : {root}")
        sys.exit(1)

    parquet_files = sorted(p for p in root.rglob("*.parquet") if p.is_file())
    if not parquet_files:
        print(f"[INFO] Aucun fichier parquet trouvé sous {root}")
        sys.exit(0)

    total = len(parquet_files)
    btc_count = 0
    eth_count = 0
    both_count = 0

    print(f"[INFO] Analyse de {total} fichier(s) parquet sous {root}\n")

    for path in parquet_files:
        try:
            # On ne lit que la colonne symbol pour aller plus vite
            df = pl.read_parquet(str(path), columns=["symbol"])
        except Exception as exc:
            print(f"[WARN] Impossible de lire {path} : {exc}")
            continue

        if "symbol" not in df.columns:
            continue

        # On passe tout en string / upper
        symbols = df["symbol"].cast(pl.Utf8).str.to_uppercase()

        has_btc = symbols.str.contains("BTC", literal=True).any()
        has_eth = symbols.str.contains("ETH", literal=True).any()

        if has_btc or has_eth:
            line = f"{path}:"
            if has_btc:
                line += " BTC"
            if has_eth:
                line += " ETH"
            print(line)

        if has_btc:
            btc_count += 1
        if has_eth:
            eth_count += 1
        if has_btc and has_eth:
            both_count += 1

    print("\n========== RÉSUMÉ ==========")
    print(f"Total parquets analysés : {total}")
    print(f"Parquets contenant au moins un symbol avec 'BTC' : {btc_count}")
    print(f"Parquets contenant au moins un symbol avec 'ETH' : {eth_count}")
    print(f"Parquets contenant à la fois BTC et ETH : {both_count}")


if __name__ == "__main__":
    main()
