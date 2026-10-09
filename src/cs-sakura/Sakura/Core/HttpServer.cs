using Fleck;
using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Reactive.Linq;
using System.Text;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;

namespace Haru.Kei.Core; 
internal class HttpServer {
	private bool isRun = false;
	//HttpListener listener;
	private WebSocketServer? server;
	private readonly List<IWebSocketConnection> webSockets = new();
	public void Start(Models.Config config, CancellationTokenSource cancell) {
		Task.Run(() => {
			using var http = new HttpListener();
			http.Prefixes.Add(WebUtility.UrlDecode("http://localhost:20480/"));
			http.Start();
			while (true) {
				static void get(HttpListener listener) {
					var context = listener.GetContext();
					var request = context.Request;

					using var response = context.Response;
					//D:\recognize_sakura\src\cs-sakura\Sakura\bin\Debug\net10.0-windows\wwww\index.html
					var wwwRoot = @"D:\recognize_sakura\src\cs-sakura\Sakura\bin\Debug\net10.0-windows\www";
					var path = Path.Combine(wwwRoot, request.RawUrl switch {
						"/" => "index.html",
						_ => (request.RawUrl switch {
							{ } v when (0 < v.Length) && v.StartsWith("/") => v.Substring(1),
							{ } v => v,
							_ => ""
						}),
					});

					response.ContentLength64 = 0;
					if (request.HttpMethod != "GET") {
						response.StatusCode = 501;
						return;
					}

					if (!File.Exists(path)) {
						response.StatusCode = 404;
						return;
					}

					try {
						var content = File.ReadAllBytes(path);
						response.ContentType = MimeMapping.MimeUtility.GetMimeMapping(path);
						response.ContentLength64 = content.Length;
						response.OutputStream.Write(content, 0, content.Length);
					}
					catch (Exception e) {
						response.StatusCode = 403; // Forbidden
					}
				}
				get(http);
			}

		}, cancell.Token);

		server = new WebSocketServer("ws://127.0.0.1:20481");
		server.RestartAfterListenError = true;

		// Nagleアルゴリズムを無効化する場合はtrueを指定する
		server.ListenerSocket.NoDelay = true;

		server.Start(socket => {
			socket.OnOpen = () => {
				lock (this.webSockets) {
					webSockets.Add(socket);
				}
			};
			socket.OnClose = () => {
				lock (this.webSockets) {
					this.webSockets.Remove(socket);
				}
			};
			socket.OnMessage = message => {
				try {
					var json = System.Text.Json.JsonSerializer.Deserialize<Models.YukaneTranscribe>(message);
					if(json == null) {
						return;
					}
					testSend(new Models.SakuraSocketObject() {
						Transcript = json.Transcript,
						Translate = json.Translate,
						IsFinish = json.IsFinish,
						Token = [],
					}.ToString());
				}
				catch (Exception) { }
			};
			socket.OnBinary = bytes => {};
		});

		isRun = true;
	}

	public void testSend(string text) {
		lock (this.webSockets) {
			foreach (var s in webSockets) {
				try {
					_ = s.Send(text);
				}
				catch { }
			}
		}
	}
}
