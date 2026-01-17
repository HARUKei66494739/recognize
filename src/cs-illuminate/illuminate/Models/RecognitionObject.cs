using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace Haru.Kei.Models;
public record class RecognitionObject {
#pragma warning disable CS8618
	[JsonProperty("transcript", Required = Required.Always)]
	public string Transcript { get; init; }

	[JsonProperty("translate", Required = Required.Always)]
	public string Translate { get; init; }
#pragma warning restore

	[JsonProperty("finish", Required = Required.Always)]
	public bool IsFinish { get; init; }
}

