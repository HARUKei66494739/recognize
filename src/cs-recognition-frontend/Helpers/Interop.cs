using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;

namespace Haru.Kei.Helpers;
static class Interop {
	[DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
	public static extern nint LoadLibrary(string dllToLoad);

	[DllImport("kernel32.dll", CharSet = CharSet.Ansi, EntryPoint = "GetProcAddress")]
	public static extern nint GetProcAddress(nint hModule, string procedureName);

	[DllImport("kernel32.dll")]
	public static extern bool FreeLibrary(nint hModule);
}