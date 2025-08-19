using System;
using System.Runtime.InteropServices;
using System.Text;
using System.Diagnostics;
using System.ComponentModel;
using System.IO;
using System.Windows.Automation;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Security.Cryptography;
using System.Collections.Generic;
using System.Reactive.Linq;
using System.Threading;
using System.Windows.Threading;

using CommandLine;
using Fleck;

namespace Haru.Kei;
class Program {
	class MessageForm : Form {
		private System.Reactive.Concurrency.EventLoopScheduler SpeechScheduler { get; } = new();
		private readonly Models.CommandOptions opt;
		private readonly Models.IClient client;
		private readonly Models.IVoiceWaitable capture;
		private readonly CancellationTokenSource cancellationSource;
		private readonly AutoResetEvent autoResetEvent = new(false);
		private readonly NotifyIcon notifyIcon = new();
		private IDisposable wsSubscriber;
		private IDisposable? masterMoniter = null;

		[DllImport("shell32.dll", CharSet = CharSet.Unicode)]
		private static extern uint ExtractIconEx(string pszFile, uint nIconIndex, out nint phIconLarge, out nint phIconSmall, uint nIcons);

		public MessageForm(Models.CommandOptions opt) {
			this.FormBorderStyle = FormBorderStyle.None;
			this.Opacity = 0;
			this.ControlBox = false;
			this.ShowInTaskbar = false;

			this.opt = opt;
			this.client = Models.IClient.Get(opt, Logger.Current);
			this.client.StartClient(this.opt.Launch);
			this.capture = Models.IVoiceWaitable.Get(opt, this.client);
			cancellationSource = new CancellationTokenSource();

			// ウェブソケット
			wsSubscriber = Observable.Create<(Models.RecognitionObject Json, IWebSocketConnection Socket)>(oo => {
				try {
					using var server = new WebSocketServer($"ws://127.0.0.1:{this.opt.Port}");

					IWebSocketConnection? soc = null;
					server.Start(socket => {
						soc = socket;
						Logger.Current.Info("WebSocketサーバが起動しました");
						socket.OnMessage = message => {
							try {
								Logger.Current.Info($"メッセージ受信=>{message}");
								if (message == "ping") {
									var _ = socket.Send("pong");
								} else {
									var json = Newtonsoft.Json.JsonConvert.DeserializeObject<Models.RecognitionObject?>(message);
									if (json != null) {
										oo.OnNext((json, socket));
									}
								}
							}
							catch (Exception e) {
								Logger.Current.Info("WebSocket送信で予期しない例外");
								Logger.Current.Info(e);
							}
						};
					});
					cancellationSource.Token.WaitHandle.WaitOne();
					Logger.Current.Info("WebSocketサーバをシャットダウンします。");
					try {
						soc?.Send("exit").Wait();
					}
					catch (AggregateException) { }
				}
				finally { }
				return System.Reactive.Disposables.Disposable.Empty;
			}) .ObserveOn(this.SpeechScheduler)
				.SubscribeOn(System.Reactive.Concurrency.TaskPoolScheduler.Default)
				.Subscribe(async x => {
					if (SynchronizationContext.Current == null) {
						SynchronizationContext.SetSynchronizationContext(
							new DispatcherSynchronizationContext());
					}

					if (string.IsNullOrWhiteSpace(x.Json.Transcript)) {
						Logger.Current.Info($"読み上げは空文字列です。スキップします");
						return;
					}

					try {
						try {
							_ = x.Socket.Send(Newtonsoft.Json.JsonConvert.SerializeObject(new Models.RecognitionObject() {
								Transcript = x.Json.Transcript,
								Translate = x.Json.Translate,
								IsFinish = false,
							}));
						}
						catch (Exception e) {
							Logger.Current.Info("WebSocket返信で予期しない例外");
							Logger.Current.Info(e);
						}

						await RunVoiceRoid(x.Json);
					}
					finally {
						try {
							_ = x.Socket.Send(Newtonsoft.Json.JsonConvert.SerializeObject(new Models.RecognitionObject() {
								Transcript = x.Json.Transcript,
								Translate = x.Json.Translate,
								IsFinish = true,
							}));
						}
						catch (Exception e) {
							Logger.Current.Info("WebSocket返信で予期しない例外");
							Logger.Current.Info(e);
						}
					}
				});

			// 親プロセスの死活監視
			if (opt.Master != 0) {
				masterMoniter = RunLifeMoniter(opt.Master);
			}
		}

