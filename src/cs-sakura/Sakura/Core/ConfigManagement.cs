using Haru.Kei.Models;
using Haru.Kei.Models.Configs;
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace Haru.Kei.Core; 
internal class ConfigManagement {
	private Models.Configs.ConfigWeb? webConfig;
	private Models.Configs.ConfigRule? ruleConfig;

	public void Load() {
		this.webConfig = null;
		this.ruleConfig = null;

		static T? Load<T>(string path) where T : class {
			try {
				var yml = System.IO.File.ReadAllText(path);
				return Utils.Singleton.Deserializer.Deserialize<T>(yml);
			}
			catch (Exception e) when (
				(e is System.IO.IOException)
				|| (e is System.FieldAccessException)) {

				return default;
			}
		}


		var configRoot = Path.Combine(AppContext.BaseDirectory, "sakura");
		var configWeb = Path.Combine(configRoot, "webconfig");

		var fileWebConfig = Path.Combine(configWeb, "webconfig.yaml");
		var fileRule = Path.Combine(configWeb, "rule.yaml");
		if (!File.Exists(configWeb)) {

		}
		if (!File.Exists(fileRule)) {

		}
		this.webConfig = Load<Models.Configs.ConfigWeb>(fileWebConfig);
		this.ruleConfig = Load<Models.Configs.ConfigRule>(fileRule);
	}

	public void ApplyWebConfig() {
		if(this.webConfig == null) {
			return;
		}
		if(this.ruleConfig == null) {
			return;
		}

		var configRoot = Path.Combine(AppContext.BaseDirectory, "www", "assets");
		var fileWebConfig = Path.Combine(configRoot, "webconfig.json");
		var fileRule = Path.Combine(configRoot, "rule.json");
		File.WriteAllText(fileWebConfig, this.webConfig?.ToJson());
		File.WriteAllText(fileRule, this.ruleConfig?.Rule?.ToJson());
	}
}
