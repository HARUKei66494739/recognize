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

			var kv = new List<KeyValuePair<string, string>>();
			while (parser.Current is Scalar) {
				kv.Add(parseKv(parser));
			}

			parser.Consume<MappingEnd>();

			if (kv.Count == 0) {
				throw new Exception();
			} else if (kv.Count == 1) {
				r.Add(new Models.TemplateVar() {
					Name = kv.First().Key,
					Value = kv.First().Value,
					Unit = null,
				});
			} else {
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
				var infUnit = tp.GetProperty(nameof(Models.TemplateVar.Unit));
				if((infName is null) || (infValue is null) || (infUnit is null)) {
					throw new ArgumentException("バグ");
				}

				var keyName = getName(infName);
				var keyValue = getName(infName);
				var keyUnit = getName(infName);

				// KeyValuePairがstructなのでnullチェックの関係上一度配列で受け取る
				var name = kv.Where(x => x.Key == keyName).ToArray();
				var val = kv.Where(x => x.Key == keyValue).ToArray();
				var unit = kv.Where(x => x.Key == keyUnit).ToArray();

				if (name.Count() == 0) {
					throw new YamlException($"{keyName}は必須");
				}
				if (val.Count() == 0) {
					throw new YamlException($"{keyValue}は必須");
				}
				r.Add(new Models.TemplateVar() {
					Name = name.First().Value,
					Value = val.First().Value,
					Unit = unit switch {
						{ } v when 0 < v.Count() => v.First().Value,
						_ => null
					},
				});
			}
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

