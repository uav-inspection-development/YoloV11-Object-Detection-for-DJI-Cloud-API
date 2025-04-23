# main.py
RUN_MODE = "streamlit"  # 可选: "streamlit" 或 "api"

if RUN_MODE == "streamlit":
    import streamlit as st
    from web import Detection_UI

    app = Detection_UI(from_streamlit=True)
    app.setupMainWindow()

elif RUN_MODE == "api":
    from api_server import socketio, app
    socketio.run(app, host="0.0.0.0", port=5000)
