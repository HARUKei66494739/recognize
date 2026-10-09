using Prism.Ioc;
using Prism.Mvvm;
using Prism.Unity;
using System.ComponentModel;
using System.Configuration;
using System.Data;
using System.Windows;

namespace Haru.Kei; 
/// <summary>
/// Interaction logic for App.xaml
/// </summary>
public partial class App : PrismApplication {
	protected override void OnStartup(StartupEventArgs e) {
		//this.Shutdown();
		base.OnStartup(e);
	}

	protected override Window CreateShell() {
		return Container.Resolve<Views.MainWindow>();
	}

	protected override void RegisterTypes(IContainerRegistry containerRegistry) {
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