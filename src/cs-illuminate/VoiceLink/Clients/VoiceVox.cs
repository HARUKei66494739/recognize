using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Net;
using System.Text;
using System.Text.Json.Nodes;
using System.Threading.Tasks;
using System.Web;
using Newtonsoft.Json;

namespace VoiceLink.Clients;
public class VoiceVox : VoiceClient<NopVoiceObject, VoiceVoxSpeechClient, NopVoiceObject> {
	private static HttpClient httpClient { get; } = new();

	public override NopVoiceObject ClientParameter { get; } = new();

	public override bool StartClient(bool isLaunch, NopVoiceObject extra) {
		return true;
	}

	public override void EndClient() {}

	public override void BeginSpeech(string text, VoiceVoxSpeechClient extra) {}
	public override void Speech(string text, VoiceVoxSpeechClient extra) {

		try {
			var entry = $@"http://{extra.Host}:{extra.Port}";
			AudioQuery? json;
			{
				using var request = new HttpRequestMessage(
					HttpMethod.Post,
					new Uri($"{entry}/audio_query?text={HttpUtility.UrlEncode(text)}&speaker={extra.Speaker}"));
				using var response = httpClient.Send(request);
				if (response.StatusCode != HttpStatusCode.OK) {
					throw new VoiceLinkException("クエリの生成に失敗");
				}

				var @string = response.Content.ReadAsStringAsync();
				@string.Wait();
				json = JsonConvert.DeserializeObject<AudioQuery>(@string.Result);
				if (json == null) {
					throw new VoiceLinkException("食えりJSONのデシリアライズに失敗");
				}
			}

			json.SpeedScale = extra.SpeedScale;
			json.PitchScale = extra.PitchScale;
			json.IntonationScale = extra.IntonationScale;
			json.VolumeScale = extra.VolumeScale;
			json.OutputSamplingRate = extra.OutputSamplingRate;
			json.OutputStereo = extra.OutputStereo;

			{
				using var request = new HttpRequestMessage(
					HttpMethod.Post,
					new Uri($"{entry}/synthesis?speaker={extra.Speaker}&enable_interrogative_upspeak={true}")) {
					Content = new StringContent(json.ToString(), Encoding.UTF8, @"application/json"),
				};
				using var response = httpClient.Send(request);
				//using var response = httpClient.SendAsync(request, HttpCompletionOption.ResponseHeadersRead);
				if (response.StatusCode != HttpStatusCode.OK) {
					throw new InvalidOperationException();
				}
				using var stream = response.Content.ReadAsStream();
				{
					var b = new byte[76800];
					int ret;
					while (0 < (ret = stream.Read(b, 0, b.Length))) {
						extra.Writer.Write(b, 0, ret);
					}
				}
			}
		}
		catch (AggregateException e) {
			throw new VoiceLinkException("VOICEVOXと通信できません", e);
		}
		catch (Exception e) {
			throw new VoiceLinkException("不明なエラー", e);
		}
	}

	public override void EndSpeech(string text, VoiceVoxSpeechClient extra) {}
}

[JsonObject]
file class JsonObject {
	public override string ToString() => JsonConvert.SerializeObject(this);
}

[JsonObject]
file class AudioQuery : JsonObject {
	[JsonProperty("accent_phrases", Required = Required.Always)]
	public AccentPhrases[] AccentPhrases { get; set; }

	[JsonProperty("speedScale", Required = Required.Always)]
	public double SpeedScale { get; set; }

	[JsonProperty("pitchScale", Required = Required.Always)]
	public double PitchScale { get; set; }

	[JsonProperty("intonationScale", Required = Required.Always)]
	public double IntonationScale { get; set; }

	[JsonProperty("volumeScale", Required = Required.Always)]
	public double VolumeScale { get; set; }

	[JsonProperty("prePhonemeLength", Required = Required.Always)]
	public double PrePhonemeLength { get; set; }


	[JsonProperty("postPhonemeLength", Required = Required.Always)]
	public double PostPhonemeLength { get; set; }


	[JsonProperty("outputSamplingRate", Required = Required.Always)]
	public int OutputSamplingRate { get; set; }

	[JsonProperty("outputStereo", Required = Required.Always)]
	public bool OutputStereo { get; set; }

	[JsonProperty("kana")]
	public string? Kana { get; set; }
}

[JsonObject]
file class AccentPhrases : JsonObject {
	[JsonProperty("moras", Required = Required.Always)]
	public Mora[] Moras { get; set; }

	[JsonProperty("accent", Required = Required.Always)]
	public int Accent { get; set; }

	[JsonProperty("pause_mora")]
	public PauseMora? PauseMora { get; set; }

	[JsonProperty("is_interrogative")]
	public bool? IsInterrogative { get; set; }
}

[JsonObject]
file class Mora : JsonObject {
	[JsonProperty("text", Required = Required.Always)]
	public string Text { get; set; }

	[JsonProperty("consonant")]
	public string? Consonant { get; set; }

	[JsonProperty("consonant_length")]
	public double? consonant_length { get; set; }

	[JsonProperty("vowel", Required = Required.Always)]
	public string Vowel { get; set; }

	[JsonProperty("vowel_length", Required = Required.Always)]
	public double VowelLength { get; set; }

	[JsonProperty("pitch", Required = Required.Always)]
	public double Pitch { get; set; }
}

[JsonObject]
file class PauseMora : JsonObject {
	[JsonProperty("text", Required = Required.Always)]
	public string Text { get; set; }

	[JsonProperty("consonant")]
	public string? Consonant { get; set; }

	[JsonProperty("consonant_length")]
	public double? ConsonantLength { get; set; }

	[JsonProperty("vowel", Required = Required.Always)]
	public string Vowel { get; set; }

	[JsonProperty("vowel_length", Required = Required.Always)]
	public double VowelLength { get; set; }

	[JsonProperty("pitch", Required = Required.Always)]
	public double Pitch { get; set; }
}

[JsonObject]
file class Speaker : JsonObject {
	[JsonProperty("supported_features")]
	public SpeakerSupportedFeature? SupportedFeatures { get; set; }

	[JsonProperty("name", Required = Required.Always)]
	public string Name { get; set; }

	[JsonProperty("speaker_uuid", Required = Required.Always)]
	public string SpeakerUuid { get; set; }

	[JsonProperty("styles", Required = Required.Always)]
	public SpeakerStyle[] Styles { get; set; }

	[JsonProperty("version")]
	public string? Version { get; set; }
}

[JsonObject]
file class SpeakerSupportedFeature : JsonObject {
	[JsonProperty("permitted_synthesis_morphing")]
	public string? PermittedSynthesisMorphing { get; set; } // "ALL" "SELF_ONLY" "NOTHING"
}


[JsonObject]
file class SpeakerStyle : JsonObject {
	[JsonProperty("name", Required = Required.Always)]
	public string Name { get; set; }

	[JsonProperty("id", Required = Required.Always)]
	public int Id { get; set; }
}