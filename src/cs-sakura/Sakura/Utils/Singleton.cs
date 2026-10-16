using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text;
using YamlDotNet.Serialization;

using sharedUtil = Haru.Kei.Shared.Utils;

namespace Haru.Kei.Utils; 
internal static class Singleton {
	/// <summary>共通YAMLシリアライズ用</summary>
	public static ISerializer YamlSserializer { get; }
		= NewYamlBuilder<SerializerBuilder>()
			.Build();

	/// <summary>共通YAMLデシリアライズ用</summary>
	public static IDeserializer YamlDeserializer { get; }
		= NewYamlBuilder<DeserializerBuilder>()
			.IgnoreUnmatchedProperties()
			.Build();

	public static sharedUtil.Logger<SakuraLogProvider> Logger
		=> Shared.Utils.Logger<SakuraLogProvider>.Current;
	public static void InitLog(bool isRotate=false) {
		// TODO: 現実装では割り込めないのでIF見直す
		SakuraLogProvider.IsRotate = isRotate;
		Logger.Init();
	}

	private static T NewYamlBuilder<T>() where T : BuilderSkeleton<T>, new() {
		var r = new T();

		var ymlConvNs = typeof(Helpers.Yaml.TemplateVarConverter).Namespace;
		var targetTypes = Assembly.GetExecutingAssembly().GetTypes()
			.Where(t => t.Namespace == ymlConvNs && t.IsClass);

		foreach (Type t in targetTypes) {
			if (t.GetConstructor([]) is { } con) {
				if (con.Invoke(null) is IYamlTypeConverter converter) {
					r.WithTypeConverter(converter);
				}
			}
		}
		return r;
	}
}


internal class SakuraLogProvider : sharedUtil.ILoggerProvider {
	public static bool IsRotate { get; set; }

	public string BaseLogName => "sakura";

	public string GetLogFileName()
		=> IsRotate switch {
			true => ((Haru.Kei.Shared.Utils.ILoggerProvider)this).GenRotateLogFileName(),
			_ => this.BaseLogName,
		};
}
