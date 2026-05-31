using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reactive.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using static System.Net.Mime.MediaTypeNames;

namespace Haru.Kei;
class Logger {
	public static Logger Current { get; } = new();
	public static string GenRotateLogFileName() =>
		$"{DefaultLogName}.{DateTime.Now.ToString("yyyy-MM-dd_HH-mm-ss", System.Globalization.CultureInfo.InvariantCulture)}.log";

	private const string DefaultLogName= "illuminate";
	private const string DefaultLogFile = $"{DefaultLogName}.log";
	private System.Reactive.Concurrency.EventLoopScheduler LogScheduler { get; } = new();
	private Stream? logStream;
	private MemoryStream memoryStream = new();

	public async void Init(string? logFileName = null) {
		this.logStream = new FileStream(
			Path.Combine(AppContext.BaseDirectory, logFileName ?? DefaultLogFile),
			FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.Read);
		if(0 < this.memoryStream.Position) {
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
