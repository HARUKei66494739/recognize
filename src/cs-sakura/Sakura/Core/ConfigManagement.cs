using Haru.Kei.Models;
using Haru.Kei.Models.Configs;
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading.Tasks;

namespace Haru.Kei.Core; 
internal class ConfigManagement {
	private Models.Configs.ConfigWeb? webConfig;
	private Models.Configs.ConfigRule? ruleConfig;

	public async Task Load() {
		this.webConfig = null;
		this.ruleConfig = null;

		var configRoot = Path.Combine(AppContext.BaseDirectory, "sakura");
		var configWeb = Path.Combine(configRoot, "webconfig");

		var fileWebConfig = Path.Combine(configWeb, "webconfig.yaml");
		var fileRule = Path.Combine(configWeb, "rule.yaml");
		if (!File.Exists(configWeb)) {
			Utils.Singleton.Logger.Error($"必要な設定ファイルが見つかりません => {configWeb}");
		}
		if (!File.Exists(fileRule)) {
			Utils.Singleton.Logger.Error($"必要な設定ファイルが見つかりません => {fileRule}");
		}
		this.webConfig = await Utils.Util.LoadYamlAsync<Models.Configs.ConfigWeb>(fileWebConfig);
		this.ruleConfig = await Utils.Util.LoadYamlAsync<Models.Configs.ConfigRule>(fileRule);
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
