using Fleck;
using Haru.Kei.Models;
using System;
using System.Collections.Generic;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Shapes;

namespace Haru.Kei.Views {
	/// <summary>
	/// MainWindow.xaml の相互作用ロジック
	/// </summary>
	public partial class MainWindow : Window {
		Core.HttpServer cores = new();
		public MainWindow() {
			InitializeComponent();

			Utils.Singleton.Logger.Info("メインウィンドウのコンポーネントが初期化されました");
		}

		protected async override void OnInitialized(EventArgs e) {
			base.OnInitialized(e);

			Utils.Singleton.Logger.Info("OnInitialized");
			Utils.Singleton.Logger.Info("字幕の設定を読み込みます");

			Core.CaptionManagement m = new Core.CaptionManagement();
			await  m.Load();
			var css = m.MakeCss();
			System.IO.File.WriteAllText(System.IO.Path.Combine(AppContext.BaseDirectory, "www", "assets", "sakura.gen.css"), css);

			Utils.Singleton.Logger.Info("字幕の設定を読み込みました");

			Utils.Singleton.Logger.Info("サーバの設定を読み込みました");
			Core.ConfigManagement confmg = new Core.ConfigManagement();
			await confmg.Load();
			confmg.ApplyWebConfig();
			Utils.Singleton.Logger.Info("サーバの設定を読み込みました");

			Utils.Singleton.Logger.Info("サーバを起動します");
			this.cores.Start(new(), new());
		}
	}
}