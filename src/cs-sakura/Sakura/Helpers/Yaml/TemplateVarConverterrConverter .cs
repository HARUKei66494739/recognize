using System;
using System.Collections.Generic;
using System.Linq;
using System.Reactive;
using System.Reflection;
using System.Xml.Linq;
using YamlDotNet.Core;
using YamlDotNet.Core.Events;
using YamlDotNet.Serialization;

namespace Haru.Kei.Helpers.Yaml;

/*
 * var:
 *  - {name}: {value}
 * 
 * または
 * 
 * var:
 *  - name: {name}
 *  - value: {value}
 *  ...
 *  
 *  を処理する
 * 
 */
public class TemplateVarConverter : IYamlTypeConverter {
	private readonly string keyName;
	private readonly string keyValue;
	private readonly string keyDescription;
	private readonly string KeyType;


	public TemplateVarConverter() {
		static string getName(System.Reflection.PropertyInfo inf) {
			var attr = inf.GetCustomAttribute<YamlMemberAttribute>();
			return attr switch {
				{ } v when !string.IsNullOrEmpty(v.Alias) => v.Alias,
				_ => inf.Name
			};
		}
		var tp = typeof(Models.TemplateVar);
		var infName = tp.GetProperty(nameof(Models.TemplateVar.Name));
		var infValue = tp.GetProperty(nameof(Models.TemplateVar.Value));
		var infDescription = tp.GetProperty(nameof(Models.TemplateVar.Description));
		var infType = tp.GetProperty(nameof(Models.TemplateVar.Type));

		System.Diagnostics.Debug.Assert(infName is not null);
		System.Diagnostics.Debug.Assert(infValue is not null);
		System.Diagnostics.Debug.Assert(infDescription is not null);
		System.Diagnostics.Debug.Assert(infType is not null);

		this.keyName = getName(infName);
		this.keyValue = getName(infValue);
		this.keyDescription = getName(infDescription);
		this.KeyType = getName(infType);
	}

	public bool Accepts(Type type) {
		return false;
	}

	public object? ReadYaml(IParser parser, Type type, ObjectDeserializer rootDeserializer) {
		static KeyValuePair<string, string> parseKv(IParser parser) =>
			new(parser.Consume<Scalar>().Value, parser.Consume<Scalar>().Value);

		var r = new List<Models.TemplateVar>();
		parser.Consume<SequenceStart>();
		while (parser.Current is MappingStart) {
			parser.Consume<MappingStart>();
			Console.WriteLine(parser.Current);

			var _name = parser.Consume<Scalar>().Value;
			var _value = default(string?);
			var _dsc = default(string?);
			var _type = default(string?);
			if (parser.Current is Scalar) {
				_value = parser.Consume<Scalar>().Value;
				_dsc = "";
			} else if(parser.Current is SequenceStart) {
				parser.Consume<SequenceStart>();

				var dic = new Dictionary<string, string>();
				while (parser.Current is MappingStart) {
					parser.Consume<MappingStart>();
					var t = parseKv(parser);
					dic.Add(t.Key, t.Value);
					parser.Consume<MappingEnd>();
				}


				string v;
				if(dic.TryGetValue("value", out v)) {
					_value = v;
				}
				if (dic.TryGetValue("dsc", out v)) {
					_dsc = v;
				}
				if (dic.TryGetValue("type", out v)) {
					_type = v;
				}
				parser.Consume<SequenceEnd>();
			}
			if (_value is null) {
				throw new Exception("aa");
			}
			if (_dsc is null) {
				throw new Exception("aa");
			}
			r.Add(new Models.TemplateVar() {
				Name = _name,
				Value = _value,
				Description = _dsc,
				Type = _type,
			});

			parser.Consume<MappingEnd>();
			Console.WriteLine(parser.Current);
		}
		parser.Consume<SequenceEnd>();
		return r;
	}


	public void WriteYaml(IEmitter emitter, object? value, Type type, ObjectSerializer serializer) {
		/*
		if(!(value is Models.TemplateVar var)) {
			return;
		}

		emitter.Emit(new MappingStart(null, null, false, MappingStyle.Block));
		emitter.Emit(new Scalar(var.Name));
		if (var.Unit != null) {
			emitter.Emit(new Scalar(var.Unit));
		}
		emitter.Emit(new MappingEnd());
		*/
	}
}

