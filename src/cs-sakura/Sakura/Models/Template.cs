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
}

internal class TemplateStyle {
	[YamlMember(Alias = "item")]
	public string Item { get; set; }

	[YamlMember(Alias = "name")]
	public string Name { get; set; }

	[YamlMember(Alias = "property")]
	public Dictionary<string, string> property { get; set; }

	/*

[YamlMember(Alias = "foreground")]
public string? foreground { get; set; }
[YamlMember(Alias = "background")]
public string? background { get; set; }
[YamlMember(Alias = "animation-name")]
public string? AnimationName { get; set; }
[YamlMember(Alias = "animation-duration")]
public string? AnimationDuration { get; set; }
[YamlMember(Alias = "animation-timing-function")]
public string? AnimationTimingFunction { get; set; }
[YamlMember(Alias = "animation-delay")]
public string? animation-delay { get; set; }
[YamlMember(Alias = "animation-direction")]
public string? animation-direction { get; set; }
[YamlMember(Alias = "animation-iteration-count")]
public string? animation-iteration-count { get; set; }
[YamlMember(Alias = "foreground")]
public string? foreground { get; set; }
[YamlMember(Alias = "foreground")]
public string? foreground { get; set; }

: null
: 5s
: null
animation-fill-mode: null
animation-play-state: null
animation-timeline: infinite
font-family: null,
font-size: null,
font-weight: null,
margin-left: null,
margin-top: null,
margin-right: null,
margin-bottom: null,
*/
}

internal class TemplateKeyframe {
	[YamlMember(Alias = "item")]
	public string Item { get; set; }

	[YamlMember(Alias = "name")]
	public string Name { get; set; }

	[YamlMember(Alias = "action")]
	public string keyframe { get; set; }
}