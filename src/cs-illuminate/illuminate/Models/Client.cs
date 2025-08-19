using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

using NAudio.CoreAudioApi;
using NAudio.Wave;


namespace Haru.Kei.Models;
internal interface IClient {
	public void StartClient(bool isLaunch);
	public void EndClinet();
	public void BeginSpeech(string text);
	public void Speech(string text);
	public void EndSpeech(string text);

	public static IClient Get(CommandOptions opt, Logger logger) {
		void info(string s) => logger.Info($"[VoiceLink]{s}");
		void debug(string s) => logger.Debug($"[VoiceLink]{s}");
		void setLogger(VoiceLink.IVoiceLogger lgr) {
			lgr.LogInfo = info;
			if (opt.Debug) {
				lgr.LogDebug = debug;
			}
		}

		// ボイロ系
		{
			if (opt.Voice switch {
				CommandOptions.VoiceClientType.voiceroid => new VoiroClinet(opt),
				CommandOptions.VoiceClientType.voiceroid2 => new VoiroClinet(opt),
				CommandOptions.VoiceClientType.voicepeak => new VoiroClinet(opt),
				CommandOptions.VoiceClientType.aivoice => new VoiroClinet(opt),
				CommandOptions.VoiceClientType.aivoice2 => new VoiroClinet(opt),
				_ => null,
			} is VoiroClinet c) {
				setLogger(c.VoiceClient);
				return c;
			}
		}

		// CeVIO系
		{
			if(opt.Voice switch {
				CommandOptions.VoiceClientType.ceviocs => new CeVioClinet(opt),
				CommandOptions.VoiceClientType.cevioai => new CeVioClinet(opt),
				_ => null,
			} is CeVioClinet c) {
				setLogger(c.VoiceClient);
				return c;
			}
		}

		// VoiceVox系
		{
			if (opt.Voice switch {
				CommandOptions.VoiceClientType.voicevox => new VoiceVoxClinet(opt),
				_ => null,
			} is VoiceVoxClinet c) {
				setLogger(c.VoiceClient);
				return c;
			}
		}

		throw new NotImplementedException($"不正な合成音声{opt.Voice}");
	}
}

// VoiceRoid, VoiceRoid2, VoicePeak, A.I.Voice, A.I.Voice2
internal class VoiroClinet : IClient {
	private readonly VoiceLink.NopVoiceObject nop = new();
	private readonly VoiceLink.IVoiceClient<VoiceLink.AudioCaptreStart, VoiceLink.NopVoiceObject, VoiceLink.IAudioCaptireClient> client;
	private readonly string exe;

	public VoiroClinet(CommandOptions opt) {
		this.client = opt.Voice switch {
			CommandOptions.VoiceClientType.voiceroid => new VoiceLink.Clients.VoiceRoid(),
			CommandOptions.VoiceClientType.voiceroid2 => new VoiceLink.Clients.VoiceRoid2(),
			CommandOptions.VoiceClientType.voicepeak => new VoiceLink.Clients.VoicePeak(),
			CommandOptions.VoiceClientType.aivoice => new VoiceLink.Clients.AiVoice(),
			CommandOptions.VoiceClientType.aivoice2 => new VoiceLink.Clients.AiVoice2(),
			_ => throw new NotImplementedException($"不正な合成音声{opt.Voice}"),
		};
		this.exe = opt.Client;
	}

	public VoiceLink.IVoiceClient<VoiceLink.AudioCaptreStart, VoiceLink.NopVoiceObject, VoiceLink.IAudioCaptireClient> VoiceClient => client;

	public void StartClient(bool isLaunch) => client.StartClient(isLaunch, new(exe));
	public void EndClinet() => client.EndClient();
	public void BeginSpeech(string text) => client.BeginSpeech(text, nop);
	public void Speech(string text) => client.Speech(text, nop);
	public void EndSpeech(string text) => client.EndSpeech(text, nop);
}

// CeVIO CS7, CeVIO AI
internal class CeVioClinet : IClient {
	private readonly VoiceLink.NopVoiceObject nop = new();
	private readonly VoiceLink.IVoiceClient<VoiceLink.NopVoiceObject, VoiceLink.CeVioSpeechClient, VoiceLink.NopVoiceObject> client;
	private readonly VoiceLink.CeVioSpeechClient cevio;

