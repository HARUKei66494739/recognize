using Lucene.Net.Search;
using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Json.Serialization;
using YamlDotNet.Serialization;

namespace Haru.Kei.Models.Configs; 
internal class ConfigWeb {
	[JsonPropertyName("max_transcript_items")]
	[JsonInclude]
	[YamlMember(Alias = "max-transcript-items")]
	public int MaxTranscriptItems { get; private set; } 

	[JsonPropertyName("remove_caption_duration")]
	[JsonInclude]
	[YamlMember(Alias = "remove-caption-duration")]
	public int RemoveCaptionDuration { get; private set; }

	[JsonPropertyName("websocket_port")]
	[JsonInclude]
	[YamlMember(Alias = "websocket-port")]
	public int WebsocketPort { get; private set; }
}

