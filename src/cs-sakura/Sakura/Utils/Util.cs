using System;
using System.Collections.Generic;
using System.Text;
using System.Threading.Tasks;

namespace Haru.Kei.Utils; 
internal class Util {
	// TODO: 例外処理を追加 T? から Tにしてnullを不許可とする
	public static async Task<T?> LoadYamlAsync<T>(string path) where T : class {
		try {
			Utils.Singleton.Logger.Info($"YAMLファイルを読み込ます => {path}");
			var yml = await System.IO.File.ReadAllTextAsync(path);
			var r = Utils.Singleton.YamlDeserializer.Deserialize<T>(yml);
			if(r == null) {
				// TODO: 例外
			}
			Utils.Singleton.Logger.Info($"YAMLファイルを読み込ました => {path}");
			return r;
		}
		catch (YamlDotNet.Core.YamlException e) {
			Utils.Singleton.Logger.Error($"{path}でエラー");
			Utils.Singleton.Logger.Error(e);
			throw;
		}
		catch (Exception e) when (
			(e is System.IO.IOException)
			|| (e is System.FieldAccessException)) {

			return default;
		}
	}
}

