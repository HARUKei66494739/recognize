using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reactive.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace Haru.Kei.Shared.Utils;
internal interface ILoggerProvider {
	public string BaseLogName { get; }

	public string GetLogFileName();

	public string GenRotateLogFileName() =>
		$"{BaseLogName}.{DateTime.Now.ToString("yyyy-MM-dd_HH-mm-ss", System.Globalization.CultureInfo.InvariantCulture)}";
}


internal class Logger<T> where T:class, ILoggerProvider, new()  {
	public static Logger<T> Current { get; } = new();

	private readonly T LogProvider = new();
	private readonly string DefaultLogFile;
	private System.Reactive.Concurrency.EventLoopScheduler LogScheduler { get; } = new();
	private Stream? logStream;
	private MemoryStream memoryStream = new();

	public Logger() {
		this.DefaultLogFile = $"{this.LogProvider.GetLogFileName()}.log";
	}

	public async void Init(string? logFileName = null) {
		this.logStream = new FileStream(
			Path.Combine(AppContext.BaseDirectory, logFileName ?? DefaultLogFile),
			FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.Read);
		if (0 < this.memoryStream.Position) {
			var ary = this.memoryStream.ToArray();
			this.memoryStream.Seek(0, SeekOrigin.Begin);
			this.memoryStream.SetLength(0);
			await this.logStream.WriteAsync(ary, 0, ary.Length);
		}
	}

	public void Info(object s) {
		this.WriteOnScheduler($"{Prefix()}[i]{s}\r\n");
	}

	public void Debug(object s) {
		this.WriteOnScheduler($"{Prefix()}[d]{s}\r\n");
	}

	public void Error(object s) {
		this.WriteOnScheduler($"{Prefix()}[e]{s}\r\n");
	}

	public void ErrorSync(object s) {
		this.WriteCore(
			data: Encoding.UTF8.GetBytes($"{Prefix()}[e]{s}\r\n"),
			writeStream: this.Get());
	}

	private void WriteOnScheduler(string text, Stream? writeStream = null) {
		this.WriteOnScheduler(
			data: Encoding.UTF8.GetBytes(text),
			writeStream: writeStream);
	}

	private void WriteOnScheduler(byte[] data, Stream? writeStream = null) {
		Observable.Return((Data: data, Stream: writeStream))
			.SubscribeOn(LogScheduler)
			.Subscribe(x => {
				this.WriteCore(x.Data, x.Stream ?? Get());
			});
	}

	private void WriteCore(byte[] data, Stream writeStream) {
		writeStream.Write(data);
		writeStream.Flush();
	}

	private string Prefix() {
		var pid = Process.GetCurrentProcess().Id;
		var tid = Thread.CurrentThread.ManagedThreadId;
		var time = DateTime.Now.ToString("yyyy/MM/dd HH:mm:ss", System.Globalization.CultureInfo.InvariantCulture);
		return $"{time}[{pid}][{tid}]";
	}

	private Stream Get() {
		return this.logStream switch {
			{ } v => v,
			_ => this.memoryStream,
		};
	}
}
