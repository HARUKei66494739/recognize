using System;
using System.Collections.Generic;
using YamlDotNet.Core;
using YamlDotNet.Core.Events;
using YamlDotNet.Serialization;

namespace Haru.Kei.Helpers.Yaml;


// まず string: string に限定して対応する
public class KeyValuePairConverter : IYamlTypeConverter {
	public bool Accepts(Type type) {
		return type == typeof(KeyValuePair<string, string>);
	}


	public object? ReadYaml(IParser parser, Type type, ObjectDeserializer rootDeserializer) {
		parser.Consume<MappingStart>();

		var key = parser.Consume<Scalar>().Value;
		var value = parser.Consume<Scalar>().Value;

		parser.Consume<MappingEnd>();

		return new KeyValuePair<string, string>(key, value);
	}


	public void WriteYaml(IEmitter emitter, object? value, Type type, ObjectSerializer serializer) {
		if(!(value is KeyValuePair<string, string> kvp)) {
			return;
		}

		emitter.Emit(new MappingStart(null, null, false, MappingStyle.Block));
		emitter.Emit(new Scalar(kvp.Key));
		emitter.Emit(new Scalar(kvp.Value));
		emitter.Emit(new MappingEnd());
	}
}

