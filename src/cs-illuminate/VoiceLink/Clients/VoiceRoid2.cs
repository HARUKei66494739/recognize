using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Forms.Automation;

namespace VoiceLink.Clients;
public class VoiceRoid2 : VoiceRoid<AudioCaptreStart, NopVoiceObject> {
	private readonly string VoiceRoid2EditorClass = "HwndWrapper[VoiceroidEditor.exe;;4cc5cceb-49d9-4fbf-8374-11d461e38c4c]";
	private string exe = "";
	private nint hTargetWindow;
	private Interop.ComObject<Accessibility.IAccessible>? textBox;
	private Interop.ComObject<Accessibility.IAccessible>? playButton;
	private Interop.ComObject<Accessibility.IAccessible>? stopButton;
	private Interop.ComObject<Accessibility.IAccessible>? caretStartButton;

	public override bool StartClient(bool isLaunch, AudioCaptreStart extra) {
		this.exe = extra.TargetExe;
		return this.Load(this.exe, isLaunch);
	}

	private bool Load(string targetExe, bool isLaunch) {
		this.ProcessId = 0;
		this.hTargetWindow = 0;

		var p = Util.GetProcess(targetExe);
		var h = p?.MainWindowHandle ?? 0;
		if (p == null) {
			/* スプラッシュスクリーンが出るのでこれじゃダメ
			var pp = isLaunch switch {
				true => Util.LaunchProcess(targetExe, (x) => x.ToLower().StartsWith(VoiceRoid2EditorClass.ToLower())),
				false => null,
			};
			if (pp == null) {
				return false;
			}
			p = pp.Value.Proc;
			h = pp.Value.WindowHandle;
			*/
			return false;
		}
		this.ProcessId = p.Id;
		this.hTargetWindow = h;
		return true;
	}

	public override void EndClient() {}


	public override void BeginSpeech(string text, NopVoiceObject extra) {
		if(!Interop.IsWindow(this.hTargetWindow)) {
			this.Load(this.exe, false);
			if (this.hTargetWindow == 0) {
				throw new VoiceLinkException("VoiceRoid2が見つかりません");
			}
		}

		this.textBox?.Dispose();
		this.playButton?.Dispose();
		this.stopButton?.Dispose();
		this.caretStartButton?.Dispose();
		this.textBox
			= this.playButton
			= this.stopButton
			= this.caretStartButton
			= null;
		_ = Interop.AccessibleObjectFromWindow(
			this.hTargetWindow,
			0,
			in Interop.IID_IAccessible,
			out var o
			);
		if (o is Accessibility.IAccessible acc) {
			object[]? obj1 = default;
			object[]? obj2 = default;
			object?[]? obj3 = default;
			try {
				obj1 = new object[acc.accChildCount];
				_ = Interop.AccessibleChildren(acc, 0, obj1.Length, obj1, out var c);
				if ((obj1.Length != c) || (c < 3)) {
					throw new VoiceLinkException("VoiceRoid2オブジェクトの取得に失敗(1/3)");
				}

				var acc2 = (Accessibility.IAccessible)obj1[3];
				obj2 = new object[acc2.accChildCount];
				_ = Interop.AccessibleChildren(acc2, 0, obj2.Length, obj2, out c);
				if ((obj2.Length != c) || (c < 3)) {
					throw new VoiceLinkException("VoiceRoid2オブジェクトの取得に失敗(2/3)");
				}

				var acc3 = (Accessibility.IAccessible)obj2[3];
				{
					var _obj3 = new object[acc3.accChildCount];
					_ = Interop.AccessibleChildren(acc3, 0, _obj3.Length, _obj3, out c);
					obj3 = _obj3;
				}
				if ((obj3.Length != c) || (c < 2)) {
					throw new VoiceLinkException("VoiceRoid2オブジェクトの取得に失敗(3/3)");
				}

				if(obj3[0] is not Accessibility.IAccessible obj3_0) {
					LogDebug("テキストボックスのインスタンスが不正");
					throw new VoiceLinkException("VoiceRoid2オブジェクトの取得において想定しないケース[0]");
				}
				if (obj3[1] is not Accessibility.IAccessible obj3_1) {
					LogDebug("再生ボタンのインスタンスが不正");
					throw new VoiceLinkException("VoiceRoid2オブジェクトの取得において想定しないケース[1]");
				}
				if (obj3[2] is not Accessibility.IAccessible obj3_2) {
					LogDebug("停止ボタンのインスタンスが不正");
					throw new VoiceLinkException("VoiceRoid2オブジェクトの取得において想定しないケース[2]");
				}
				if (obj3[3] is not Accessibility.IAccessible obj3_3) {
					LogDebug("先頭ボタンのインスタンスが不正");
					throw new VoiceLinkException("VoiceRoid2オブジェクトの取得において想定しないケース[3]");
				}

				this.textBox = new(obj3_0);
				this.playButton = new(obj3_1);
				this.stopButton = new(obj3_2);
				this.caretStartButton = new(obj3_3);
				obj3[0] = obj3[1] = obj3[2] = obj3[3] = null; 

				return;
			}
			finally {
				static void range<T>(List<T> list, IEnumerable<T>? it) {
					if (it != null) {
						list.AddRange(it);
					}
				}
				var rls = (obj3 ?? []).ToList<object?>();
				range(rls, obj2);
				range(rls, obj1);
				rls.Add(o);

				foreach (var it in rls) {
					if ((it != null) && Marshal.IsComObject(it)) {
						Marshal.ReleaseComObject(it);
					}
				}
			}
		}
		System.Threading.Thread.Sleep(1000);
		throw new VoiceLinkException("読み上げ開始準備に失敗");
	}

