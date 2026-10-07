# 理科基礎問題 API v2

「理科基礎問題集」のJSON構造に対応したFastAPIです。

## 対応科目

- `basic_phys` : 物理基礎
- `basic_chem` : 化学基礎
- `basic_bio` : 生物基礎
- `basic_geo` : 地学基礎

各科目の問題IDは科目ごとに管理します。そのため、各科目に `id: 1` があっても問題ありません。
APIでは `subjectId + questionId` で一意に扱います。

## 起動（Windows PowerShell）

```powershell
cd science_api
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

ブラウザで `http://127.0.0.1:8000/docs` を開くとAPI仕様を確認できます。

## エンドポイント

- `GET /api/subjects`
- `GET /api/subjects/{subject_id}`
- `GET /api/subjects/{subject_id}/categories`
- `GET /api/subjects/{subject_id}/units`
- `GET /api/subjects/{subject_id}/questions`
- `GET /api/subjects/{subject_id}/questions/{question_id}`
- `GET /api/subjects/{subject_id}/random`
- `POST /api/subjects/{subject_id}/questions/{question_id}/answer`

## 絞り込み

```text
/api/subjects/basic_phys/questions?category=運動とエネルギー
/api/subjects/basic_phys/questions?difficulty=hard
/api/subjects/basic_chem/questions?category=物質の構成
/api/subjects/basic_chem/questions?unit=原子
```

## 回答送信

```json
POST /api/subjects/basic_phys/questions/1/answer
{
  "choiceIndex": 1
}
```

`choiceIndex` は0始まりです。

## 公開運用

CORSはデフォルトで全許可です。公開時は環境変数 `ALLOWED_ORIGINS` にWebアプリのURLを設定してください。

例:

```text
ALLOWED_ORIGINS=https://example.com
```

簡易IPレート制限も入れています。大規模運用ではRedis等への置き換えを推奨します。
