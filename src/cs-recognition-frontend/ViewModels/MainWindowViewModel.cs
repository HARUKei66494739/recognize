using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Reactive.Linq;
using System.Reflection;
using System.Security;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using Haru.Kei.Models;
using Haru.Kei.Views;
using Livet.Behaviors.Messaging;
using Livet.Messaging;
using Livet.Messaging.IO;
using Prism.Dialogs;
using Prism.Mvvm;
using Reactive.Bindings;

namespace Haru.Kei.ViewModels;

public class MainWindowViewModel : BindableBase {
	public static string ConfirmationKey = "Confirmation";
	public static string OpenFileKey = "OpenFile";
	public static string SaveFileKey = "SaveFile";

	private readonly string CONFIG_0_FILE = "frontend.conf";
	private readonly string CONFIG_FILE = "recognize-gui.conf";
	private readonly string FILTER_FILE = "recognize-filter.conf";
	private readonly string BAT_FILE = "custom-recognize.bat";
	private readonly string TEMP_BAT = global::System.IO.Path.Combine(
		global::System.IO.Path.GetTempPath(),
		string.Format("recognize-gui-{0}.bat", Guid.NewGuid()));

	private ReactivePropertySlim<bool> IsRunningLoadMic { get; } = new(initialValue: false);

	public ReactivePropertySlim<Visibility> InitializeVisibility { get; } = new(initialValue: Visibility.Visible);
	public IReadOnlyReactiveProperty<bool> IsEnabledMicSelect { get; }
	public IReadOnlyReactiveProperty<bool> IsEnabledStart { get; }

	public ReactiveProperty<Models.Filter> Filter { get; } = new(initialValue: new());

	public ReactiveCommand CreateBatchommand { get; } = new();
	public ReactiveCommand MicReloadCommand { get; } = new();
	public ReactiveCommand MicTestCommand { get; } = new();
	public ReactiveCommand AmbientTestCommand { get; } = new();
	public ReactiveCommand IlluminateTestCommand { get; } = new();
	public ReactiveCommand CloseCommand { get; } = new();

	public ReactiveCommand ConnectWhisperCommand { get; } = new();
	public ReactiveCommand ConnectGoogleCommand { get; } = new();
	public ReactiveCommand ConnectYukarinetteCommand { get; } = new();
	public ReactiveCommand ConnectYukaConeCommand { get; } = new();

	public ReactiveCommand ExecCommand { get; } = new();


	public ReactiveCommand<RoutedEventArgs> LoadedCommand { get; } = new();
	public ReactiveCommand ClosingCommand { get; } = new();


	public ReactiveCommand<OpeningFileSelectionMessage> IlluminateClientClickCommand { get; } = new();

	public ReactiveCommand<RoutedEventArgs> FilterAddClickCommand { get; } = new();
	public ReactiveCommand<RoutedEventArgs> FilterRemoveClickCommand { get; } = new();
	public ReactiveCommand<RoutedEventArgs> RuleAddClickCommand { get; } = new();
	public ReactiveCommand<RoutedEventArgs> RuleEditClickCommand { get; } = new();
	public ReactiveCommand<RoutedEventArgs> RuleRemoveClickCommand { get; } = new();

	public ReactiveCommand RuleImportCommand {  get; } = new();
	public ReactiveCommand RuleExportCommand {  get; } = new();

	public ReactiveProperty<Models.FilterItem?> SelectedFilterItem { get; } = new();


	public InteractionMessenger Messenger { get; } = new();

	private global::System.Windows.Forms.PropertyGrid? propertyGrid;
	private readonly IDialogService dialogService;

	public Models.Config Config { get; private set; }
	public Models.ConfigBinder ConfigBinder { get; private set; }

