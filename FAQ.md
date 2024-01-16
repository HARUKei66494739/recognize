# FAQ

## マイクの指定
recognize.exeを--print_micsで実行するとマイクデバイスをコンソールに出力します。そのIDを--micオプションに指定します。


## 音声認識のタイミング
マイクが無音となった時間が--mic_pause秒経過したタイミングで音声認識を行います。  
ゆかりねっとのような逐次認識は行いません。


## マイク感度の調整
デフォルトでマイク音量が300(この値が具体的にどの音量なのかはお使いのマイクによります)を下回る場合無音として扱われます。話終わっても認識をが始まらない場合のノイズを拾っているので300より大きい値に設定してください。
話していても認識されない場合300より低い値にしてください。
