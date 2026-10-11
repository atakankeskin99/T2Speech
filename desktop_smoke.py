import webview

webview.create_window(
    "T2Speech — Desktop Test",
    "http://127.0.0.1:8000",
    width=1280,
    height=900,
    min_size=(900, 600),
)

webview.start(debug=True)