	public MainWindowViewModel(IDialogService dialogService) {
		this.dialogService = dialogService;

		this.IsEnabledMicSelect = this.IsRunningLoadMic
			.Select(x => !x)
			.ToReadOnlyReactivePropertySlim();
		this.IsEnabledStart = this.IsRunningLoadMic
			.Select(x => !x)
			.ToReadOnlyReactivePropertySlim();

		this.LoadedCommand.Subscribe(async x => await this.OnLoaded(x));
		this.ClosingCommand.Subscribe(() => this.OnClosing());
		this.IlluminateClientClickCommand.Subscribe(x => this.OnIlluminateClientClick(x));
		this.FilterAddClickCommand.Subscribe(_ => this.OnFilterAdd());
		this.FilterRemoveClickCommand.Subscribe(x => this.OnFilterRemove(x));
		this.RuleAddClickCommand.Subscribe(x => this.OnRuleAdd(x));
		this.RuleEditClickCommand.Subscribe(x => this.OnRuleEdit(x));
		this.RuleRemoveClickCommand.Subscribe(x => this.OnRuleRemove(x));
		this.RuleImportCommand.Subscribe(async () => await this.OnRuleImport());
		this.RuleExportCommand.Subscribe(async () => await this.OnRuleExport());

		this.SelectedFilterItem.Subscribe(x => {
			if((x == null) && (this.Filter.Value.Filters?.FirstOrDefault() is Models.FilterItem it)) {
				this.SelectedFilterItem.Value = it;
			}
		});

		this.ExecCommand.Subscribe(() => this.OnExec());
		this.CreateBatchommand.Subscribe(async () => await this.OnCreateBatch());
		this.MicReloadCommand.Subscribe(() => this.OnMicReload());
		this.MicTestCommand.Subscribe(() => this.ExecuteTest("mic"));
		this.AmbientTestCommand.Subscribe((_) => this.ExecuteTest("mic_ambient"));
		this.IlluminateTestCommand.Subscribe(() => this.ExecuteTest("illuminate"));
		this.CloseCommand.Subscribe((_) => {
			global::System.Windows.Application.Current?.Shutdown();
		});

		this.ConnectWhisperCommand.Subscribe(() => this.OnConnectWhisper());
		this.ConnectGoogleCommand.Subscribe((_) => this.OnConnectGoogle());
		this.ConnectYukarinetteCommand.Subscribe((_) => this.OnConnectYukarinette());
		this.ConnectYukaConeCommand.Subscribe(() => this.OnConnectYukaCone());

		try {
			var conf0Path = System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, this.CONFIG_0_FILE);
			if(File.Exists(conf0Path)) {
				// 旧設定ファイルからのマイグレ
				var conf0 = this.LoadConfig0(conf0Path);
				this.Config = new();
				this.Config.TranscribeModel = conf0.ArgMethod switch {
					"faster_whisper" => "kotoba_whisper",
					"kotoba_whisper" => "kotoba_whisper",
					"google" => "google_mix",
					"google_duplex" => "google_mix",
					"google_mix" => "google_mix",
					_ => ""
				};
				this.Config.GoogleLanguage = conf0.ArgGoogleLanguage;
				this.Config.GoogleTimeout = conf0.ArgGoogleTimeout;
				this.Config.GoogleProfanityFilter = conf0.ArgGoogleProfanityFilter ?? false;
				this.Config.TranslateModel = conf0.ArgTranslate;
				this.Config.Microphone = conf0.ArgMicV2;
				this.Config.MicrophoneThresholdDb = conf0.ArgMicDbThresholdV2;
				this.Config.MicrophoneRecordMinDuration = conf0.ArgMicRecordMinDuration;
				{
					if(Enum.TryParse<HpfArgGenerater.HpfParamater>(conf0.ArgVadParamaterV2, out var v2)) {
						this.Config.HpfParamater = v2 switch {
							HpfArgGenerater.HpfParamater.無効 => ConfigBinder.HpfParamDisable,
							HpfArgGenerater.HpfParamater.弱い => ConfigBinder.HpfParamLow,
							HpfArgGenerater.HpfParamater.普通 => ConfigBinder.HpfParamNormal,
							HpfArgGenerater.HpfParamater.強め => ConfigBinder.HpfParamHi,
							_ => null
						};
					} else {
						this.Config.HpfParamater = null;
					}
				}
				this.Config.IsUsedYukarinette = conf0.ArgOutWithYukarinette ?? false;
				this.Config.YukatinettePort = conf0.ArgOutYukarinette;
				this.Config.IsUsedYukaCone = conf0.ArgOutWithYukacone ?? false;
				this.Config.YukaConePort = conf0.ArgOutYukacone;
				this.Config.IsUsedObsSubtitle = conf0.ArgSubtitle?.Length != 0;
				this.Config.ObsSubtitleTruncate = conf0.ArgSubtitleTruncate;
				this.Config.ObsSubtitleTextEn = conf0.ArgSubtitleObsTextEn;
				this.Config.ObsSubtitlePort = conf0.ArgSubtitlePort;
				this.Config.ObsSubtitlePassword = conf0.ArgSubtitlePassword;
				this.Config.Extra.RecognizeExePath = conf0.RecognizeExePath;
				this.Config.Extra.ArgVerbose = conf0.ArgVerbose;
				this.Config.Extra.ArgLogDirectory = conf0.ArgLogDirectory;
				this.Config.Extra.ArgRecord = conf0.ArgRecord;
				this.Config.Extra.ArgRecordFile = conf0.ArgRecordFile;
				this.Config.Extra.ArgRecordDirectory = conf0.ArgRecordDirectory;
				this.Config.Extra.ArgTorchCache = conf0.ArgTorchCache;
				this.Config.UserArguments = conf0.ExtraArgument;

				try {
					this.SaveConfig((this.CONFIG_FILE, this.Config));
					File.Delete(conf0Path);
				}
				catch { }
			} else if(File.Exists(this.CONFIG_FILE)) {
				var json = File.ReadAllText(System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, this.CONFIG_FILE));
				this.Config = Newtonsoft.Json.JsonConvert.DeserializeObject<Models.Config>(json) switch {
					Models.Config v => v,
					_ => new Config(),
				};
			} else {
				this.Config = new();
			}
		}
		catch(Exception) {
			this.Config = new();
		}
		this.ConfigBinder = new(this.Config);
		{
			var mic = this.ConfigBinder.MicDeviceIndex.Value;
			this.LoadMicList()
				.Subscribe(
					x => { 
						if(1 < x.Count()) {
							this.ConfigBinder.MicDeviceIndex.Value = mic;
						}
					},
					ex => { },
					() => {
						this.InitializeVisibility.Value = Visibility.Collapsed;
					});
		}
	}

	/// <summary>旧設定フォーマットからの読み込み</summary>
	/// <param name="path"></param>
	/// <returns></returns>
	private RecognizeExeArgument LoadConfig0(string path) {
		var convDic = new Dictionary<Type, Func<string, object?>>();
		convDic.Add(typeof(string), (x) => x);
		convDic.Add(typeof(bool?), (x) => bool.TryParse(x, out var v) ? v : null);
		convDic.Add(typeof(int?), (x) => int.TryParse(x, out var v) ? v : null);
		convDic.Add(typeof(float?), (x) => float.TryParse(x, out var v) ? v : null);

		var list = new List<Tuple<string, string>>();
		try {
			var save = File.ReadAllText(path);
			foreach(var line in save.Replace("\r\n", "\n").Split('\n')) {
				var c = line.IndexOf(':');
				if(0 < c) {
					var tp = new Tuple<string, string>(line.Substring(0, c), line.Substring(c + 1));
					list.Add(tp);
				}
			}
		}
		catch(IOException) { }

		var prop = typeof(RecognizeExeArgument).GetProperties().Where(x => x.CanWrite);
		var pr = typeof(RecognizeExeArgument).GetProperty("RecognizeExePath");
		var exe = list.Where(x => x.Item1 == pr.Name).FirstOrDefault();
		var arg = new RecognizeExeArgument();
		foreach(var tp in list) {
			var p = prop.Where(x => x.Name == tp.Item1).FirstOrDefault();
			if(p != null) {
				var svattr = p.GetCustomAttribute<SaveAttribute>();
				if((svattr != null) && !svattr.IsRestore) {
					continue;
				}

				Func<string, object> f;
				if(convDic.TryGetValue(p.PropertyType, out f)) {
					var v = f(tp.Item2);
					if(v != null) {
						p.SetValue(arg, v);
					}
				}
			}
		}
		return arg;
	}


	private string GetCommandLine() {
		var sb = new StringBuilder(this.Config.ToCommandOption());
		if(this.Filter.Value?.Filters?.Any() ?? false) {
			sb.Append($"  --transcribe_filter \"{Path.Combine(AppContext.BaseDirectory, FILTER_FILE)}\"");
		}
		return sb.ToString();
	}

	private IObservable<IEnumerable<string>> LoadMicList() {
		return Observable.Create<List<string>>(o => {
			try {
				if(File.Exists(this.Config.Extra.RecognizeExePath)) {
					this.IsRunningLoadMic.Value = true;
					var r = new List<string>() {
						"設定しない"
					};
					using(var p = System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo() {
						FileName = this.Config.Extra.RecognizeExePath,
						Arguments = "--print_mics",
						RedirectStandardOutput = true,
						UseShellExecute = false,
						WindowStyle = System.Diagnostics.ProcessWindowStyle.Hidden,
						CreateNoWindow = true,
					})) {
						string? s;
						while((s = p?.StandardOutput?.ReadLine()) != null) {
							r.Add(s);
						}
						p.WaitForExit();
						o.OnNext(r);
					}
				}
			}
			catch(Exception e) {
				o.OnError(e);
			}
			finally {
				o.OnCompleted();
			}
			return System.Reactive.Disposables.Disposable.Empty;
		})
			.SubscribeOn(System.Reactive.Concurrency.TaskPoolScheduler.Default)
			.ObserveOn(Reactive.Bindings.UIDispatcherScheduler.Default)
			.Finally(() => {
				this.IsRunningLoadMic.Value = false;
			})
			.Select(
				x => {
					if(0 < x.Count) {
						this.ConfigBinder.MicDevicesBinder.Clear();
						this.ConfigBinder.MicDevicesBinder.AddRange(x);
					}
					return x.AsReadOnly();
				});
	}

	private void ExecuteTest(string testArg) {
		System.Diagnostics.Debug.Assert(this.Config is not null);
		try {
			using(System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo() {
				FileName = this.Config.Extra.RecognizeExePath,
				Arguments = $"--test {testArg} {this.GetCommandLine()}",
				UseShellExecute = true,
			})) { }
		}
		catch(Exception) { }
	}

	private async Task OnLoaded(RoutedEventArgs e) {
		this.propertyGrid = ((MainWindow)e.Source).propertyGrid;
		this.propertyGrid.SelectedObject = this.Config.Extra;
		if(!IsValidExePath(this.Config)) {
			await Messenger.RaiseAsync(new ConfirmationMessage(
				"パスに不正な文字が含まれます。ゆーかねすぴれこは英数字だけのパスに配置してください。",
				"ゆーかねすぴれこ",
				ConfirmationKey) {

				Button = MessageBoxButton.OK,
				Image = MessageBoxImage.Warning,
			});
			global::System.Windows.Application.Current?.Shutdown();
		}

		Models.Filter? filter = default;
		try {
			var json = File.ReadAllText(System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, this.FILTER_FILE));
			filter = Newtonsoft.Json.JsonConvert.DeserializeObject<Models.Filter>(json);
		}
		catch(IOException) { }
		if(filter != null) {
			this.Filter.Value = filter;
			this.SelectedFilterItem.Value = filter.Filters?.FirstOrDefault();
		}
	}

	private void OnClosing() {
		this.SaveConfig(
			(this.CONFIG_FILE, this.Config),
			(this.FILTER_FILE, this.Filter.Value));
		try {
			if(File.Exists(this.TEMP_BAT)) {
				File.Delete(this.TEMP_BAT);
			}
		}
		catch(IOException) { }
	}

	private void OnIlluminateClientClick(OpeningFileSelectionMessage e) {
		if(e.Response?.FirstOrDefault() is string file) {
			this.ConfigBinder.IlluminateClientBinding.Value = file;
		}
	}

	private void OnFilterAdd() {
		var f = new Models.FilterItem();
		f.Name.Value = "新規フィルタ";
		this.Filter.Value.Filters?.Add(f);
		this.SelectedFilterItem.Value = f;
	}

	private void OnFilterRemove(RoutedEventArgs e) {
		if(e.Source is FrameworkElement el && el.DataContext is Models.FilterItem item) {
			this.Filter.Value.Filters?.Remove(item);
		}
	}

	private void OnRuleAdd(RoutedEventArgs e) {
		if(this.SelectedFilterItem.Value != null) {
			var parameters = new DialogParameters();
			this.dialogService.ShowDialog(nameof(Views.FilterRuleEditDialog), parameters, dialogResult => {
				if(dialogResult.Result == ButtonResult.OK) {
					if(dialogResult.Parameters["result"] is Models.FilterRule r) {
						this.SelectedFilterItem.Value.Rules?.Add(r);
					}
				}
			});
		}
	}

	private void OnRuleEdit(RoutedEventArgs e) {
		if(e.Source is FrameworkElement el && el.DataContext is Models.FilterRule rule) {
			if(this.SelectedFilterItem.Value != null) {
				var index = this.SelectedFilterItem.Value.Rules?.Select((x, i) => (V: x, I: i))
					.Where(x => object.ReferenceEquals(x.V, rule))
					.Select(x => x.I)
					.FirstOrDefault();
				System.Diagnostics.Debug.WriteLine(index);


				var parameters = new DialogParameters
				{
					{ "input", rule}
				};

				this.dialogService.ShowDialog(nameof(Views.FilterRuleEditDialog), parameters, dialogResult => {
					if(dialogResult.Result == ButtonResult.OK) {
					}
				});
			}
		}
	}


	private void OnRuleRemove(RoutedEventArgs e) {
		if(e.Source is FrameworkElement el && el.DataContext is Models.FilterRule rule) {
			if(this.SelectedFilterItem.Value != null) {
				this.SelectedFilterItem.Value.Rules?.Remove(rule);
			}
		}
	}


	private bool IsValidExePath(Models.Config argument) {
		if(string.IsNullOrEmpty(argument.Extra.RecognizeExePath)) {
			return true;
		}

		try {
			var path = Helpers.Util.IsFullPath(argument.Extra.RecognizeExePath) switch {
				true => argument.Extra.RecognizeExePath,
				false => global::System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, Config.Extra.RecognizeExePath) // 作業ディレクトリがexeのディレクトリとは限らないので作り直す
			};

			// ASCIIを超えた場合はfalse
			foreach(var c in path) {
				if(255 < c) {
					return false;
				}
			}
			return true;
		}
		catch(ArgumentException) { return false; }
		catch(SecurityException) { return false; }
		catch(NotSupportedException) { return false; }
		catch(PathTooLongException) { return false; }
	}

	private void SaveConfig(params (string File, object Obj)[] objs) {
		static bool json(string fileName, object o) {
			try {
				System.IO.File.WriteAllText(
					System.IO.Path.Combine(AppContext.BaseDirectory, fileName),
					Newtonsoft.Json.JsonConvert.SerializeObject(o));
				return true;
			}
			catch {
				return false;
			}
		}

		foreach(var it in objs) {
			json(it.File, it.Obj);
		}
	}

	private void OnExec() {
		this.SaveConfig(
			(this.CONFIG_FILE, this.Config),
			(this.FILTER_FILE, this.Filter.Value));

		var bat = new StringBuilder()
			.AppendLine("@echo off")
			.AppendLine()
			.AppendFormat("\"{0}\"", this.Config.Extra.RecognizeExePath).Append(" ").AppendLine(this.GetCommandLine())
			.AppendLine("if %ERRORLEVEL% neq 0 (")
			.AppendLine("  pause")
			.AppendLine(")");
		File.WriteAllText(this.TEMP_BAT, bat.ToString(), Encoding.GetEncoding("Shift_JIS"));

		try {
			using(System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo() {
				FileName = this.TEMP_BAT,
				WorkingDirectory = AppDomain.CurrentDomain.BaseDirectory,
				UseShellExecute = true,
			})) { }
		}
		catch(Exception) { }
	}

	private async Task OnCreateBatch() {
		try {
			var bat = new StringBuilder()
				.AppendLine("@echo off")
				.AppendLine("pushd \"%~dp0\"")
				.AppendLine()
				.AppendFormat("\"{0}\"", this.Config.Extra.RecognizeExePath).Append(" ").AppendLine(this.GetCommandLine())
				.AppendLine("pause");
			File.WriteAllText(
				global::System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, this.BAT_FILE),
				bat.ToString(),
				Encoding.GetEncoding("Shift_JIS"));

			await Messenger.RaiseAsync(new ConfirmationMessage(
				$"{this.BAT_FILE}を作成しました！",
				"ゆーかねすぴれこ",
				ConfirmationKey) {

				Button = MessageBoxButton.OK,
				Image = MessageBoxImage.Information,
			});
		}
		catch(System.IO.IOException) { }
	}



	private void OnConnectWhisper() {
		this.ConfigBinder.TranscribeModeIndex.Value = ConfigBinder.TranscribeIndexAiWhisper;
		this.ConfigBinder.HpfParamaterIndex.Value = ConfigBinder.HpfIndexHi;
		this.ConfigBinder.MicrophoneRecordMinDurationBinder.Value = "0.8";
	}

	private void OnConnectGoogle() {
		this.ConfigBinder.TranscribeModeIndex.Value = ConfigBinder.TranscribeIndexGoogle;
		this.ConfigBinder.GoogleProfanityFilterBinder.Value = true;
		this.ConfigBinder.HpfParamaterIndex.Value = ConfigBinder.HpfIndexDisable;
		this.ConfigBinder.MicrophoneRecordMinDurationBinder.Value = "";

	}

	private void OnConnectYukarinette() {
		this.ConfigBinder.IsUsedYukarinetteBinding.Value = true;
		this.ConfigBinder.YukarinettePortBinding.Value = "49513";
	}

	private void OnConnectYukaCone() {
		this.ConfigBinder.IsUsedYukaConeBinding.Value = true;
	}


	private void OnMicReload() {
		this.LoadMicList()
			.Subscribe(
				x => {
					this.ConfigBinder.MicDeviceIndex.Value = 0;
				},
				ex => { },
				() => { });
	}

	public async Task OnRuleImport() {
		if(this.SelectedFilterItem.Value != null) {
			var c1 = new ConfirmationMessage(
				"フィルタルールを上書きインポートします。\r\n既存のルールは消去されますのでご注意ください。",
				"ゆーかねすぴれこ",
				ConfirmationKey) {

				Button = MessageBoxButton.OKCancel,
				Image = MessageBoxImage.Warning,
			};
			await Messenger.RaiseAsync(c1);
			if(c1.Response is bool b && b) {
				var c2 = new OpeningFileSelectionMessage(OpenFileKey) {
					Title = "ゆーかねすぴれこ",
					Filter = "ゆーかねすぴれこフィルタルール(.json)|*.json"
				};
				await Messenger.RaiseAsync(c2);
				if(c2.Response is IEnumerable<string> rs && rs.Any()) {
					var file = rs.First();
					if(File.Exists(file)) {
						try {
							var json = File.ReadAllText(file);
							var item = Newtonsoft.Json.JsonConvert.DeserializeObject<Models.FilterExporter>(json);
							System.Diagnostics.Debug.Assert(item != null);
							this.SelectedFilterItem.Value.Rules?.Clear();
							this.SelectedFilterItem.Value.Rules?.AddRangeOnScheduler(item.Rules ?? []);
						}
						catch(Exception ex) when ((ex is Newtonsoft.Json.JsonException) || (ex is IOException)) {
							await Messenger.RaiseAsync(new ConfirmationMessage(
								"フィルタルールフォーマットが間違っています。\r\nインポートに失敗しました。",
								"ゆーかねすぴれこ",
								ConfirmationKey) {

								Button = MessageBoxButton.OK,
								Image = MessageBoxImage.Warning,
							});
						}
					} else {
						this.Config = new();
					}
				}
			}
		}
	}

	public async Task OnRuleExport() {
		if(this.SelectedFilterItem.Value != null) {
			static string safe(string s)
				=> s.Replace('\\', '￥')
					.Replace('/', '／')
					.Replace(':', '：')
					.Replace('*', '＊')
					.Replace('?', '？')
					.Replace('\"', '”')
					.Replace('<', '＜')
					.Replace('>', '＞')
					.Replace('|', '｜');
			var c1 = new SavingFileSelectionMessage(SaveFileKey) {
				Title = "ゆーかねすぴれこ",
				Filter = "(ゆーかねすぴれこフィルタルール(.json))|*.json",
				FileName = this.SelectedFilterItem.Value.Name.Value switch {
					string v when (0 < v.Length) => $"{safe(v)}.json",
					_ => "",
				}
			};
			await Messenger.RaiseAsync(c1);
			if(c1.Response is IEnumerable<string> rs && rs.Any()) {
				var exp = new FilterExporter(this.SelectedFilterItem.Value?.Rules?.ToArray() ?? []);
				var file = rs.First();
				var json = Newtonsoft.Json.JsonConvert.SerializeObject(exp);
				File.WriteAllText(file, json);
			}
		}
	}
}