using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Json.Serialization;
using YamlDotNet.Serialization;

namespace Haru.Kei.Models.Configs; 
internal class ConfigRule {
	[YamlMember(Alias = "rule")]
	public IEnumerable<RuleItem>? Rule { get; private set; }
}

internal class RuleItem {
	[JsonPropertyName("method")]
	[JsonInclude]
	[YamlMember(Alias = "method")]
	public string Method { get; private set; } = "";

	[JsonPropertyName("target")]
	[JsonInclude]
	[YamlMember(Alias = "target")]
	public string Target { get; private set; } = "";


	[JsonPropertyName("appearance")]
	[JsonInclude]
	[YamlMember(Alias = "appearance")]
	public string Appearance { get; private set; } = "";
}