	public CeVioClinet(Models.CommandOptions opt) {
		this.client = opt.Voice switch {
			CommandOptions.VoiceClientType.ceviocs => new VoiceLink.Clients.CeVioCs(),
			CommandOptions.VoiceClientType.cevioai => new VoiceLink.Clients.CeVioAi(),
			_ => throw new NotImplementedException($"不正な合成音声{opt.Voice}"),
		};
		this.cevio = new(
			Cast: opt.CeVioCast,
			Speed: opt.CeVioSpeed,
			Tone: opt.CeVioTone,
			ToneScale: opt.CeVioToneScale,
			Alpha: opt.CeVioAlpha,
			Components: opt.ParseCeVioComponents()
		) {
			Volume = opt.CeVioVolume,
		};
	}

	public VoiceLink.IVoiceClient<VoiceLink.NopVoiceObject, VoiceLink.CeVioSpeechClient, VoiceLink.NopVoiceObject> VoiceClient => client;
	public void StartClient(bool isLaunch) => client.StartClient(isLaunch, nop);
	public void EndClinet() => client.EndClient();
	public void BeginSpeech(string text) => client.BeginSpeech(text, cevio);
	public void Speech(string text) => client.Speech(text, cevio);
	public void EndSpeech(string text) => client.EndSpeech(text, cevio);
}

// VoiceVox
internal class VoiceVoxClinet : IClient {
	private readonly VoiceLink.NopVoiceObject nop = new();
	private readonly VoiceLink.IVoiceClient<VoiceLink.NopVoiceObject, VoiceLink.VoiceVoxSpeechClient, VoiceLink.NopVoiceObject> client;
	private readonly VoiceLink.VoiceVoxSpeechClient voicevox;
	private readonly MMDevice device;

	public VoiceVoxClinet(Models.CommandOptions opt) {
		static MMDevice mm_dev(string id)  {
			MMDevice? d = null;
			var en = new MMDeviceEnumerator();
			try {
				if (!string.IsNullOrEmpty(id)) {
					d = en.GetDevice(id);
				}
			}
			catch (Exception e) {
			}
			finally {
				if(d == null) {
					d = en.GetDefaultAudioEndpoint(
						DataFlow.Render,
						Role.Multimedia);
				}
			}
			return d;
		}

		this.client = opt.Voice switch {
			CommandOptions.VoiceClientType.voicevox => new VoiceLink.Clients.VoiceVox(),
			_ => throw new NotImplementedException($"不正な合成音声{opt.Voice}"),
		};
		this.device = mm_dev(opt.WasapiId);
		this.voicevox = new(
			Host: opt.VoiceVoxHost,
			Port: opt.VoiceVoxPort,
			Speaker: opt.VoiceVoxSpeaker,
			SpeedScale: opt.VoiceVoxSpeedScale,
			PitchScale: opt.VoiceVoxPitchScale,
			IntonationScale: opt.VoiceVoxIntonationScale,
			Writer: new()
		) {
		};
	}

	public VoiceLink.IVoiceClient<VoiceLink.NopVoiceObject, VoiceLink.VoiceVoxSpeechClient, VoiceLink.NopVoiceObject> VoiceClient => client;
	public void StartClient(bool isLaunch) => client.StartClient(isLaunch, nop);
	public void EndClinet() => client.EndClient();
	public void BeginSpeech(string text) {
		voicevox.Writer.Seek(0, System.IO.SeekOrigin.Begin);
		voicevox.Writer.SetLength(0);
		client.BeginSpeech(text, voicevox);
	}
	public void Speech(string text) {
		static BufferedWaveProvider provide(VoiceLink.VoiceVoxSpeechClient vv) {
			var wavFormat = new WaveFormat(48000, 16, 1);
			var provider = new BufferedWaveProvider(wavFormat);
			var wav = vv.Writer.ToArray();
			provider.AddSamples(wav, 0, wav.Length);

			return provider;
		}

		client.Speech(text, voicevox);

		using var wavPlayer = new WasapiOut(
			device,
			AudioClientShareMode.Shared,
			false,
			0);

		wavPlayer.Init(provide(this.voicevox));
		wavPlayer.Volume = 1f;
		wavPlayer.Play();

		while (wavPlayer.PlaybackState == PlaybackState.Playing) {
			Thread.Sleep(10);
		}
		wavPlayer.Stop();
	}

	public void EndSpeech(string text) => client.EndSpeech(text, voicevox);

}