	public override void Speech(string text, NopVoiceObject extra) {
		if ((this.textBox == null) || (this.playButton == null) || (this.caretStartButton == null)) {
			throw new VoiceLinkException("");
		}

		this.FocusVoiceRoid2();
		for (int i = 0; i < 10; i++) {
			try {
				var s = this.textBox.Ptr.accValue[0];
				if (string.IsNullOrEmpty(s)) {
					break;
				} else {
					LogDebug($"以前のテキストが残っています=>{s}");
					Thread.Sleep(500);
				}
			}
			catch(COMException e) {
				LogDebug("テキスト取得に失敗");
				LogDebug($"{e}");
			}
			try {
				this.textBox.Ptr.accValue[0] = "";
			}
			catch (COMException e) {
				LogDebug("テキスト初期化に失敗");
				LogDebug($"{e}");
			}
		}

		if (this.textBox.Ptr.accValue[0] != "") {
			//LogDebug("なにか文字が残っています");
			//throw new VoiceLinkException($"VoiceRoid2読み上げ連携に失敗(0/2)");
		}

		foreach (var it in new (int Index, Action Action)[] {
			(1, () => { this.textBox.Ptr.accSelect(0x1, 0); this.textBox.Ptr.accValue[0] = text; }),
			(2, () => { this.playButton.Ptr.accSelect(0x1, 0); this.playButton.Ptr.accDoDefaultAction(0); }),
		}) {
			try {
				it.Action();
			}
			catch (COMException e) {
				// 0x80040200が確認されている
				System.Threading.Thread.Sleep(1000);
				throw new VoiceLinkException($"VoiceRoid2読み上げ連携に失敗({it.Index}/2)", e);
			}
		}

		// 読み上げ開始まち
		// 読み上げ文章が十分に短い場合ステート判定が失敗することがある
		const int timeoutMiliSec = 500;
		var time = DateTime.Now;
		while ((DateTime.Now - time).TotalMilliseconds < timeoutMiliSec) {
			if (this.IsSpeak()) {
				break;
			}
			Thread.Sleep(10);
		}
	}

	public override void EndSpeech(string text, NopVoiceObject extra) {
		try {
			if (this.textBox == null) {
				return;
			}
			try {
				this.stopButton?.Ptr.accDoDefaultAction(0);
			}
			catch (Exception e) {
				LogDebug("停止ボタン呼び出しに失敗");
				LogDebug($"{e}");
				System.Threading.Thread.Sleep(1000);
			}

			this.FocusVoiceRoid2();
			// 5回試行する
			for (var i = 0; i < 5; i++) {
				try {
					this.textBox.Ptr.accValue[0] = "";
					break;
				}
				catch (Exception e) {
					LogDebug("テキストボックス初期化に失敗");
					LogDebug($"{e}");
					System.Threading.Thread.Sleep(200);
				}
			}
		}
		finally {
			this.textBox?.Dispose();
			this.playButton?.Dispose();
			this.stopButton?.Dispose();
			this.caretStartButton?.Dispose();

			this.textBox
				= this.playButton
				= this.stopButton
				= this.caretStartButton
				= null;
		}
	}

	private bool IsSpeak() {
		if (this.caretStartButton != null) {
			try {
				var state = (int)this.caretStartButton.Ptr.accState[0];
				if (state == 0x1) {
					return true;
				}
			}
			catch(COMException e) {
				LogDebug("再生状況の取得に失敗");
				LogDebug($"{e}");
			}
		}
		return false;
	}

	/// <summary>ボイロ2エディタのテキストボックスに強引にフォーカスを移す</summary>
	private void FocusVoiceRoid2() {
		if (this.textBox != null) {
			this.textBox.Ptr.accLocation(
				out int pxLeft,
				out int pyTop,
				out int pcxWidth,
				out int pcyHeight,
				0);
			var pt = new Interop.POINT() {
				x = pxLeft,
				y = pyTop,
			};
			Interop.ScreenToClient(hTargetWindow, ref pt);
			Util.PlatformClick(
				this.hTargetWindow,
				pt.x + 4,
				pt.y + 4);
		}
	}
}

