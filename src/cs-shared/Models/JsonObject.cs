using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Unicode;

namespace Haru.Kei.Shared.Models;

internal class JsonObject {
	public override string ToString() => this.ToString(
		writeIndented: true);

	public string ToString(
		bool writeIndented) => JsonSerializer.Serialize(
			this,
			this.GetType(),
			new JsonSerializerOptions {
				Encoder = JavaScriptEncoder.Create(UnicodeRanges.All),
				WriteIndented = writeIndented
			});
}