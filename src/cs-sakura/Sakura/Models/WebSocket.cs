using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.Unicode;
using Haru.Kei.Shared.Models;

namespace Haru.Kei.Models; 



internal class YukaneTranscribe : JsonObject {
	[JsonPropertyName("transcript")]
	[JsonInclude]
	public required string Transcript { get; init; }
	[JsonPropertyName("translate")]
	[JsonInclude]
	public required IEnumerable<YukaneTranslate> Translate { get; init; }

	/// <summary>現在オンライン変換は実装していないので常にTrue</summary>
	[JsonPropertyName("finish")]
	[JsonInclude] public required bool IsFinish { get; init; } = true;

}

//{"transcript": "あちらたんはチャレンジみたいよ", "translate": [{"index": 0, "translate": "", "lang": "en"}], "finish": true}


internal class YukaneTranslate : JsonObject {
	/// <summary>0固定</summary>
	[JsonPropertyName("index")]
	[JsonInclude]
	public required int Index { get; init; } = 0;
	[JsonPropertyName("translate")]
	[JsonInclude]
	public required string Translate { get; init; }
	/// <summary>en固定</summary>
	[JsonPropertyName("lang")]
	[JsonInclude]
	public required string Langage { get; init; } = "en";
}


internal class SakuraSocketObject : JsonObject {
	[JsonPropertyName("transcript")]
	[JsonInclude]
	public required string Transcript { get; init; }
	[JsonPropertyName("translate")]
	[JsonInclude]
	public required IEnumerable<YukaneTranslate> Translate { get; init; }

	/// <summary>現在オンライン変換は実装していないので常にTrue</summary>
	[JsonPropertyName("finish")]
	[JsonInclude]
	public required bool IsFinish { get; init; } = true;


	[JsonPropertyName("token")]
	[JsonInclude]
	public required IEnumerable<object> Token { get; init; } = Array.Empty<object>();
}