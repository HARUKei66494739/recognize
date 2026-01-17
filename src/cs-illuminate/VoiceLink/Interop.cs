using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Runtime.InteropServices;

#pragma warning disable SYSLIB1054 // LibraryImportの警告はいったん抑制する


namespace VoiceLink;
internal static class Interop {
	internal class ComObject<T> : IDisposable where T : class {
		private T? value;

		public ComObject(T value) {
			this.value = value;
		}

		~ComObject() {
			lock (this) {
				this.Dispose();
			}
		}

		public T Ptr {
			get {
				ObjectDisposedException.ThrowIf(this.value == null, this);
				return this.value;
			}
		}

		public void Dispose() {
			if(this.value != null) {
				Marshal.ReleaseComObject(this.value);
				this.value = null;
				GC.SuppressFinalize(this);
			}
		}
	}

	[DllImport("user32.dll", CharSet = CharSet.Unicode)]
	public static extern bool IsWindow(nint hwnd);

	[DllImport("user32.dll", CharSet = CharSet.Unicode)]
	public static extern int RegisterWindowMessage(string lpString);

	[DllImport("user32.dll", CharSet = CharSet.Unicode)]
	public static extern nint PostMessage(nint hwnd, int msg, nint wp, nint lp);
	[DllImport("user32.dll", CharSet = CharSet.Unicode)]
	public static extern nint SendMessage(nint hwnd, int msg, nint wp, nint lp);
	[DllImport("user32.dll", CharSet = CharSet.Unicode)]
	public static extern nint SendMessage(nint hwnd, int msg, nint wp, string lp);
	[DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
	public static extern nint LoadLibrary(string lpLibFileName);
	[DllImport("kernel32.dll", CharSet = CharSet.Ansi, SetLastError = true)]
	public static extern nint GetProcAddress(nint hModule, string lpProcName);

	[DllImport("user32.dll")]
	public static extern bool GetClientRect(nint hWnd, out RECT lpRect);
	[DllImport("user32.dll")]
	public static extern bool GetWindowRect(nint hWnd, out RECT lpRect);
	[DllImport("user32.dll")]
	public static extern bool SetWindowPos(nint hWnd, nint hWndInsertAfter, int x, int y, int cx, int cy, int uFlags);

	[DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
	public static extern int GetPrivateProfileInt(string lpAppName, string lpKeyName, int nDefault, string lpFileName);
	[DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
	public static extern int GetPrivateProfileString(string lpAppName, string lpKeyName, string lpDefault, StringBuilder lpReturnedString, int nSize, string lpFileName);

	[DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
	public static extern nint CreateFileMapping(nint hFile, nint lpFileMappingAttributes, int flProtect, int dwMaximumSizeHigh, int dwMaximumSizeLow, string lpName);
	[DllImport("kernel32.dll")]
	public static extern nint MapViewOfFile(nint hFileMappingObject, int dwDesiredAccess, int dwFileOffsetHigh, int dwFileOffsetLow, nint dwNumberOfBytesToMap);
	[DllImport("kernel32.dll")]
	public static extern nint UnmapViewOfFile(nint hFileMappingObject);
	[DllImport("kernel32.dll")]
	public static extern nint CloseHandle(nint hObject);
	[DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
	public static extern nint lstrcpy(nint str1, string str2);
	[DllImport("user32.dll", CharSet = CharSet.Unicode)]
	public static extern nint FindWindowEx(
		nint hWndParent,
		nint hWndChildAfter,
		string lpszClass,
		string lpszWindow);
	[DllImport("user32.dll", CharSet = CharSet.Unicode)]
	public static extern int GetClassName(nint hWnd, StringBuilder lpClassName, int nMaxCount);
	[DllImport("user32.dll", CharSet = CharSet.Unicode)]
	public static extern bool EnumThreadWindows(int dwThreadId, EnumThreadWndProc lpfn, nint lParam);
	[DllImport("user32.dll", CharSet = CharSet.Unicode)]
	public static extern bool EnumChildWindows(nint hWndParent, EnumThreadWndProc lpEnumFunc, nint lParam);
	public delegate bool EnumThreadWndProc(nint hwnd, nint lParam);
	[DllImport("user32.dll", CharSet = CharSet.Unicode)]
	public static extern nint GetParent(nint hwnd);

	[DllImport("user32.dll", CharSet = CharSet.Unicode)]
	public static extern nint GetDlgItem(nint hwnd, int childID);
	[DllImport("user32.dll", CharSet = CharSet.Unicode)]
	public static extern int GetDlgCtrlID(nint hwnd);
	[DllImport("user32.dll", CharSet = CharSet.Unicode)]
	public static extern bool SetWindowText(nint hWnd, string lpString);
	[DllImport("user32.dll", CharSet = CharSet.Unicode)]
	public static extern bool ClientToScreen(nint hWnd, ref POINT lpPoint);
	[DllImport("user32.dll", CharSet = CharSet.Unicode)]
	public static extern bool ScreenToClient(nint hWnd, ref POINT lpPoint);

	public const int WM_KILLFOCUS = 0x0008;
	public const int WM_LBUTTONDOWN = 0x201;
	public const int WM_LBUTTONUP = 0x202;
	public const int WM_KEYDOWN = 0x0100;
	public const int WM_KEYUP = 0x0101;
	public const int WM_IME_CHAR = 0x286;
	public const int MK_LBUTTON = 0x01;
	public const int WM_CHAR = 0x0102;
	public const int WM_SETTEXT = 0x000C; 
	public const int VK_HOME = 0x24;
	public const int VK_DELETE = 0x2E;
	public const int VK_SPACE = 0x20;
	public const int VK_F5 = 0x74;

	public const int PAGE_READWRITE = 0x04;
	public const int FILE_MAP_WRITE = 0x00000002;

	public const int BM_CLICK = 0x00F5;

	[StructLayout(LayoutKind.Sequential)]
	public struct POINT {
		public int x;
		public int y;
	}
	[StructLayout(LayoutKind.Sequential)]
	public struct RECT {
		public int left;
		public int top;
		public int right;
		public int bottom;
	}

	[DllImport("oleacc.dll")]
	public static extern uint AccessibleObjectFromWindow(
		nint hwnd,
		int dwObjectID,
		in Guid riid,
		[MarshalAs(UnmanagedType.IUnknown)][Out] out object? ppvObject);

	// Token: 0x0600005C RID: 92
	[DllImport("oleacc.dll")]
	public static extern uint AccessibleChildren(
		Accessibility.IAccessible paccContainer,
		int iChildStart,
		int cChildren,
		[In][Out][MarshalAs(UnmanagedType.LPArray, SizeParamIndex = 2)] object[] rgvarChildren,
		out int pcObtained);

	[DllImport("oleacc.dll", CharSet = CharSet.Unicode, PreserveSig = false)]
	public static extern void GetStateText(int lStateBit, StringBuilder lpszState, int cchState);

	public static readonly Guid IID_IAccessible = new("{618736e0-3c3d-11cf-810c-00aa00389b71}");
}
