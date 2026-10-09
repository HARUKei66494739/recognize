using Haru.Kei.Models;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Windows.Media.Animation;
using YamlDotNet.Core.Tokens;

namespace Haru.Kei.Core;

file enum AppearanceType {
	Var,
	Style,
	KeyFrame,
}


file record SelectorRecord(string Selector, string Def) {
	public override string ToString() {
		var sb = new StringBuilder();
		sb.AppendLine($"{Selector} {{");
		foreach (var p in Def.Replace("\r\n", "\n").Split("\n")) {
			sb.AppendLine($"  {p}");
		}
		sb.AppendLine($"}}");
		return sb.ToString();
	}
}
file record AppearanceRecord(string Key, string Value, AppearanceType type) {
	public override string ToString() {
		switch(this.type) {
		case AppearanceType.Var:
			return $"--{Key}: {Value};";
			break;
		case AppearanceType.Style: {
				var sb = new StringBuilder();
				sb.AppendLine($"#sakura-contents .item:last-child .appearance.{Key} {{");
				foreach (var p in Value.Replace("\r\n", "\n").Split("\n")) {
					sb.AppendLine($"  {p};");
				}
				sb.AppendLine($"}}");
				return sb.ToString();
			}
			break;
		case AppearanceType.KeyFrame: {
				var sb = new StringBuilder();
				sb.AppendLine($"@keyframes {Key} {{");
				foreach (var p in Value.Replace("\r\n", "\n").Split("\n")) {
					sb.AppendLine($"  {p}");
				}
				sb.AppendLine($"}}");
				return sb.ToString();
			}
			break;
		}
		return base.ToString();
	}


}


internal class CaptionManagement {
	private Models.Style? baseStyle;
	private List<Models.Template> templates = new();


	public void Load() {
		this.baseStyle = null;
		this.templates.Clear();

		static T? Load<T>(string path) where T : class {
			try {
				var yml = System.IO.File.ReadAllText(path);
				return Utils.Singleton.Deserializer.Deserialize<T>(yml);
			}
			catch (Exception e) when (
				(e is System.IO.IOException)
				|| (e is System.FieldAccessException)) {

				return default;
			}
		}

		string path(string sub, string root = null) => root switch {
			{ } v => Path.Combine(v, sub),
			_ => Path.Combine(this.PathTemplateRoot, sub),
		};
		var appr = path("appearance");


		this.baseStyle = Load<Models.Style>(path("style.yaml"));
		foreach (var file in Directory.EnumerateFiles(appr)) {
			templates.Add(Load<Models.Template>(file));
		}


		var configRoot = Path.Combine(AppContext.BaseDirectory, "sakura");
		var configAppearance = Path.Combine(configRoot, "template", "appearance");
		if(Directory.Exists(configAppearance)) {
			foreach (var file in Directory.EnumerateFiles(configAppearance)) {
				templates.Add(Load<Models.Template>(file));
			}
		}
	}


	public string MakeCss() {
		if (baseStyle == null) {
			return "";
		}

		var selector = new Dictionary<string, SelectorRecord>();
		foreach (var it in this.baseStyle.Selector ?? []) {
			if (selector.ContainsKey(it.Id)) {
				// 競合した場合は上書きする
				selector[it.Id] = new(it.Selector, it.Def);
			} else {
				selector.Add(it.Id, new(it.Selector, it.Def));
			}
		}

		var vars = new Dictionary<string, AppearanceRecord>();
		var styles = new Dictionary<string, AppearanceRecord>();
		var keyflames = new Dictionary<string, AppearanceRecord>();

		foreach(var it in this.baseStyle.Var ?? []) {
			var id = $"{it.Key}";
			vars.Add(id, new(id, it.Value, AppearanceType.Var));
		}

		foreach (var it in this.templates) {
			if (it == null) {
				continue;
			}

			var pkg = it.Package;
			foreach (var var in it._Var ?? []) {
				var id = $"{pkg}_{var.Name}";
				vars.Add(id, new(id, var.Value, AppearanceType.Var));
			}
			foreach (var style in it._Style ?? []) {
				var id = $"{pkg}_{style.Name}";
				styles.Add(id, new(
					id,
					string.Join("\n", style.property.Select(x => $"{x.Key}: {x.Value}")),
					AppearanceType.Style));

			}
			foreach (var kf in it._Keyframe ?? []) {
				var id = $"{pkg}_{kf.Name}";
				keyflames.Add(id, new(
					id,
					kf.keyframe,
					AppearanceType.KeyFrame));
			}
		}

		var sb = new StringBuilder();
		sb.AppendLine(":root {");
		foreach (var var in vars.Values) {
			sb.AppendLine($"  {var}");
		}
		sb.AppendLine("}")
			.AppendLine()
			.AppendLine();

		foreach (var style in selector.Values) {
			sb.AppendLine($"{style}");
		}
		foreach (var style in styles.Values) {
			sb.AppendLine($"{style}");
		}

		foreach (var kf in keyflames.Values) {
			sb.AppendLine($"{kf}");
		}

		Console.WriteLine(sb.ToString());
		return sb.ToString();
	}



	private string PathTemplateRoot {
		get {
			return Path.Combine(AppContext.BaseDirectory, "template");
		}
	}
}


