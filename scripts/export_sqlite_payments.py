#!/usr/bin/env python3
"""Export SQLite payment data into CSV files for Salespos CSV import.

Usage example:
  python scripts/export_sqlite_payments.py \
    --db "C:\\Users\\shunk\\App\\sales.db" \
    --out "C:\\Users\\shunk\\App\\Salespos_v2\\import-csv" \
    --from-date 2026-01-01 \
    --to-date 2026-02-29
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path


DATE_CANDIDATES = [
    "date",
    "sales_date",
    "target_date",
    "business_date",
    "transaction_date",
    "created_at",
    "createdat",
]

PAYMENT_CANDIDATES = {
    "point": [
        "point_usage",
        "pointuse",
        "point",
        "points",
        "point_amount",
        "pointpayment",
        "point_payment",
    ],
    "credit": [
        "credit_card_payment",
        "creditcardpayment",
        "credit_payment",
        "credit",
        "card",
        "card_payment",
        "credit_amount",
    ],
    "qr": [
        "qr_payment",
        "qrpayment",
        "qr",
        "qrcode_payment",
        "barcode_payment",
        "paypay",
        "qr_amount",
    ],
}


@dataclass
class TableSelection:
    table: str
    date_col: str
    amount_cols: dict[str, str | None]


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def list_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [row[0] for row in rows]


def list_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({quote_ident(table)})").fetchall()
    return [row[1] for row in rows]


def pick_column(columns: list[str], candidates: list[str]) -> str | None:
    lower_map = {col.lower(): col for col in columns}
    for cand in candidates:
        if cand in lower_map:
            return lower_map[cand]
    return None


def auto_select_table(conn: sqlite3.Connection) -> TableSelection:
    best: TableSelection | None = None
    best_score = -1

    for table in list_tables(conn):
        cols = list_columns(conn, table)
        if not cols:
            continue

        date_col = pick_column(cols, DATE_CANDIDATES)
        if not date_col:
            continue

        amount_cols = {
            payment_type: pick_column(cols, candidates)
            for payment_type, candidates in PAYMENT_CANDIDATES.items()
        }
        score = 10 + sum(1 for v in amount_cols.values() if v)
        if score > best_score:
            best_score = score
            best = TableSelection(table=table, date_col=date_col, amount_cols=amount_cols)

    if not best:
        tables = list_tables(conn)
        raise RuntimeError(
            "日付カラムを含むテーブルを自動判定できませんでした。"
            f" 利用可能テーブル: {', '.join(tables) if tables else '(なし)'}"
        )
    return best


def resolve_selection(
    conn: sqlite3.Connection,
    table_arg: str | None,
    date_col_arg: str | None,
    point_col_arg: str | None,
    credit_col_arg: str | None,
    qr_col_arg: str | None,
) -> TableSelection:
    if not table_arg:
        selected = auto_select_table(conn)
    else:
        cols = list_columns(conn, table_arg)
        if not cols:
            raise RuntimeError(f"指定テーブルが見つかりません: {table_arg}")
        date_col = date_col_arg or pick_column(cols, DATE_CANDIDATES)
        if not date_col:
            raise RuntimeError(
                f"日付カラムを判定できませんでした。--date-column で指定してください。 columns={cols}"
            )
        selected = TableSelection(
            table=table_arg,
            date_col=date_col,
            amount_cols={
                "point": point_col_arg or pick_column(cols, PAYMENT_CANDIDATES["point"]),
                "credit": credit_col_arg or pick_column(cols, PAYMENT_CANDIDATES["credit"]),
                "qr": qr_col_arg or pick_column(cols, PAYMENT_CANDIDATES["qr"]),
            },
        )

    if date_col_arg:
        selected.date_col = date_col_arg
    if point_col_arg:
        selected.amount_cols["point"] = point_col_arg
    if credit_col_arg:
        selected.amount_cols["credit"] = credit_col_arg
    if qr_col_arg:
        selected.amount_cols["qr"] = qr_col_arg

    return selected


def export_csv(
    conn: sqlite3.Connection,
    out_dir: Path,
    table: str,
    date_col: str,
    amount_col: str,
    payment_type: str,
    from_date: str,
    to_date: str,
) -> tuple[Path, int, int]:
    table_q = quote_ident(table)
    date_q = quote_ident(date_col)
    amount_q = quote_ident(amount_col)
    date_expr = f"CASE WHEN typeof({date_q})='integer' THEN date({date_q}, 'unixepoch') ELSE date({date_q}) END"

    sql = f"""
        SELECT
          {date_expr} AS date,
          CAST(ROUND(SUM(COALESCE(CAST({amount_q} AS REAL), 0)), 0) AS INTEGER) AS amount
        FROM {table_q}
        WHERE {date_expr} BETWEEN ? AND ?
          AND COALESCE(CAST({amount_q} AS REAL), 0) <> 0
        GROUP BY {date_expr}
        ORDER BY {date_expr}
    """
    rows = conn.execute(sql, (from_date, to_date)).fetchall()

    out_path = out_dir / f"{payment_type}_{from_date}_to_{to_date}.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "amount"])
        writer.writerows(rows)

    total = sum(int(row[1]) for row in rows)
    return out_path, len(rows), total


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="sales.db から CSV取込用ファイルを生成します。")
    parser.add_argument("--db", required=True, help="SQLite DB のパス")
    parser.add_argument("--out", required=True, help="CSV 出力先フォルダ")
    parser.add_argument("--from-date", default="2026-01-01", help="開始日 (YYYY-MM-DD)")
    parser.add_argument("--to-date", default="2026-02-29", help="終了日 (YYYY-MM-DD)")
    parser.add_argument("--table", help="テーブル名（省略時は自動推定）")
    parser.add_argument("--date-column", help="日付カラム名")
    parser.add_argument("--point-column", help="ポイント金額カラム名")
    parser.add_argument("--credit-column", help="カード金額カラム名")
    parser.add_argument("--qr-column", help="QR金額カラム名")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_path = Path(args.db)
    out_dir = Path(args.out)

    if not db_path.exists():
        print(f"[ERROR] DBファイルが見つかりません: {db_path}", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        selected = resolve_selection(
            conn=conn,
            table_arg=args.table,
            date_col_arg=args.date_column,
            point_col_arg=args.point_column,
            credit_col_arg=args.credit_column,
            qr_col_arg=args.qr_column,
        )

        print("[INFO] 使用テーブル:", selected.table)
        print("[INFO] 日付カラム:", selected.date_col)
        print("[INFO] 金額カラム:", selected.amount_cols)

        exported = 0
        for payment_type in ("point", "credit", "qr"):
            amount_col = selected.amount_cols.get(payment_type)
            if not amount_col:
                print(f"[WARN] {payment_type} のカラムが見つからないためスキップ")
                continue
            out_path, row_count, total = export_csv(
                conn=conn,
                out_dir=out_dir,
                table=selected.table,
                date_col=selected.date_col,
                amount_col=amount_col,
                payment_type=payment_type,
                from_date=args.from_date,
                to_date=args.to_date,
            )
            print(f"[OK] {payment_type}: {out_path} ({row_count}日分, 合計 {total:,}円)")
            exported += 1

        if exported == 0:
            print(
                "[ERROR] 出力できるデータがありませんでした。--table / --*-column で列名を指定してください。",
                file=sys.stderr,
            )
            return 1

        print("[DONE] CSV取込画面で種類を切り替えて各CSVを読み込んでください。")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
