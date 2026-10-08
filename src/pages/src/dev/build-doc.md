---
layout: doc
prev: false
next: false
---

# ドキュメントの編集

## 環境構築
1. [nodejs](https://nodejs.org/)をインストールします。(v18以上LTS推奨)
2. コマンドプロンプトを開きプロジェクトのrootに移動します。
3. 下記コマンドを打鍵
```bat
cd src\pages
npm ci
```
\# ローカルにnodejs入れるとめどいのでwslでLinux環境作って立てたほうがいいと思う。Linux環境に構築する場合は`\`と`/`を適宜読み替えてください。

## 編集
`src\pages\src`配下のmdファイルを編集します。MarkDown記法が使えるほか[VitePress拡張記法](https://vitepress.dev/guide/markdown)もあります。

## ビルド
1. コマンドプロンプトを開きプロジェクトのrootに移動します。
2. 下記コマンドを打鍵
```bat
cd src\pages\src
npm run doc:build
```

## ビルド結果の確認
ドキュメントは`src\pages\src\.vitepress\dist`にビルドされますが、ローカルでブラウザには表示できません。doc:previewを行いwebサーバを立ち上げます。
```bat
npm run doc:preview
```


## 本番へのデプロイ
githubにブランチをプッシュした後docs-updateブランチに対してPRを投げてください。mainまでマージされるとデプロイされます。