---
layout: doc
prev: false
next: false
---

# 開発ドキュメント

## ビルド環境
|種別|バージョン|
|----|----|
|OS|Windows 11|
|python|3.10,3.11,3.12|
|そのほか|Visual C++コンパイラ<br>.NET SDK v8|

## ビルド
プロジェクトルートにあるbuild-all.batを実行するとビルドされます。


## recognize本体の開発
ディレクトリ`src\py-recognition`に移動し、pipenvを使用し環境構築を行います。

```bat
python -m pipenv install --dev
```