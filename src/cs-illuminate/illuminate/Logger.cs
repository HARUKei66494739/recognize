using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Reactive.Linq;

namespace Haru.Kei;
class Logger {
	public static Logger Current { get; } = new();

	private System.Reactive.Concurrency.EventLoopScheduler LogScheduler { get; } = new();
	private Stream? _stream;
	private string? _filePath;

	public void Info(object s) {
		this.Write($"{Prefix()}[i]{s}\r\n");
	}

	public void Debug(object s) {
		this.Write($"{Prefix()}[d]{s}\r\n");
	}

	private void Write(string text) {
		Observable.Return(text)
			.SubscribeOn(LogScheduler)
			.Subscribe(x => {
				var st = Get();
				st.Write(System.Text.Encoding.UTF8.GetBytes(text));
				st.Flush();
			});
	}

	private string Prefix() {
		var pid = Process.GetCurrentProcess().Id;
		var tid = Thread.CurrentThread.ManagedThreadId;
		var time = DateTime.Now.ToString("yyyy/MM/dd hh:mm:ss", System.Globalization.CultureInfo.InvariantCulture);
		return $"{time}[{pid}][{tid}]";
	}

	public void SetTarget(string? filePath) {
		this._filePath = filePath;
	}

	private Stream Get() {
		if (this._stream == null) {
			if ((this._filePath == null) || !File.Exists(this._filePath)) {
				this._stream = new FileStream(Path.Combine(AppContext.BaseDirectory, "illuminate.log"), FileMode.Create, FileAccess.ReadWrite, FileShare.Read);
			} else {
				this._stream = new FileStream(this._filePath, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.Read);
			}
		}
		return this._stream;
	}
}
