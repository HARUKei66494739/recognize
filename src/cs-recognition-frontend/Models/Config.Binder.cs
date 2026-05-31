using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Reactive.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;

using Reactive.Bindings;


namespace Haru.Kei.Models;
public class ConfigBinder : INotifyPropertyChanged {
	delegate int cuInit(int flags);
	delegate int cuDeviceGetCount(ref int count);

	public class TranscribeItem(string name, bool enabled) {
		public ReactivePropertySlim<string> Name { get; } = new(initialValue: name);
		public ReactivePropertySlim<bool> Enabled { get; } = new(initialValue: enabled);
	}

	public event PropertyChangedEventHandler? PropertyChanged;

	private readonly (string Name, bool Enabled)[] TranscribeModels = [
		("設定しない", true),
		("AI音声認識(Whisper)", CanUsedCuda()),
		("AI音声認識(ReazonSpeech)", true),
		("google音声認識", true),
	];
	public const int TranscribeIndexNull = 0;
	public const int TranscribeIndexAiWhisper = 1;
	public const int TranscribeIndexAiReasonSpeech = 2;
	public const int TranscribeIndexGoogle = 3;
	private readonly string[] TranslateModels = {
		"設定しない",
		"AI翻訳",
	};
	public const int TranslateIndexNull = 0;
	public const int TranslateIndexAi = 1;
	private readonly string[] HpfParamaters = {
		"設定しない",
		"無効",
		"弱い",
		"普通",
		"強め",
	};
	public const int HpfIndexNull = 0;
	public const int HpfIndexDisable = 1;
	public const int HpfIndexLow = 2;
	public const int HpfIndexNormal = 3;
	public const int HpfIndexHi = 4;
	public const int HpfParamDisable = 0;
	public const int HpfParamLow = 80;
	public const int HpfParamNormal = 120;
	public const int HpfParamHi = 200;
	private readonly string[] IlluminateVoices = {
		"VOICEROID1/PLUS/EX",
		"VOICEROID2",
		"VOICEPEAK",
		"A.I.VOICE",
		"A.I.VOICE2",
	//	"CeVio CS7",
	//	"CeVio AI",
	};
	public const int VoiceIndexVoiceRoid = 0;
	public const int VoiceIndexVoiceRoid2 = 1;
	public const int VoiceIndexVoicePeak = 2;
	public const int VoiceIndexAiVoice = 3;
	public const int VoiceIndexAiVoice2 = 4;
	public const int VoiceIndexCeVioCs = 5;
	public const int VoiceIndexCeVioAi = 6;
	private readonly string[] VadMethods = {
		"設定しない",
		"WebRTC",
		"Silero VAD",
		"YAMNet",
	};
	public const int VadMethodIndexNone = 0;
	public const int VadMethodIndexWebRTC = 1;
	public const int VadMethodIndexSilero = 2;
	public const int VadMethodIndexYAMNet = 3;

	// モデル
	public ReactiveCollection<TranscribeItem> TranscribeModelsBinder { get; }
	public ReactivePropertySlim<int> TranscribeModeIndex { get; }
	public ReactivePropertySlim<string> GoogleLanguageBinding { get; }
	public ReactivePropertySlim<string> GoogleTimeoutBinding { get; set; }
	public ReactivePropertySlim<bool> GoogleProfanityFilterBinder { get; set; }
	public ReactiveCollection<string> TranslateModelsBinder { get; set; }
	public ReactivePropertySlim<int> TranslateModelIndex { get; }
	public ReadOnlyReactivePropertySlim<Visibility> GoogleItemVisibility { get; }
	private ReadOnlyReactivePropertySlim<Visibility> _GoogleTimeoutError { get; }
	public ReadOnlyReactivePropertySlim<Visibility> GoogleTimeoutError { get; }

	// マイク
	public ReactiveCollection<string> MicDevicesBinder { get; }
	public ReactivePropertySlim<int> MicDeviceIndex { get; }
	public ReactivePropertySlim<string> MicrophoneThresholdDbBinder { get; }
	public ReactivePropertySlim<string> MicrophoneRecordMinDurationBinder { get; }
	public ReactiveCollection<string> HpfParamatersBinder { get; }
	public ReactivePropertySlim<int> HpfParamaterIndex { get; }
	public ReactiveCollection<string> VadMethodsBinder { get; }
	public ReactivePropertySlim<int> VadMethodsIndex { get; }
	public ReactivePropertySlim<string> VadSileroThresholdBinder { get; }
	public ReadOnlyReactivePropertySlim<Visibility> VadSileroOptionVisibility { get; }
	public ReadOnlyReactivePropertySlim<Visibility> MicrophoneThresholdDbError { get; }
	public ReadOnlyReactivePropertySlim<Visibility> MicrophoneRecordMinDurationError { get; }
	// VadSileroThresholdErrorでRx合成用の一時プロパティ
	private ReadOnlyReactivePropertySlim<Visibility> _VadSileroThresholdError { get; }
	public ReadOnlyReactivePropertySlim<Visibility> VadSileroThresholdError { get; }

