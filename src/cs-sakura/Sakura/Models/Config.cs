using System;
using System.Collections.Generic;
using System.Text;

namespace Haru.Kei.Models; 
internal class Config {
	public LocalHostOrder Localhost { get; private set; } = LocalHostOrder.Auto;
	public int HttpPort { get; private set; } = 24080;
	public int WsPort { get; private set; } =  24081;

	public string LogPath { get; private set; } = "";
	public string ConfigPath { get; private set; } = "";


}

enum LocalHostOrder {
	Auto = 0,
	v4 = 1,
	v6 = 2,
}

