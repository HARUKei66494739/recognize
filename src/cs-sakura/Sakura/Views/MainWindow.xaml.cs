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

			Core.CaptionManagement m = new Core.CaptionManagement();
			m.Load();
			var css = m.MakeCss();
			System.IO.File.WriteAllText(System.IO.Path.Combine(AppContext.BaseDirectory, "www", "assets", "sakura.gen.css"), css);


			Core.ConfigManagement confmg = new Core.ConfigManagement();
			confmg.Load();
			confmg.ApplyWebConfig();

			this.cores.Start(new(), new());
		}
	}
}