using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace VoiceLink;

public interface IVoiceLogger {
	/// <summary>INFOレベルログを出力したい場合設定</summary>
	Action<string>? LogInfo { get; set; }
	/// <summary>DEBUGレベルログを出力したい場合設定</summary>
	Action<string>? LogDebug { get; set; }
}

public interface IVoiceClient<TStartObj, TSpeechObj, TClientObj> : IVoiceLogger
	where TStartObj:IStartObject
	where TSpeechObj:ISpeechObject
	where TClientObj:IClientObject
	{

	/// <summary>合成音声クライアント依存パラメータ</summary>
	TClientObj ClientParameter { get; }

	/// <summary>クライアントの初期化</summary>
	/// <param name="targetExe">クライアントexeファイルのフルパス</param>
	/// <param name="isLaunch">クライアントを自動起動する場合はtrue(現在使用されていません)</param>
	/// <returns>初期化に成功した場合はtrue</returns>
	bool StartClient(bool isLaunch, TStartObj extra);
	/// <summary>クライアントの開放(現在使用されていません)</summary>
	void EndClient();

	/// <summary>読み上げ開始前の準備を行います。失敗した場合は<see cref="VoiceLinkException"/>を投げてください。</summary>
	/// <param name="text">読み上げテキスト</param>
	public void BeginSpeech(string text, TSpeechObj extra);
	/// <summary>読み上げ処理を行います。失敗した場合は<see cref="VoiceLinkException"/>を投げてください。</summary>
	/// <param name="text">読み上げテキスト</param>
	public void Speech(string text, TSpeechObj extra);
	/// <summary>読み上げで使用したリソースの解放処理を行います。失敗した場合は<see cref="VoiceLinkException"/>を投げてください。</summary>
	/// <param name="text">読み上げテキスト</param>
	public void EndSpeech(string text, TSpeechObj extra);
}

public interface IStartObject { }
public interface ISpeechObject { }
public interface IClientObject { }

/// <summary>VoiceClientはなにも要求しません</summary>
public record NopVoiceObject() : IStartObject, ISpeechObject, IClientObject;

/// <summary>
/// VoiceClientはオーディオキャプチャを要求します
/// </summary>
/// <param name="TargetExe"></param>
public record AudioCaptreStart(string TargetExe) : IStartObject;

/// <summary>
/// CeVIOのSpeechパラメータ
/// </summary>
/// <param name="Cast">トークキャスト</param>
/// <param name="Volume">音の大きさ（0～100）</param>
/// <param name="Speed">話す速さ（0～100）</param>
/// <param name="Tone">音の高さ（0～100）</param>
/// <param name="ToneScale">抑揚（0～100）</param>
/// <param name="Alpha">声質（0～100）</param>
/// <param name="Components">感情パラメータ(パラメータ名, 値)</param>
public record CeVioSpeechClient(
	string Cast,
	uint Speed,
	uint Tone,
	uint ToneScale,
	uint Alpha,
	IEnumerable<(string Name, uint Value)> Components) : ISpeechObject {

	public uint Volume { get; init; } = 50;
}


public record VoiceVoxSpeechClient(
	string Host,
	int Port,
	int Speaker,
	double SpeedScale,
	double PitchScale,
	double IntonationScale,
	System.IO.MemoryStream Writer) : ISpeechObject {

	public double VolumeScale { get; init; } = 1.0;
	public int OutputSamplingRate { get; init; } = 48000;
	public bool OutputStereo { get; init; } = false;
}

/// <summary>オーディオキャプチャのためのクライアントパラメータ</summary>
public interface IAudioCaptireClient : IClientObject {
	int ProcessId { get; }
}
