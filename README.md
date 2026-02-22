# Salespos_v2

## sales.db 取り込み（2026年1月〜2月）

このアプリは現在、画面上では CSV 取込に対応しています。  
`sales.db`（SQLite）から取り込む場合は、先に CSV へ変換してください。

### 1) CSV 変換

PowerShell でプロジェクト直下に移動して実行:

```powershell
cd "C:\Users\shunk\App\Salespos_v2"
python .\scripts\export_sqlite_payments.py `
  --db "C:\Users\shunk\App\sales.db" `
  --out "C:\Users\shunk\App\Salespos_v2\import-csv" `
  --from-date 2026-01-01 `
  --to-date 2026-02-29
```

`import-csv` フォルダに `point_*.csv` / `credit_*.csv` / `qr_*.csv` が生成されます。

### 2) アプリへ取込

1. アプリを起動（`npm run dev`）
2. サイドメニュー `CSV取込` を開く
3. 種類を `ポイント利用` / `クレジットカード払い` / `QRコード払い` に切り替え
4. 対応する CSV を選択して取り込む

取り込んだデータは `売上入力` 画面へ反映されます。