	// ゆかりねっと連携
	public ReactivePropertySlim<bool> IsUsedYukarinetteBinding { get; }
	public ReactivePropertySlim<string> YukarinettePortBinding { get; }
	public ReadOnlyReactivePropertySlim<Visibility> YukarinettePortError { get; }

	// ゆかこね連携
	public ReactivePropertySlim<bool> IsUsedYukaConeBinding { get; }
	public ReactivePropertySlim<string> YukaConePortBinding { get; }
	public ReadOnlyReactivePropertySlim<Visibility> YukaConePortError { get; }

	// 字幕
	public ReactivePropertySlim<bool> IsUsedObsSubtitleBinder { get; }
	public ReactivePropertySlim<string> ObsSubtitleTruncateBinder { get; }
	public ReactivePropertySlim<string> ObsSubtitleTextJpBinder { get; }
	public ReactivePropertySlim<string> ObsSubtitleTextEnBinder { get; }
	public ReactivePropertySlim<string> ObsSubtitlePortBinder { get; }
	public ReactivePropertySlim<string> ObsSubtitlePasswordBinder { get; }
	public ReactivePropertySlim<bool> ObsSubtitleTextStartsWithBinder { get; }
	public ReactivePropertySlim<bool> IsUsedVrcSubtitleBinder { get; }
	public ReadOnlyReactivePropertySlim<Visibility> ObsSubtitleTruncateError { get; }
	public ReadOnlyReactivePropertySlim<Visibility> ObsSubtitlePortError { get; }


	// ボイロ連携
	public ReactivePropertySlim<bool> IsUsedIlluminateBinding { get; }
	public ReactiveCollection<string> IlluminateVoiceBinding { get; }
	public ReactivePropertySlim<int> IlluminateVoiceIndex { get; }
	// Value書き換えたいのでいったんSlimにしない
	public ReactiveProperty<string> IlluminateClientBinding { get; }
	public ReadOnlyReactivePropertySlim<Visibility> IlluminateOptionVoiceRoidVisibility { get; }
	public ReadOnlyReactivePropertySlim<Visibility> IlluminateOptionCeVioVisibility { get; }

	// 自由記入欄
	public ReactivePropertySlim<string> UserArgumentsBinding { get; }

