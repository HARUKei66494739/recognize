using System;
using System.IO;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using Newtonsoft.Json;

namespace Haru.Kei.Models;

[JsonObject]
public class Config {
	public const int CurrentVersion = 2025071400;

	[JsonProperty("version")]
	public int Version { get; private set; } = CurrentVersion;
	[JsonProperty("method")]
	public string TranscribeModel { get; set; } = "";
	[JsonProperty("google_language")]
	public string GoogleLanguage { get; set; } = "";
	[JsonProperty("google_timeout")]
	public float? GoogleTimeout { get; set; }
	[JsonProperty("google_profanity_filter")]
	public bool GoogleProfanityFilter { get; set; }
	[JsonProperty("translate")]
	public string TranslateModel { get; set; } = "";

	// マイク
	[JsonProperty("mic")]
	public int? Microphone { get; set; } = null;
	[JsonProperty("mic_db_threshold")]
	public float? MicrophoneThresholdDb { get; set; } = null;
	[JsonProperty("mic_record_min_duration")]
	public float? MicrophoneRecordMinDuration { get; set; } = null;
	[JsonProperty("filter_hpf")]
	public int? HpfParamater { get; set; } = null;
	[JsonProperty("vad")]
	public string? Vad { get; set; } = null;
	[JsonProperty("vad_silero_threshold")]
	public float? VadSileroThreshold { get; set; } = null;

	// ゆかりねっと連携
	[JsonProperty("out:yukarinette")]
	public bool IsUsedYukarinette { get; set; } = false;
	[JsonProperty("out_yukarinette")]
	public int? YukatinettePort { get; set; } = null;

	// ゆかこね連携
	[JsonProperty("out:yukacone")]
	public bool IsUsedYukaCone { get; set; } = false;
	[JsonProperty("out_yukacone")]
	public int? YukaConePort { get; set; } = null;

	// 字幕
	[JsonProperty("out:obs")]
	public bool IsUsedObsSubtitle { get; set; } = false;
	[JsonProperty("out_obs_truncate")]
	public float? ObsSubtitleTruncate { get; set; } = null;
	[JsonProperty("out_obs_text_ja")]
	public string ObsSubtitleTextJp { get; set; } = "";
	[JsonProperty("out_obs_text_en")]
	public string ObsSubtitleTextEn { get; set; } = "";
	[JsonProperty("out_obs_port")]
	public int? ObsSubtitlePort { get; set; } = null;
	[JsonProperty("out_obs_password")]
	public string ObsSubtitlePassword { get; set; } = "";
	[JsonProperty("out_obs_text_starts_with")]
	public bool ObsSubtitleTextStartsWith { get; set; } = false;
	[JsonProperty("out:vrc")]
	public bool IsUsedVrcSubtitle { get; set; } = false;

	// illuminate
	[JsonProperty("out:illuminate")]
	public bool IsUsedIlluminate { get; set; } = false;
	[JsonProperty("out_illuminate_voice")]
	public string IlluminateVoice { get; set; } = "voiceroid";

	[JsonProperty("out_illuminate_client:voiceroid")]
	public string IlluminateClientVoiceRoid { get; set; } = "";
	[JsonProperty("out_illuminate_client:voiceroid2")]
	public string IlluminateClientVoiceRoid2 { get; set; } = "";
	[JsonProperty("out_illuminate_client:voicepeak")]
	public string IlluminateClientVoicePeak { get; set; } = "";
	[JsonProperty("out_illuminate_client:aivoice")]
	public string IlluminateClientAiVoice { get; set; } = "";
	[JsonProperty("out_illuminate_client:aivoice2")]
	public string IlluminateClientAiVoice2 { get; set; } = "";
	[JsonProperty("out_illuminate_kana:voiceroid")]
	public bool IlluminateKanaVoiceRoid { get; set; } = false;
	[JsonProperty("out_illuminate_kana:voiceroid2")]
	public bool IlluminateKanaVoiceRoid2 { get; set; } = false;
	[JsonProperty("out_illuminate_kana:voicepeak")]
	public bool IlluminateKanaVoicePeak { get; set; } = true;
	[JsonProperty("out_illuminate_kana:aivoice")]
	public bool IlluminateKanaAiVoice { get; set; } = false;
	[JsonProperty("out_illuminate_kana:aivoice2")]
	public bool IlluminateKanaAiVoice2 { get; set; } = false;


