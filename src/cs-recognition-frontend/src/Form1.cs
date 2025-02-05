using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Collections.Generic;
using System.Windows.Forms;
using System.Reflection;
using System.ComponentModel;
using System.Xml.Linq;
using System.Diagnostics;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Security;

namespace Haru.Kei {
	public partial class Form1 : Form {
		[DllImport("user32.dll", CharSet = CharSet.Unicode)]
		private static extern IntPtr SendMessage(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam);
		[DllImport("shell32.dll", CharSet = CharSet.Unicode)]
		private static extern uint ExtractIconEx(string pszFile, uint nIconIndex, out IntPtr phIconLarge, out IntPtr phIconSmall, uint nIcons);
		private const int WM_SETICON = 0x0080;
		private const int ICON_BIG = 1;
		private const int ICON_SMALL = 0;

		private readonly string CONFIG_FILE = "frontend.conf";
		private readonly string BAT_FILE = "custom-recognize.bat";
		private readonly string TEMP_BAT = Path.Combine(Path.GetTempPath(), string.Format("recognize-gui-{0}.bat", Guid.NewGuid()));

		private RecognizeExeArgument arg;
		public Form1() {
			InitializeComponent();

			IntPtr hIcon;
			IntPtr hIconSmall;
			ExtractIconEx(
				Process.GetCurrentProcess().MainModule.FileName,
				0,
				out hIcon,
				out hIconSmall,
				1);
			SendMessage(this.Handle, WM_SETICON, (IntPtr)ICON_BIG, hIcon);
			SendMessage(this.Handle, WM_SETICON, (IntPtr)ICON_SMALL, hIconSmall);

			this.batToolStripMenuItem.Click += (_, __) => {
				try {
					var bat = new StringBuilder()
						.AppendLine("@echo off")
						.AppendLine("pushd \"%~dp0\"")
						.AppendLine()
						.AppendFormat("\"{0}\"", this.arg.RecognizeExePath).Append(" ").AppendLine(this.GenExeArguments(this.arg))
						.AppendLine("pause");
					File.WriteAllText(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, this.BAT_FILE), bat.ToString(), Encoding.GetEncoding("Shift_JIS"));
					MessageBox.Show(this, string.Format("{0}を作成しました！", this.BAT_FILE), "成功", MessageBoxButtons.OK, MessageBoxIcon.Information);
				}
				catch(System.IO.IOException) { }
			};
			this.testmicToolStripMenuItem.Click += (_, __) => {
				var properties = this.arg.GetType().GetProperties();
				try {
					using(System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo() {
						FileName = this.arg.RecognizeExePath,
						Arguments = string.Format("--test mic {0}", this.GenExeArguments(this.arg)),
						UseShellExecute = true,
					})) { }
				}
				catch(Exception) { }
			};
			testambientToolStripMenuItem.Click += (_, __) => {
				using(System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo() {
					FileName = this.arg.RecognizeExePath,
					Arguments = string.Format("--test mic_ambient {0}", this.GenExeArguments(this.arg)),
					UseShellExecute = true,
				})) { }
			};
			this.exitToolStripMenuItem.Click += (_, __) => this.Close();

			this.whisperToolStripMenuItem.Click+= (_, __) => {
				this.arg.ArgMethod = "kotoba_whisper";
				this.arg.ArgHpfParamaterV2 = HpfArgGenerater.HpfParamater.強め.ToString();
				this.arg.ArgVadParamaterV2 = "0";
				this.propertyGrid.Refresh();
			};
			this.googleToolStripMenuItem.Click += (_, __) => {
				this.arg.ArgMethod = "google_mix";
				this.arg.ArgGoogleProfanityFilter = true;
				this.arg.ArgHpfParamaterV2 = HpfArgGenerater.HpfParamater.無効.ToString();
				this.arg.ArgVadParamaterV2 = "0";
				this.propertyGrid.Refresh();
			};
			this.yukarinetteToolStripMenuItem.Click += (_, __) => {
				this.arg.ArgOut = "yukarinette";
				if(!this.arg.ArgOutYukarinette.HasValue) {
					this.arg.ArgOutYukarinette = 49513;
				}
				this.propertyGrid.Refresh();
			};
			this.yukaconeToolStripMenuItem.Click += (_, __) => {
				this.arg.ArgOut = "yukacone";
				this.propertyGrid.Refresh();
			};

			this.button.Click += (_, __) => {
				this.SaveConfig(this.arg);

				var bat = new StringBuilder()
					.AppendLine("@echo off")
					.AppendLine()
					.AppendFormat("\"{0}\"", this.arg.RecognizeExePath).Append(" ").AppendLine(this.GenExeArguments(this.arg))
					.AppendLine("if %ERRORLEVEL% neq 0 (")
					.AppendLine("  pause")
					.AppendLine(")");
				File.WriteAllText(this.TEMP_BAT, bat.ToString(), Encoding.GetEncoding("Shift_JIS"));


				try {
					/*
					using(System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo() {
						FileName = this.arg.RecognizeExePath,
						Arguments = this.GenExeArguments(this.arg),
						UseShellExecute = true,
					})) { }
					*/
					using(System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo() {
						FileName = this.TEMP_BAT,
						WorkingDirectory = AppDomain.CurrentDomain.BaseDirectory,
						UseShellExecute = true,
					})) { }

				}
				catch(Exception) { }
			};
		}

		protected override void OnLoad(EventArgs e) {
			base.OnLoad(e);

			var convDic = new Dictionary<Type, Func<string, object>>();
			convDic.Add(typeof(string), (x) => x);
			convDic.Add(typeof(bool?), (x) => {
				bool v;
				return bool.TryParse(x, out v) ? (object)v : null;
			});
			convDic.Add(typeof(int?), (x) => {
				int v;
				return int.TryParse(x, out v) ? (object)v : null;
			});
			convDic.Add(typeof(float?), (x) => {
				float v;
				return float.TryParse(x, out v) ? (object)v : null;
			});

			var isVesionUp = false;
			var list = new List<Tuple<string, string>>();
			try {
				var save = File.ReadAllText(System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, this.CONFIG_FILE));
				foreach(var line in save.Replace("\r\n", "\n").Split('\n')) {
					var c = line.IndexOf(':');
					if(0 < c) {
						var tp = new Tuple<string, string>(line.Substring(0, c), line.Substring(c + 1));
						list.Add(tp);


						if(tp.Item1.ToLower() == "version") {
							int ver;
							if(int.TryParse(tp.Item2, out ver) && ver < RecognizeExeArgument.FormatVersion) {
								isVesionUp = true;
							}
						}
					}
				}
			}
			catch(IOException) {}

			var prop = typeof(RecognizeExeArgument).GetProperties().Where(x => x.CanWrite);
			var pr = typeof(RecognizeExeArgument).GetProperty("RecognizeExePath");
			var exe = list.Where(x => x.Item1 == pr.Name).FirstOrDefault();
			this.arg = RecognizeExeArgumentEx.Init((exe != null) ? exe.Item2 : (string)pr.GetCustomAttribute<DefaultValueAttribute>().Value);
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
							p.SetValue(this.arg, v);
						}
					}
				}
			}
			this.propertyGrid.SelectedObject = this.arg;
			if(isVesionUp) {
				MessageBox.Show(
					this,
					"設定が更新されています。内容を確認してね",
					"ゆーかねすぴれこ",
					MessageBoxButtons.OK,
					MessageBoxIcon.Information);
			}
			if(!IsValidExePath(this.arg)) {
				MessageBox.Show(
					this,
					"パスに不正な文字が含まれます。ゆーかねすぴれこは英数字だけのパスに配置してください。",
					"ゆーかねすぴれこ",
					MessageBoxButtons.OK,
					MessageBoxIcon.Warning);
				Application.Exit();
			}
		}

		protected override void OnFormClosed(FormClosedEventArgs e) {
			this.SaveConfig(this.arg);
			try {
				if(File.Exists(this.TEMP_BAT)) {
					File.Delete(this.TEMP_BAT);
				}
			}
			catch(IOException) {}

			base.OnFormClosed(e);
		}

		private bool IsValidExePath(RecognizeExeArgument argument) {
			try {
				var path = Path.GetFullPath(argument.RecognizeExePath);
				if(path.ToLower() != arg.RecognizeExePath.ToLower()) {
					// exeは相対パス
					// 作業ディレクトリがexeのディレクトリとは限らないので作り直す
					path = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, arg.RecognizeExePath);
				} else {
					// exeはフルパス
				}

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

		private string GenExeArguments(RecognizeExeArgument argument) {
			var araguments = new StringBuilder();
			foreach(var p in argument.GetType().GetProperties()) {
				var att = p.GetCustomAttribute<ArgAttribute>();
				if(att != null) {
					var opt = att.Generate(p.GetValue(this.arg, null), this.arg);
					if(!string.IsNullOrEmpty(opt)) {
						araguments.Append(" ").Append(opt);
					}
				}
			}
			if(!string.IsNullOrEmpty(argument.ExtraArgument)) {
				araguments.Append(" ")
					.Append(argument.ExtraArgument);
			}
			return araguments.ToString();
		}

		private void SaveConfig(RecognizeExeArgument argument) {
			try {
				var save = new StringBuilder();
				var dict = new  Dictionary<string, string>();
				foreach(var p in argument.GetType().GetProperties()) {
					var dfattr = p.GetCustomAttribute<DefaultValueAttribute>();
					if(dfattr != null) {
						var pv = p.GetValue(this.arg, null);
						var dv = dfattr.Value;
						if((pv != null) && !pv.Equals(dv)) {
							var svattr = p.GetCustomAttribute<SaveAttribute>();
							if((svattr != null) && !svattr.IsSave) {
								continue;
							}
							dict.Add(p.Name, pv.ToString());
							continue;
						}
						//if((dv != null) && !dv.Equals(pv)) {
						//	save.Append(p.Name).Append(":").AppendLine(pv.ToString());
						//	continue;
						//}
					}
				}

				foreach(var p in argument.GetType().GetProperties()) {
					var svattr = p.GetCustomAttribute<SaveAttribute>();
					var pv = p.GetValue(this.arg, null);
					if((pv != null) && (svattr != null) && svattr.IsSave) {
						if(!dict.ContainsKey(p.Name)) {
							dict.Add(p.Name, pv.ToString());
							continue;
						}
					}
				}

				foreach(var key in  dict.Keys) {
					save.Append(key).Append(":").AppendLine(dict[key]);
				}
				File.WriteAllText(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, this.CONFIG_FILE), save.ToString());
			}
			catch(IOException) { }
		}
	}
}
