using Haru.Kei.Models;
using Lucene.Net.Util;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
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


	public async Task Load() {
		this.baseStyle = null;
		this.templates.Clear();

		string path(string sub, string root = null) => root switch {
			{ } v => Path.Combine(v, sub),
			_ => Path.Combine(this.PathTemplateRoot, sub),
		};
		var appr = path("appearance");
		var configRoot = Path.Combine(AppContext.BaseDirectory, "sakura");
		var configAppearance = Path.Combine(configRoot, "template", "appearance");


		this.baseStyle = await Utils.Util.LoadYamlAsync<Models.Style>(path("style.yaml"));
		var tasks = Directory.EnumerateFiles(appr)
			.Select(x => Utils.Util.LoadYamlAsync<Models.Template>(x))
			.ToList();
		if(Directory.Exists(configAppearance)) {
			tasks.AddRange(Directory.EnumerateFiles(configAppearance)
				.Select(x => Utils.Util.LoadYamlAsync<Models.Template>(x)));
		}
		await Task.WhenAll(tasks);
		templates.AddRange(tasks.Select(x => x.Result));
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

		var s = new List<(
			string Id,
			Models.TemplateStyle Style,
			List<Models.TemplateVar> Var,
			List<KeyValuePair<string, string>> Property,
			List<KeyValuePair<string, string>> ApplyProperty)>();
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
				var id = $"{pkg}_{style.Id}";
				// id重複チェック
				s.Add(new(id, style, [], [], []));
			}
			foreach (var kf in it._Keyframe ?? []) {
				var id = $"{pkg}_{kf.Id}";
				keyflames.Add(id, new(
					id,
					kf.keyframe,
					AppearanceType.KeyFrame));
			}
		}
		foreach (var style in s) {
			Console.WriteLine(style.Id);
			/*
			if(style.Id == "sample_pink-shadow") {
				System.Diagnostics.Debugger.Break();
			}
			*/
			foreach (var baseOn in style.Style.BaseOn ?? []) {
				if (!(s.Where(x => x.Id == baseOn).FirstOrDefault() is { } on)) {
					Console.WriteLine($"!!!!! {style.Id} base-on不正 !!!!!");

					continue;
				}
				style.Var.AddRange(on.Var ?? []);
				style.Property.AddRange(on.Property ?? []);
			}

			var d = new Dictionary<string, (int Count, Models.TemplateVar Val)>();
			style.Var.AddRange(style.Style.Var ?? []);
			foreach (var vv in style.Var) {
				if (d.ContainsKey(vv.Name)) {
					d[vv.Name] = (d[vv.Name].Count + 1, d[vv.Name].Val);
				} else {
					d.Add(vv.Name, (1, vv));
				}
			}

			foreach (var rm
				in d.Where(xx => 1 < xx.Value.Count)
					.Select(xx => xx.Value)) {

				style.Var.Remove(rm.Val);
			}
			foreach (var p in style.Style.Property ?? []) {
				foreach(var rm in style.Property.Where(pp => pp.Key == p.Key).ToArray()) {
					style.Property.Remove(rm);
				}
			}
			//style.ApplyProperty.AddRange(style.Var.Select(
			//	x => new KeyValuePair<string, string>($"--{x.Name}", $"{x.Value}")));
			style.Property.AddRange(style.Style.Property ?? []);
		}

		foreach (var style in s) {
			var v = string.Join("\n", style.Var.Select(x => $"--{x.Name}: {x.Value}"));
			var p = string.Join("\n", style.Property.Select(x => $"{x.Key}: {x.Value}"));

			styles.Add(style.Id, new(
				style.Id,
				$"{v}\n\n{p}",
				AppearanceType.Style));
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


