using Lucene.Net.Codecs;
using Prism.Ioc;
using Prism.Mvvm;
using Prism.Unity;
using System;
using System.ComponentModel;
using System.Configuration;
using System.Data;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Media3D;
using YamlDotNet.Core;

namespace Haru.Kei; 
/// <summary>
/// Interaction logic for App.xaml
/// </summary>
public partial class App : PrismApplication {
	private readonly Core.CaptionManagement caption = new();
	private readonly Core.ConfigManagement config = new();

	protected override async void OnStartup(StartupEventArgs e) {
		AppDomain.CurrentDomain.UnhandledException += (_, e) => {
			Utils.Singleton.Logger.ErrorUnHandled("致命的なエラー", e);
		};
		/*
		Application.Current.Resources["MahApps.Brushes.ThemeForeground"] = new SolidColorBrush(
			Colors.White);
		MahApps.Metro.Converters.BackgroundToForegroundConverter
		*/
		//            <SolidColorBrush x:Key="MahApps.Brushes.ThemeForeground" Color="{DynamicResource Primary500Foreground}" />
		Utils.Singleton.Logger.Info("sakura起動");
		Utils.Singleton.InitLog();

		Utils.Singleton.Logger.Info("字幕，サーバの設定の読み込みを開始します");
		try {
			await Task.WhenAll(
				caption.Load(),
				config.Load()
				);
		}
		catch (Exception ex) {
			Utils.Singleton.Logger.Error(ex);
			this.Shutdown();
		}
		Utils.Singleton.Logger.Info("字幕，サーバの設定を読み込みました");
		base.OnStartup(e);
	}

	protected override Window CreateShell() {
		return Container.Resolve<Views.MainWindow>();
	}

	protected override void RegisterTypes(IContainerRegistry containerRegistry) {

		ViewModelLocationProvider.Register<Views.MainWindow, ViewModels.MainWindowViewModel>();


		containerRegistry.RegisterInstance<Core.ICaptionManagement>(this.caption);
		containerRegistry.RegisterInstance<Core.IConfigManagement>(this.config);
		containerRegistry.RegisterInstance(containerRegistry);

		base.ConfigureViewModelLocator();
		/*
		ViewModelLocationProvider.Register<Views.MainWindow, ViewModels.MainWindowViewModel>();
		ViewModelLocationProvider.Register<Views.YomiageDialog, ViewModels.YomiageDialogViewModel>();
		containerRegistry.RegisterDialogWindow<Views.YomiageDialogWindow>(nameof(Views.YomiageDialogWindow));
		containerRegistry.RegisterDialog<Views.YomiageDialog>(typeof(Views.YomiageDialog).FullName);
		containerRegistry.RegisterInstance(this.Container);
		*/
	}
}