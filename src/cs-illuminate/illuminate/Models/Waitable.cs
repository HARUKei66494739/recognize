using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace Haru.Kei.Models;
interface IVoiceWaitable {
	public Task LoadFromUi();
	public Task<bool> Prepare();
	public void Start();
	public void Wait();
	public void Stop();


	public static IVoiceWaitable Get(CommandOptions opt, IClient client) {
		return client switch {
			VoiroClinet v => new AudioCaptureWait(opt, v.VoiceClient),
			CeVioClinet => new NopWait(),
			_ => throw new NotImplementedException($"不正な合成音声{opt.Voice}"),
		};
	}
}

internal class NopWait : IVoiceWaitable {
	public Task LoadFromUi() { return Task.Delay(0); }

	public async Task<bool> Prepare() {
		await Task.Yield();
		return true;
	}

	public void Start() { }
	public void Stop() { }
	public void Wait() { }
}

internal class AudioCaptureWait : IVoiceWaitable {
	private readonly CommandOptions opt;
	private readonly VoiceLink.IVoiceClient<VoiceLink.AudioCaptreStart, VoiceLink.NopVoiceObject, VoiceLink.IAudioCaptireClient> voiceClient;
	private int targetProcess;
	private ApplicationCapture? capture;

	public AudioCaptureWait(CommandOptions opt, VoiceLink.IVoiceClient<VoiceLink.AudioCaptreStart, VoiceLink.NopVoiceObject, VoiceLink.IAudioCaptireClient> voiceClient) {
		this.opt = opt;
		this.voiceClient = voiceClient;
		this.targetProcess = voiceClient.ClientParameter.ProcessId;
	}

	public Task LoadFromUi() {
		ApplicationCapture.UiInitilize();
		return Task.Run(async () => {
			// UIが止まるのでスレッドを起動する
			this.capture = await ApplicationCapture.Get(this.targetProcess, this.opt.GetCaptureParam());
		});
	}

	public async Task<bool> Prepare() {
		if ((this.capture == null && this.targetProcess != 0)
			|| (this.targetProcess != this.voiceClient.ClientParameter.ProcessId)) {

			Logger.Current.Info($"！！合成音声クライアントの再起動が確認されました");
			this.targetProcess = this.voiceClient.ClientParameter.ProcessId;
			this.capture = await ApplicationCapture.Get(this.targetProcess, this.opt.GetCaptureParam());
		}
		return this.capture != null;
	}

	public void Start() => this.capture?.Start();
	public void Wait() => this.capture?.Wait();
	public void Stop() => this.capture?.Stop();
}