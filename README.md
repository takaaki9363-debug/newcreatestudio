# newcreatestudio 完成版

企業名を **newcreatestudio** とした、営業・ポートフォリオ用のFlaskサイト完成見本です。

## ページ
- `/` トップ
- `/company` 会社情報
- `/service` サービス
- `/works` 制作実績
- `/sample` 制作見本
- `/price` 料金
- `/staff` スタッフ紹介
- `/contact` お問い合わせ
- `/privacy` プライバシーポリシー

## 起動
PowerShellでこのフォルダを開いて、

```powershell
python -m pip install -r requirements.txt
python app.py
```

ブラウザで `http://127.0.0.1:5000` を開きます。

## 本番公開前に必ず差し替えるもの
- 所在地
- 代表者名
- 実際の料金
- 実際の制作実績
- スタッフ写真・氏名
- お問い合わせメール送信処理
- プライバシーポリシーの実情報
- ドメイン・サーバー設定
- SECRET_KEY

現在の問い合わせフォームは「入力→受付メッセージ」までの完成見本です。
実運用ではメール送信またはDB保存を接続してください。