	[JsonProperty("user_args")]
	public string UserArguments { get; set; } = "";


	[JsonObject]
	[TypeConverter(typeof(DefinitionOrderTypeConverter))]
	public class RecognizeExeArgument {
		/// <summary>プロパティグリッドのソート順番を宣言順に行う</summary>
		class DefinitionOrderTypeConverter : TypeConverter {
			public override PropertyDescriptorCollection GetProperties(ITypeDescriptorContext context, object value, Attribute[] attributes) {
				var pdc = TypeDescriptor.GetProperties(value, attributes);
				return pdc.Sort(value.GetType().GetProperties().Select(x => x.Name).ToArray());
			}

			public override bool GetPropertiesSupported(ITypeDescriptorContext context) { return true; }
		}
		/// <summary>文字列選択ボックスを出す用の基底</summary>
		/// <typeparam name="T"></typeparam>
		protected abstract class SelectableConverter<T> : StringConverter {
			protected abstract T[] GetItems();
			public override bool GetStandardValuesSupported(ITypeDescriptorContext context) { return true; }
			public override StandardValuesCollection GetStandardValues(ITypeDescriptorContext context) {
				return new StandardValuesCollection(this.GetItems());
			}
			public override bool GetStandardValuesExclusive(ITypeDescriptorContext context) { return true; }
		}

		/// <summary>--verboseの選択一覧</summary>
		class ArgVerboseConverter : SelectableConverter<string> {
			protected override string[] GetItems() {
				return new[] {
					"",
					"0",
					"1",
					"2",
					"3",
				};
			}
		}

		protected const string category00 = "00.環境";
		protected const string category01 = "01.illuminate";

		[Category(category00)]
		[DisplayName("recognize.exeパス")]
		[Description("recognize.exeのパスをフルパスまたは相対パスで指定")]
		[DefaultValue(@".\src\\py-recognition\dist\recognize\recognize.exe")]
		[JsonProperty("recognize_exe")]
		public string RecognizeExePath { get; set; } = "";

		[Category(category00)]
		[DisplayName("illuminate.exeパス")]
		[Description("illuminate.exeのパスをフルパスまたは相対パスで指定")]
		[DefaultValue(@".\src\\cs-illuminate\dist\illuminate.exe")]
		[JsonProperty("out_illuminate_exe")]
		public string IlluminateExePath { get; set; } = "";

		[Category(category01)]
		[DisplayName("ポート")]
		[Description("illuminateのTCP待受ポートを指定します")]
		[DefaultValue(null)]
		[JsonProperty("out_illuminate_port")]
		public int? IlluminatePort { get; set; } = default;

		[Category(category01)]
		[DisplayName("通知領域")]
		[Description("illuminateは通知領域に常駐します")]
		[DefaultValue(null)]
		[JsonProperty("out_illuminate_notify_icon")]
		public bool? IlluminateNotifyIcon { get; set; } = default;

		[DisplayName("ログレベル")]
		[Description("コンソールに出すログ出力レベルを設定します")]
		[DefaultValue("")]
		[TypeConverter(typeof(ArgVerboseConverter))]
		[JsonProperty("verbose")]
		public string ArgVerbose { get; set; } = "";

		/* 設定できないほうがいい気がするので保留
		[DisplayName("ログファイル名")]
		[Description("ログファイル名を指定します")]
		[DefaultValue("")]
		[ArgAttribute("--log_file")]
		public string ArgLogFile { get; set; } = "";
		*/

