using Haru.Kei.Models;
using System;
using System.Collections.Generic;
using System.Text;

namespace Haru.Kei.ViewModels; 
internal class MainWindowViewModel {
	Core.HttpServer cores = new();

	public MainWindowViewModel(
		Core.ICaptionManagement captionManagement,
		Core.IConfigManagement configManagement) {

		Utils.Singleton.Logger.Info("メインウィンドウのコンポーネントが初期化されました");

		var css = captionManagement.MakeCss();
		System.IO.File.WriteAllText(System.IO.Path.Combine(AppContext.BaseDirectory, "www", "assets", "sakura.gen.css"), css);
		Utils.Singleton.Logger.Info("字幕の設定を配置しました");

		configManagement.ApplyWebConfig();
		Utils.Singleton.Logger.Info("サーバの設定を配置しました");

		Utils.Singleton.Logger.Info("サーバを起動します");
		this.cores.Start(new(), new());
	}

}