	public ConfigBinder(Config config) {
		// モデル
		this.TranscribeModelsBinder = new();
		this.TranscribeModelsBinder.AddRangeOnScheduler(TranscribeModels.Select(x => new TranscribeItem(x.Name, x.Enabled)));
		this.TranscribeModeIndex = new(initialValue: config.TranscribeModel switch {
			"kotoba_whisper" => TranscribeIndexAiWhisper,
			"reazon" => TranscribeIndexAiReasonSpeech,
			"google_mix" => TranscribeIndexGoogle,
			_ => TranscribeIndexNull
		});
		this.TranscribeModeIndex.Subscribe(x => config.TranscribeModel = x switch {
			TranscribeIndexAiWhisper => "kotoba_whisper",
			TranscribeIndexAiReasonSpeech => "reazon",
			TranscribeIndexGoogle => "google_mix",
			_ => ""
		});
		this.GoogleLanguageBinding = new(initialValue: config.GoogleLanguage);
		this.GoogleLanguageBinding.Subscribe(x => config.GoogleLanguage = x);
		this.GoogleTimeoutBinding = new(initialValue: this.ToString(config.GoogleTimeout));
		this.GoogleTimeoutBinding.Subscribe(x => config.GoogleTimeout = this.ToFloat(x));
		this.GoogleProfanityFilterBinder = new(initialValue: config.GoogleProfanityFilter);
		this.GoogleProfanityFilterBinder.Subscribe(x => config.GoogleProfanityFilter = x);

		this.TranslateModelsBinder = new();
		this.TranslateModelsBinder.AddRangeOnScheduler(TranslateModels);
		this.TranslateModelIndex = new(initialValue: config.TranslateModel switch {
			"kotoba_whisper" => TranslateIndexAi,
			_ => TranslateIndexNull
		});
		this.TranslateModelIndex.Subscribe(x => config.TranslateModel = x switch {
			TranslateIndexAi => "kotoba_whisper",
			_ => "",
		});

		this.GoogleItemVisibility = this.TranscribeModeIndex
			.Select(x => x switch {
				TranscribeIndexGoogle => Visibility.Visible,
				_ => Visibility.Hidden,
			}).ToReadOnlyReactivePropertySlim();
		this._GoogleTimeoutError = this.GoogleTimeoutBinding
			.Select(x => this.ToFloatError(x))
			.ToReadOnlyReactivePropertySlim();
		this.GoogleTimeoutError = this._GoogleTimeoutError
			.CombineLatest(this.GoogleItemVisibility,
				(p1, p2) => this.Visibilities2Visibility(p1, p2)
			).ToReadOnlyReactivePropertySlim();

		// マイク
		this.MicDevicesBinder = new();
		this.MicDeviceIndex = new(initialValue: config.Microphone switch {
			int v => v + 1,
			_ => 0
		});
		this.MicDeviceIndex.Subscribe(x => config.Microphone = (x - 1) switch {
			int v when(0 <= v) => v,
			_ => null
		});
		this.MicrophoneThresholdDbBinder = new(initialValue: this.ToString(config.MicrophoneThresholdDb));
		this.MicrophoneThresholdDbBinder.Subscribe(x => {
			config.MicrophoneThresholdDb = this.ToFloat(x);
		});
		this.MicrophoneRecordMinDurationBinder = new(initialValue: this.ToString(config.MicrophoneRecordMinDuration));
		this.MicrophoneRecordMinDurationBinder.Subscribe(x => {
			config.MicrophoneRecordMinDuration = this.ToFloat(x);
		});
		this.HpfParamatersBinder = new();
		this.HpfParamatersBinder.AddRangeOnScheduler(this.HpfParamaters);
		this.HpfParamaterIndex = new(initialValue: config.HpfParamater switch {
			int v when(HpfParamDisable <= v) && (v < HpfParamLow) => HpfIndexDisable,
			int v when(HpfParamLow <= v) && (v < HpfParamNormal) => HpfIndexLow,
			int v when(HpfParamNormal <= v) && (v < HpfParamHi) => HpfIndexNormal,
			int v when(HpfParamHi <= v) => HpfIndexHi,
			_ => HpfIndexNull
		});
		this.HpfParamaterIndex.Subscribe(x => config.HpfParamater = x switch {
			HpfIndexDisable => HpfParamDisable,
			HpfIndexLow => HpfParamLow,
			HpfIndexNormal => HpfParamNormal,
			HpfIndexHi => HpfParamHi,
			_ => null
		});
		this.VadMethodsBinder = new();
		this.VadMethodsBinder.AddRangeOnScheduler(this.VadMethods);
		this.VadMethodsIndex = new(initialValue: config.Vad switch {
			"webrtc" => VadMethodIndexWebRTC,
			"silero" => VadMethodIndexSilero,
			"yamnet" => VadMethodIndexYAMNet,

			// マイグレ
			"google" => VadMethodIndexNone,
			_ => VadMethodIndexNone
		});
		this.VadMethodsIndex.Subscribe(x => config.Vad = x switch {
			VadMethodIndexWebRTC => "webrtc",
			VadMethodIndexSilero => "silero",
			VadMethodIndexYAMNet => "yamnet",
			_ => null
		});
		this.VadSileroThresholdBinder = new(initialValue: this.ToString(config.VadSileroThreshold));
		this.VadSileroThresholdBinder.Subscribe(x => {
			config.VadSileroThreshold = this.ToFloat(x);
		});
		this.VadSileroOptionVisibility = this.VadMethodsIndex
			.Select(x => x switch {
				VadMethodIndexSilero => Visibility.Visible,
				_ => Visibility.Hidden,
			}).ToReadOnlyReactivePropertySlim();
		this.MicrophoneThresholdDbError = this.MicrophoneThresholdDbBinder
			.Select(x => this.ToFloatError(x))
			.ToReadOnlyReactivePropertySlim();
		this.MicrophoneRecordMinDurationError = this.MicrophoneRecordMinDurationBinder
			.Select(x => this.ToFloatError(x))
			.ToReadOnlyReactivePropertySlim();
		this._VadSileroThresholdError = this.VadSileroThresholdBinder
			.Select(x => x switch {
				string v when !string.IsNullOrEmpty(v) => ToFloat(v) switch {
					null => Visibility.Visible,
					float vv when(0 <= vv) && (vv <= 1.0f) => Visibility.Collapsed,
					_ => Visibility.Visible,
				},
				_ => Visibility.Collapsed
			}).ToReadOnlyReactivePropertySlim();
		this.VadSileroThresholdError = this._VadSileroThresholdError
			.CombineLatest(this.VadSileroOptionVisibility,
				(p1, p2) => {
					static bool conv(Visibility v) => v switch {
						Visibility.Visible => true,
						_ => false
					};
					return (conv(p1) && conv(p2)) switch {
						true => Visibility.Visible,
						_ => Visibility.Collapsed
					};
				}).ToReadOnlyReactivePropertySlim();

		// ゆかりねっと連携
		this.IsUsedYukarinetteBinding = new(initialValue: config.IsUsedYukarinette);
		this.IsUsedYukarinetteBinding.Subscribe(x => config.IsUsedYukarinette = x);
		this.YukarinettePortBinding = new(initialValue: ToString(config.YukatinettePort));
		this.YukarinettePortBinding.Subscribe(x => config.YukatinettePort = ToInt(x));
		this.YukarinettePortError = this.YukarinettePortBinding
			.Select(x => ToIntError(x))
			.ToReadOnlyReactivePropertySlim();

		this.IsUsedYukaConeBinding = new(initialValue: config.IsUsedYukaCone);
		this.IsUsedYukaConeBinding.Subscribe(x => config.IsUsedYukaCone = x);
		this.YukaConePortBinding = new(initialValue: ToString(config.YukaConePort));
		this.YukaConePortBinding.Subscribe(x => config.YukaConePort = ToInt(x));
		this.YukaConePortError = this.YukaConePortBinding
			.Select(x => ToIntError(x))
			.ToReadOnlyReactivePropertySlim();

		// 字幕
		this.IsUsedObsSubtitleBinder = new(initialValue: config.IsUsedObsSubtitle);
		this.IsUsedObsSubtitleBinder.Subscribe(x => config.IsUsedObsSubtitle = x);
		this.ObsSubtitleTruncateBinder = new(initialValue: ToString(config.ObsSubtitleTruncate));
		this.ObsSubtitleTruncateBinder.Subscribe(x => config.ObsSubtitleTruncate = ToFloat(x));
		this.ObsSubtitleTruncateError = this.ObsSubtitleTruncateBinder
			.Select(x => ToFloatError(x))
			.ToReadOnlyReactivePropertySlim();
		this.ObsSubtitleTextJpBinder = new(initialValue: config.ObsSubtitleTextJp);
		this.ObsSubtitleTextJpBinder.Subscribe(x => config.ObsSubtitleTextJp = x);
		this.ObsSubtitleTextEnBinder = new(initialValue: config.ObsSubtitleTextEn);
		this.ObsSubtitleTextEnBinder.Subscribe(x => config.ObsSubtitleTextEn = x);
		this.ObsSubtitlePortBinder = new(initialValue: ToString(config.ObsSubtitlePort));
		this.ObsSubtitlePortBinder.Subscribe(x => config.ObsSubtitlePort = ToInt(x));
		this.ObsSubtitlePortError = this.ObsSubtitlePortBinder
			.Select(x => ToIntError(x))
			.ToReadOnlyReactivePropertySlim();
		this.ObsSubtitlePasswordBinder = new(initialValue: config.ObsSubtitlePassword);
		this.ObsSubtitlePasswordBinder.Subscribe(x => config.ObsSubtitlePassword = x);
		this.ObsSubtitleTextStartsWithBinder = new(initialValue: config.ObsSubtitleTextStartsWith);
		this.ObsSubtitleTextStartsWithBinder.Subscribe(x => config.ObsSubtitleTextStartsWith = x);
		this.IsUsedVrcSubtitleBinder = new(initialValue: config.IsUsedVrcSubtitle);
		this.IsUsedVrcSubtitleBinder.Subscribe(x => config.IsUsedVrcSubtitle = x);

		// ボイロ連携
		this.IsUsedIlluminateBinding = new(initialValue: config.IsUsedIlluminate);
		this.IsUsedIlluminateBinding.Subscribe(x => config.IsUsedIlluminate = x);
		this.IlluminateVoiceBinding = new();
		this.IlluminateVoiceBinding.AddRangeOnScheduler(IlluminateVoices);
		this.IlluminateVoiceIndex = new(initialValue: config.IlluminateVoice switch {
			Config.VoiroVoiceRoid => VoiceIndexVoiceRoid,
			Config.VoiroVoiceRoid2 => VoiceIndexVoiceRoid2,
			Config.VoiroVoicePeak => VoiceIndexVoicePeak,
			Config.VoiroAiVoice => VoiceIndexAiVoice,
			Config.VoiroAiVoice2 => VoiceIndexAiVoice2,
			Config.VoiroCeVioCs => VoiceIndexCeVioCs,
			Config.VoiroCeVioAi => VoiceIndexCeVioAi,
			_ => VoiceIndexVoiceRoid
		});
		this.IlluminateVoiceIndex.Subscribe(x => {
			(string Voice, string Client) v = x switch {
				VoiceIndexVoiceRoid2 => (Config.VoiroVoiceRoid2, config.IlluminateClientVoiceRoid2),
				VoiceIndexVoicePeak => (Config.VoiroVoicePeak, config.IlluminateClientVoicePeak),
				VoiceIndexAiVoice => (Config.VoiroAiVoice, config.IlluminateClientAiVoice),
				VoiceIndexAiVoice2 => (Config.VoiroAiVoice2, config.IlluminateClientAiVoice2),
				VoiceIndexCeVioCs => (Config.VoiroCeVioCs, ""),
				VoiceIndexCeVioAi => (Config.VoiroCeVioAi, ""),
				_ => (Config.VoiroVoiceRoid, config.IlluminateClientVoiceRoid),
			};
			config.IlluminateVoice = v.Voice;
		});
		this.IlluminateClientBinding = this.IlluminateVoiceIndex.Select(x => {
			(string Voice, string Client) v = x switch {
				VoiceIndexVoiceRoid2 => (Config.VoiroVoiceRoid2, config.IlluminateClientVoiceRoid2),
				VoiceIndexVoicePeak => (Config.VoiroVoicePeak, config.IlluminateClientVoicePeak),
				VoiceIndexAiVoice => (Config.VoiroAiVoice, config.IlluminateClientAiVoice),
				VoiceIndexAiVoice2 => (Config.VoiroAiVoice2, config.IlluminateClientAiVoice2),
				VoiceIndexCeVioCs => (Config.VoiroCeVioCs, ""),
				VoiceIndexCeVioAi => (Config.VoiroCeVioAi, ""),
				_ => (Config.VoiroVoiceRoid, config.IlluminateClientVoiceRoid),
			};
			return v.Client;
		}).ToReactiveProperty<string>();
		this.IlluminateClientBinding.Subscribe(x => {
			Action<string> aply = this.IlluminateVoiceIndex.Value switch {
				VoiceIndexVoiceRoid2 => (y) => config.IlluminateClientVoiceRoid2 = y,
				VoiceIndexVoicePeak => (y) => config.IlluminateClientVoicePeak = y,
				VoiceIndexAiVoice => (y) => config.IlluminateClientAiVoice = y,
				VoiceIndexAiVoice2 => (y) => config.IlluminateClientAiVoice2 = y,
				VoiceIndexCeVioCs => (_) => { },
				VoiceIndexCeVioAi => (_) => { },
				_ => (y) => config.IlluminateClientVoiceRoid = y,
			};
			aply(x);
		});

		/*
		this.IlluminateClientBinding = new(initialValue: config.IlluminateClient);
		this.IlluminateClientBinding.Subscribe(x => config.IlluminateClient = x);
		*/

		this.IlluminateClientDialogFilter = this.IlluminateVoiceIndex.Select(x => x switch {
			VoiceIndexVoiceRoid => "VOICEROID|VOICEROID.exe",
			VoiceIndexVoiceRoid2 => "VOICEROID2|VoiceroidEditor.exe",
			VoiceIndexVoicePeak => "VOICEPEAK|voicepeak.exe",
			VoiceIndexAiVoice => "A.I.VOICE|AIVoiceEditor.exe",
			VoiceIndexAiVoice2 => "A.I.VOICE2|aivoice.exe",
			_ => "",
		}).Select(x => $"{x}|すべてのファイル(*.*)|*.*").ToReadOnlyReactivePropertySlim<string>();
		this.IlluminateClientDialogDirectory = this.IlluminateVoiceIndex.Select(x => x switch {
			VoiceIndexVoiceRoid => @"C:\Program Files (x86)\AHS\",
			VoiceIndexVoiceRoid2 => @"C:\Program Files (x86)\AHS\VOICEROID2",
			VoiceIndexVoicePeak => @"C:\Program Files\VOICEPEAK",
			VoiceIndexAiVoice => @"C:\Program Files\AI\AIVoice\AIVoiceEditor",
			VoiceIndexAiVoice2 => @"C:\Program Files\AI\AIVoice2\AIVoice2Editor",
			_ => null,
		}).Select(x => Directory.Exists(x) switch {
			true => x,
			_ => null,
		}).ToReadOnlyReactivePropertySlim();

		this.IlluminateOptionVoiceRoidVisibility = this.IlluminateVoiceIndex.Select(x => x switch {
			VoiceIndexVoiceRoid => Visibility.Visible,
			VoiceIndexVoiceRoid2 => Visibility.Visible,
			VoiceIndexVoicePeak => Visibility.Visible,
			VoiceIndexAiVoice => Visibility.Visible,
			VoiceIndexAiVoice2 => Visibility.Visible,
			_ => Visibility.Collapsed,
		}).ToReadOnlyReactivePropertySlim();
		this.IlluminateOptionCeVioVisibility = this.IlluminateVoiceIndex.Select(x => x switch {
			VoiceIndexCeVioCs => Visibility.Visible,
			VoiceIndexCeVioAi => Visibility.Visible,
			_ => Visibility.Collapsed,
		}).ToReadOnlyReactivePropertySlim();

		this.UserArgumentsBinding = new(initialValue: config.UserArguments);
		this.UserArgumentsBinding.Subscribe(x => config.UserArguments = x);
	}
	public ReadOnlyReactivePropertySlim<string> IlluminateClientDialogFilter { get; }
	public ReadOnlyReactivePropertySlim<string?> IlluminateClientDialogDirectory { get; }

