# ImageNetDataSetMaker
ImageNetの画像はサイズがバラバラなのでトリミングして画像のサイズを揃えます。
ImageNetの画像の中からバウンディングボックスがつけられたものを選んでダウンロードし、バウンディングボックスを含むように画像をトリミングしてくれます。
## パラメータ
### targetXResolution、targetYResolution
整形後の画像のサイズをここで指定。
### useImageCountPerClass
各wordnetid毎に何枚の画像が欲しいかをここで指定。
### saveImagePath
画像の保存場所。
### checkPointId
途中再開したい場合に使う。wordnetidを入力するとそのidから処理を始める。