		[DisplayName("ログファイル出力先")]
		[Description("ログファイル出力先フォルダパスを指定します")]
		[DefaultValue("")]
		[JsonProperty("log_directory")]
		public string ArgLogDirectory { get; set; } = "";

		[DisplayName("録音")]
		[DefaultValue(null)]
		[Description("録音データを保存する場合trueにします")]
		[JsonProperty("record")]
		public bool? ArgRecord { get; set; } = null;

		[DisplayName("録音ファイル名")]
		[Description("録音ファイル名を指定します。最終的なファイル名は{指定ファイル名}-{連番}.wavになります。")]
		[DefaultValue("record")]
		[JsonProperty("record_file")]
		public string ArgRecordFile { get; set; } = "";

		[DisplayName("録音格納先")]
		[Description("録音ファイル出力先フォルダパスを指定します")]
		[JsonProperty("record_directory")]
		public string ArgRecordDirectory { get; set; } = "";

		[DisplayName("AIファイル格納先")]
		[Description("AIファイル格納ルートフォルダパスを指定します。このパスの配下に.cacheディレクトリが作られます。")]
		[JsonProperty("torch_cache")]
		public string ArgTorchCache { get; set; } = "";

		/*
		[DisplayName("自由記入欄")]
		[Description("入力した文字列はコマンド引数末尾に追加されます")]
		[DefaultValue("")]
		[JsonProperty("user_args")]
		public string ExtraArgument { get; set; } = "";
		*/
		public RecognizeExeArgument() {
			foreach(var p in this.GetType().GetProperties()) {
				var dva = p.GetCustomAttribute(typeof(DefaultValueAttribute)) as DefaultValueAttribute;
				if(dva != null) {
					p.SetValue(this, dva.Value);
				}
			}
			this.ArgLogDirectory
				= this.ArgTorchCache
				= AppDomain.CurrentDomain.BaseDirectory;
			this.ArgRecordDirectory = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Record");
		}
	}

	public RecognizeExeArgument Extra { get; private set; } = new();

	public const string TranscribeModelWhisper = "kotoba_whisper";
	public const string TranscribeModelGoogle = "google_mix";

	public const string VoiroVoiceRoid = "voiceroid";
	public const string VoiroVoiceRoid2 = "voiceroid2";
	public const string VoiroAiVoice = "aivoice";
	public const string VoiroAiVoice2 = "aivoice2";
	public const string VoiroVoicePeak = "voicepeak";
	public const string VoiroCeVioCs = "ceviocs";
	public const string VoiroCeVioAi = "cevioai";