		private async Task RunVoiceRoid(Models.RecognitionObject recogObj) {
			var transcript = this.opt.Kana switch {
				true => KanaConv.Current.Convert(recogObj.Transcript),
				false => recogObj.Transcript,
			};
			if (this.opt.Kana) {
				Logger.Current.Info($"カナ変換:{recogObj.Transcript} => {transcript}");
			}

			try {
				Logger.Current.Info($"合成音声呼び出し開始:{transcript}");
				this.autoResetEvent.Reset();
				try {
					this.client.BeginSpeech(transcript);
				}
				catch (VoiceLink.VoiceLinkException e) {
					Logger.Current.Info($"！！合成音声クライアントの読み上げ準備に失敗しました");
					Logger.Current.Info($"{e}");
					return;
				}

				try {
					if (await this.capture.Prepare()) {
						this.capture.Start();
						_ = Task.Run(() => {
							this.capture.Wait();
							this.capture.Stop();
							this.autoResetEvent.Set();
						});
						this.client.Speech(transcript);
						this.autoResetEvent.WaitOne();
					} else {
						Logger.Current.Info($"！！音声キャプチャの準備ができていません。スキップします");
					}
				}
				catch (VoiceLink.VoiceLinkException e) {
					Logger.Current.Info($"！！合成音声クライアントの呼び出しに失敗");
					Logger.Current.Info($"{e}");
				}
				finally {
					try {
						this.capture?.Stop();
						this.client.EndSpeech(transcript);
					}
					catch (VoiceLink.VoiceLinkException) { }
				}

			}
			finally {
				Logger.Current.Info($"合成音声呼び出し終了:{transcript}");
			}
		}

		private IDisposable? RunLifeMoniter(int targetPid) {
			try {
				var p = Process.GetProcessById(opt.Master);
				return Observable.Interval(TimeSpan.FromMilliseconds(100))
					.Subscribe(_ => {
						try {
							if (p.HasExited) {
								Logger.Current.Info("親プロセスの終了を確認しました");
								Application.Exit();
								masterMoniter?.Dispose();
							}
						}
						catch { }
					});
			}
			catch { }
			return default;
		}

		protected override async void OnLoad(EventArgs e) {
			base.OnLoad(e);

			if (this.opt.NotifyIcon) {
				var menu = new ContextMenuStrip();
				// 表示メニュー項目の追加
				var mItem = new ToolStripMenuItem("終了");
				mItem.Click += (_, _) => { Application.Exit(); };
				menu.Items.Add(mItem);

				ExtractIconEx(
					Process.GetCurrentProcess().MainModule?.FileName ?? "",
					0,
					out var hIcon,
					out var hIconSmall,
					1);
				this.notifyIcon.Text = "ゆーかねすぴれこ/illuminate";
				this.notifyIcon.Icon = System.Drawing.Icon.FromHandle(hIcon);
				this.notifyIcon.ContextMenuStrip = menu;
				this.notifyIcon.Visible = true;
			}

			var _ = this.capture.LoadFromUi();
			await Task.Delay(500);
			this.Hide();
		}

		protected override void OnFormClosed(FormClosedEventArgs e) {
			base.OnFormClosed(e);
			this.cancellationSource.Cancel();
			this.notifyIcon.Dispose();
			this.wsSubscriber.Dispose();
			this.masterMoniter?.Dispose();
			Application.Exit();
		}
	}

	[STAThread]
	static int Main(string[] args) {
		/* ボイロ各種パスメモ
		const string VoiceRoidExKiritan = @"C:\Program Files (x86)\AHS\VOICEROID+\KiritanEX\VOICEROID.exe";
		const string VoiceRoid2 = @"C:\Program Files (x86)\AHS\VOICEROID2\VoiceroidEditor.exe";
		const string VoicePeak = @"C:\Program Files\VOICEPEAK\voicepeak.exe";
		const string AiVoice = @"C:\Program Files\AI\AIVoice\AIVoiceEditor\AIVoiceEditor.exe";
		const string AiVoice2 = @"C:\Program Files\AI\AIVoice2\AIVoice2Editor\aivoice.exe";
		*/

		var result = Parser.Default.ParseArguments<Models.CommandOptions>(args);
		if (result.Tag == ParserResultType.Parsed) {
			var parsed = (Parsed<Models.CommandOptions>)result;
			if (parsed != null) {
				AppDomain.CurrentDomain.UnhandledException += (_, e) => {
					Logger.Current.Info("致命的なエラー");
					Logger.Current.Info(e.ExceptionObject);
				};

				Logger.Current.Info("illuminateが起動しました");
				Logger.Current.Info(string.Join(' ', args));

				{
					var vld = parsed.Value.Validate();
					if (!vld.IsValid) {
						throw new InvalidOperationException($"コマンドラインに不正な値があります{Environment.NewLine}{Environment.NewLine}{vld.ErrorText}");
					}
				}

				ApplicationConfiguration.Initialize();
				Application.Run(new MessageForm(parsed.Value));
				return 0;
			}
		} else {
			/*
			// パース失敗時
			var notParsed = (NotParsed<Options>)result;
			// 処理
			*/
		}
		return 1;
	}
}
