using System;
using System.Collections.Generic;
using System.Text;
using System.Windows;
using System.Windows.Media.Animation;
using YamlDotNet.Serialization;

namespace Haru.Kei.Models; 

internal class Style {
	[YamlMember(Alias = "var")]
	public Dictionary<string, string>? Var { get; set; }


	[YamlMember(Alias = "selector")]
	public IEnumerable<StyleSelector>? Selector { get; set; }
}

internal class StyleSelector {
	[YamlMember(Alias = "id")]
	public string Id { get; private set; } = "";

	[YamlMember(Alias = "selector")]
	public string Selector { get; private set; } = "";

	[YamlMember(Alias = "def")]
	public string Def { get; private set; } = "";
}


internal class Template {
	[YamlMember(Alias = "package")]
	public string Package { get; set; }


	[YamlMember(Alias = "var")]
	[YamlConverter(typeof(Helpers.Yaml.TemplateVarConverter))]
	public IEnumerable<TemplateVar>? _Var { get; set; }

	[YamlMember(Alias = "style")]
	public IEnumerable<TemplateStyle>? _Style { get; set; }

	[YamlMember(Alias = "keyframe")]
	public IEnumerable<TemplateKeyframe>? _Keyframe { get; set; }
}

internal class TemplateVar {
	[YamlMember(Alias = "name")]
	public string Name { get; set; }

	[YamlMember(Alias = "value")]
	public string Value { get; set; }

	[YamlMember(Alias = "unit")]
	public string? Unit { get; set; }
}

internal class TemplateStyle {
	[YamlMember(Alias = "item")]
	public string Item { get; init; } = "";

	[YamlMember(Alias = "id")]
	public string Id { get; init; } = "";

	[YamlMember(Alias = "base-on")]
	public IEnumerable<string>? BaseOn { get; init; }

	[YamlMember(Alias = "var")]
	[YamlConverter(typeof(Helpers.Yaml.TemplateVarConverter))]
	public IEnumerable<TemplateVar>? Var { get; init; }

	[YamlMember(Alias = "property")]
	public IEnumerable<KeyValuePair< string, string>>? Property { get; init; }
}

internal class TemplateKeyframe {
	[YamlMember(Alias = "item")]
	public string Item { get; set; }

	[YamlMember(Alias = "id")]
	public string Id { get; set; }

	[YamlMember(Alias = "action")]
	public string keyframe { get; set; }
}