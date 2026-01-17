using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;

using Reactive.Bindings;


namespace Haru.Kei.Models;
public class CeVioBinder(uint volume, uint speed, uint tone, uint toneScale, uint alpha, IEnumerable<CeVioBinder.CeVioItemBinder> items) : INotifyPropertyChanged {
	public class CeVioItemBinder(string cast, IEnumerable<CeVioComponentBinder> components) : INotifyPropertyChanged {
		public event PropertyChangedEventHandler? PropertyChanged;
		public ReactiveProperty<string> Cast { get; } = new(initialValue: cast);
		public ReactiveCollection<CeVioComponentBinder> Components { get; } = InitCollection(components);
	}

	public class CeVioComponentBinder(string name, uint value) : INotifyPropertyChanged {
		public event PropertyChangedEventHandler? PropertyChanged;
		public ReactiveProperty<string> Name { get; } = new(initialValue: name);
		public ReactiveProperty<uint> Value { get; } = new(initialValue: value);
	}

	private static readonly (string Cevio, string Taller) ProgIdCs7 = (
		"CeVIO.Talk.RemoteService.ServiceControlV40",
		"CeVIO.Talk.RemoteService.TalkerV40");
	private static readonly (string Cevio, string Taller) ProgIdAi = (
		"CeVIO.Talk.RemoteService2.ServiceControl2",
		"CeVIO.Talk.RemoteService2.Talker2V40");

	private static ReactiveCollection<T> InitCollection<T>(IEnumerable<T> componets) {
		var ret = new ReactiveCollection<T>();
		foreach(var componet in componets) {
			ret.Add(componet);
		}
		return ret;
	}

	public static (dynamic CeVio, dynamic Talker)? CreateComInstance(string cenvio, string talker) {
		static dynamic? create(string progId) {
			var type = Type.GetTypeFromProgID(progId);
			if(type == null) {
				return null;
			}
			return Activator.CreateInstance(type);
		}

		static void release(dynamic? o) {
			if(o != null) {
				Marshal.ReleaseComObject(o);
			}
		}

		var c = create(cenvio);
		if(c == null) {
			return null;
		}
		var t = create(talker);
		if(t == null) {
			release(c);
			return null;
		}
		return (c, t);
	}

	private static CeVioBinder Connect(string cevio, string talker) {
		var com = CreateComInstance(cevio, talker);
		if(com == null) {
			throw new InvalidOperationException();
		}

		try {
			com.Value.CeVio.StartHost(true);
			var items = new List<CeVioItemBinder>();
			uint volume = com.Value.Talker.Volume;
			uint speed = com.Value.Talker.Speed;
			uint tone = com.Value.Talker.Tone;
			uint toneScale = com.Value.Talker.ToneScale;
			uint alpha = com.Value.Talker.Alpha;
			var casts = com.Value.Talker.AvailableCasts;
			for(var i = 0; i < casts.Length; i++) {
				var cmpts = new List<CeVioComponentBinder>();
				string cast = com.Value.Talker.At(i);
				com.Value.Talker.Cast = cast;
				foreach(var c in com.Value.Talker.Components) {
					string name = c.Name;
					uint val = c.Value;
					cmpts.Add(new(name, val));
				}
				items.Add(new(cast, cmpts));
			}
			return new(volume, speed, tone, toneScale, alpha, items);
		}
		finally {
			Marshal.ReleaseComObject(com.Value.CeVio);
			Marshal.ReleaseComObject(com.Value.Talker);
		}
	}

	public static CeVioBinder ConnectCs7() => Connect(ProgIdCs7.Cevio, ProgIdCs7.Taller);
	public static CeVioBinder ConnectAi() => Connect(ProgIdAi.Cevio, ProgIdAi.Taller);

	public event PropertyChangedEventHandler? PropertyChanged;
	public ReactiveProperty<uint> Volume { get; } = new(initialValue: volume);
	public ReactiveProperty<uint> Speed { get; } = new(initialValue: speed);
	public ReactiveProperty<uint> Tone { get; } = new(initialValue: tone);
	public ReactiveProperty<uint> ToneScale { get; } = new(initialValue: toneScale);
	public ReactiveProperty<uint> Alpha { get; } = new(initialValue: alpha);
	public ReactiveCollection<CeVioItemBinder> Casts { get; } = InitCollection(items);
}