	public string ToCommandOption() {
		static StringBuilder arg<T>(StringBuilder opt, string name, T? val) {
			if(val switch {
				string v => !string.IsNullOrEmpty(v),
				var v => v != null,
			}) {
				if(val is bool v1) {
					if(v1) {
						return opt.Append($"{name} ");
					}
				} else {
					if($"{val}".ToString().Last() == '\\') {
						return opt.Append($"{name} \"{val}\\\" ");
					} else {
						return opt.Append($"{name} \"{val}\" ");
					}
				}
			}
			return opt;
		}

		var opt = new StringBuilder();
		if(!string.IsNullOrEmpty(this.TranscribeModel)) {
			opt.Append($"--method \"{this.TranscribeModel}\" ");
			if(this.TranscribeModel == TranscribeModelGoogle) {
				arg(opt, "--google_language", this.GoogleLanguage);
				arg(opt, "--google_timeout", this.GoogleTimeout);
				arg(opt, "--google_profanity_filter", this.GoogleProfanityFilter);
			}
		}
		arg(opt, "--translate", this.TranslateModel);

		arg(opt, "--mic", this.Microphone);
		arg(opt, "--mic_db_threshold", this.MicrophoneThresholdDb);
		arg(opt, "--mic_record_min_duration", this.MicrophoneRecordMinDuration);
		arg(opt, "--vad", this.Vad);
		arg(opt, "--vad_silero_threshold", this.VadSileroThreshold);
		arg(opt, "--filter_hpf", this.HpfParamater);

		opt.Append($"--out \"print\" "); // ないと本体が起動しないのでいったん付与する
		if(this.IsUsedYukarinette) {
			opt.Append($"--out \"yukarinette\" ");
			arg(opt, "--out_yukarinette", this.YukatinettePort);
		}
		if(this.IsUsedYukaCone) {
			opt.Append($"--out \"yukacone\" ");
			arg(opt, "--out_yukacone", this.YukaConePort);
		}

		if(this.IsUsedObsSubtitle) {
			opt.Append($"--out \"obs\" ");
			arg(opt, "--out_obs_truncate", this.ObsSubtitleTruncate);
			arg(opt, "--out_obs_port", this.ObsSubtitlePort);
			arg(opt, "--out_obs_password", this.ObsSubtitlePassword);
			arg(opt, "--out_obs_text_ja", this.ObsSubtitleTextJp);
			arg(opt, "--out_obs_text_en", this.ObsSubtitleTextEn);
			arg(opt, "--out_obs_text_starts_with", this.ObsSubtitleTextStartsWith);
		}

		if(this.IsUsedVrcSubtitle) {
			opt.Append($"--out \"vrc\" ");
		}

		if(this.IsUsedIlluminate) {
			opt.Append($"--out \"illuminate\" ");
			if(Helpers.Util.IsFullPath(this.Extra.IlluminateExePath)) {
				var p = Path.Combine(AppContext.BaseDirectory, this.Extra.IlluminateExePath);
				arg(opt, "--out_illuminate_exe", p);
			} else {
				arg(opt, "--out_illuminate_exe", this.Extra.IlluminateExePath);
			}
			arg(opt, "--out_illuminate_voice", this.IlluminateVoice);
			arg(opt, "--out_illuminate_client", this.IlluminateVoice switch {
				VoiroVoiceRoid => this.IlluminateClientVoiceRoid,
				VoiroVoiceRoid2 => this.IlluminateClientVoiceRoid2,
				VoiroVoicePeak => this.IlluminateClientVoicePeak,
				VoiroAiVoice => this.IlluminateClientAiVoice,
				VoiroAiVoice2 => this.IlluminateClientAiVoice2,
				_ => throw new NotImplementedException($"--out_illuminate_voice {this.IlluminateVoice}")
			});
			arg(opt, "--out_illuminate_kana", this.IlluminateVoice switch {
				VoiroVoiceRoid => this.IlluminateKanaVoiceRoid,
				VoiroVoiceRoid2 => this.IlluminateKanaVoiceRoid2,
				VoiroVoicePeak => this.IlluminateKanaVoicePeak,
				VoiroAiVoice => this.IlluminateKanaAiVoice,
				VoiroAiVoice2 => this.IlluminateKanaAiVoice2,
				_ => throw new NotImplementedException($"--out_illuminate_kana {this.IlluminateVoice}")
			});

			arg(opt, "--out_illuminate_port", this.Extra.IlluminatePort);
			arg(opt, "--out_illuminate_notify_icon", this.Extra.IlluminateNotifyIcon);
		}

		arg(opt, "--verbose", this.Extra.ArgVerbose);
		arg(opt, "--log_directory", this.Extra.ArgLogDirectory);
		if(this.Extra.ArgRecord.HasValue) {
			if(this.Extra.ArgRecord.Value) {
				opt.Append($"--record ");
				arg(opt, "--record_file", this.Extra.ArgRecordFile);
				arg(opt, "--record_directory", this.Extra.ArgRecordDirectory);
			}
		}
		arg(opt, "--torch_cache", this.Extra.ArgTorchCache);

		if(!string.IsNullOrEmpty(this.UserArguments)) {
			opt.Append(string.Join(
				" ",
				this.UserArguments
					.Replace("\r\n", "\n")
					.Split('\n')));
		}

		return opt.ToString();
	}
}
