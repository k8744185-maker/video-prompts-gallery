"""
Async proxy using aiohttp - handles HTTP + WebSocket connections
Serves Google verification file + proxies everything else to Streamlit
"""
import asyncio
import aiohttp
from aiohttp import web
import subprocess
import sys
import os
import time
from pathlib import Path


STREAMLIT_PORT = 8501
STREAMLIT_URL = f"http://127.0.0.1:{STREAMLIT_PORT}"
STREAMLIT_WS  = f"ws://127.0.0.1:{STREAMLIT_PORT}"


# ── Serve Google verification files ──────────────────────────────────────────
async def serve_verification(request):
    filename = request.match_info["filename"]
    file_path = Path("static") / f"google{filename}.html"
    if file_path.exists():
        return web.FileResponse(file_path, content_type="text/html")
    return web.Response(text="Not found", status=404)


# ── Health check ─────────────────────────────────────────────────────────────
async def health(request):
    return web.Response(text="OK")


# ── WebSocket proxy ───────────────────────────────────────────────────────────
async def websocket_proxy(request):
    ws_client = web.WebSocketResponse()
    await ws_client.prepare(request)

    target_url = f"{STREAMLIT_WS}{request.path_qs}"
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in ("host","connection","upgrade",
                                    "sec-websocket-key","sec-websocket-version",
                                    "sec-websocket-extensions")}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(target_url, headers=headers) as ws_server:

                async def to_server():
                    async for msg in ws_client:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await ws_server.send_str(msg.data)
                        elif msg.type == aiohttp.WSMsgType.BINARY:
                            await ws_server.send_bytes(msg.data)
                        else:
                            break

                async def to_client():
                    async for msg in ws_server:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await ws_client.send_str(msg.data)
                        elif msg.type == aiohttp.WSMsgType.BINARY:
                            await ws_client.send_bytes(msg.data)
                        else:
                            break

                await asyncio.gather(to_server(), to_client())
    except Exception as e:
        print(f"WebSocket proxy error: {e}")
    return ws_client


# ── HTTP proxy ────────────────────────────────────────────────────────────────
async def http_proxy(request):
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return await websocket_proxy(request)

    target_url = f"{STREAMLIT_URL}{request.path_qs}"
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in ("host", "connection")}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                request.method, target_url, headers=headers,
                data=await request.read(), allow_redirects=False,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                body = await resp.read()
                skip = {"transfer-encoding","connection","keep-alive"}
                resp_headers = {k: v for k, v in resp.headers.items()
                                if k.lower() not in skip}
                return web.Response(body=body, status=resp.status,
                                    headers=resp_headers)
    except aiohttp.ClientConnectorError:
        return web.Response(text="Streamlit not available", status=503)
    except Exception as e:
        return web.Response(text=f"Proxy error: {e}", status=502)


# ── App setup ─────────────────────────────────────────────────────────────────
def make_app():
    app = web.Application()
    app.router.add_get("/google{filename}.html", serve_verification)
    app.router.add_get("/health", health)
    app.router.add_route("*", "/", http_proxy)
    app.router.add_route("*", "/{path_info:.*}", http_proxy)
    return app


def start_streamlit():
    print("Starting Streamlit on port 8501...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py",
         f"--server.port={STREAMLIT_PORT}",
         "--server.address=127.0.0.1",
         "--server.headless=true",
         "--server.enableCORS=true",
         "--server.enableXsrfProtection=false"],
        env={**os.environ, "STREAMLIT_SERVER_HEADLESS": "true"},
    )
    for i in range(30):
        time.sleep(1)
        try:
            import urllib.request
            urllib.request.urlopen(
                f"http://127.0.0.1:{STREAMLIT_PORT}/healthz", timeout=2)
            print("Streamlit is ready!")
            return proc
        except Exception:
            print(f"Waiting for Streamlit... ({i+1}/30)")
    print("Streamlit started (continuing anyway)")
    return proc


if __name__ == "__main__":
    start_streamlit()
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting aiohttp proxy on port {port}")
    web.run_app(make_app(), host="0.0.0.0", port=port)
