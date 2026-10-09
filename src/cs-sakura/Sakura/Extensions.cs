using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Unicode;

namespace Haru.Kei; 
internal static class Extensions {

	extension(object source) {

		public string ToJson(
			bool writeIndented = true) => JsonSerializer.Serialize(
				source,
				source.GetType(),
				new JsonSerializerOptions {
					Encoder = JavaScriptEncoder.Create(UnicodeRanges.All),
					WriteIndented = writeIndented
				});
	}

}