	private static bool CanUsedCuda() {
		var cudaDevice = 0;
		var hNvcuda = default(nint);
		try {
			hNvcuda = Helpers.Interop.LoadLibrary("nvcuda.dll");
			if(hNvcuda == 0) {
				return false;
			}

			var pCuInit = Helpers.Interop.GetProcAddress(hNvcuda, "cuInit");
			var pCuDeviceGetCount = Helpers.Interop.GetProcAddress(hNvcuda, "cuDeviceGetCount");
			if((pCuInit == 0) || (pCuDeviceGetCount == 0)) {
				return false;
			}

			var cuInit = System.Runtime.InteropServices.Marshal.GetDelegateForFunctionPointer<cuInit>(pCuInit);
			var cuDeviceGetCount = System.Runtime.InteropServices.Marshal.GetDelegateForFunctionPointer<cuDeviceGetCount>(pCuDeviceGetCount);

			cuInit(0);
			cuDeviceGetCount(ref cudaDevice);
		}
		finally {
			if(0 != hNvcuda) {
				Helpers.Interop.FreeLibrary(hNvcuda);
			}
		}
		return 0 < cudaDevice;
	}

	private string ToString<T>(T v) {
		if(v == null) {
			return "";
		} else {
			return $"{v}";
		}
	}

	private int? ToInt(string s) {
		if(int.TryParse(s, out var v)) {
			return v;
		} else {
			return null;
		}
	}

	private Visibility ToIntError(string s) {
		if(string.IsNullOrEmpty(s)) {
			return Visibility.Collapsed;
		}

		if(int.TryParse(s, out var v)) {
			return Visibility.Collapsed;
		} else {
			return Visibility.Visible;
		}
	}

	private float? ToFloat(string s) {
		if(float.TryParse(s, out var v)) {
			return v;
		} else {
			return null;
		}
	}

	private Visibility ToFloatError(string s) {
		if(string.IsNullOrEmpty(s)) {
			return Visibility.Collapsed;
		}

		if(float.TryParse(s, out var _)) {
			return Visibility.Collapsed;
		} else {
			return Visibility.Visible;
		}
	}

	private Visibility Visibilities2Visibility(params Visibility[] visibilities) {
		var ret = true;
		foreach(var v in visibilities) {
			ret &= (v == Visibility.Visible);
		}

		return ret switch {
			true => Visibility.Visible,
			_ => Visibility.Collapsed,
		};
	}
}
