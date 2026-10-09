using System;
using System.Collections.Generic;
using System.Text;
using YamlDotNet.Serialization;

namespace Haru.Kei.Utils; 
internal static class Singleton {

	public static IDeserializer Deserializer { get; }
		= new DeserializerBuilder()
			.IgnoreUnmatchedProperties()
			.Build();
}
