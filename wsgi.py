"""
aiohttp proxy: serves static files + injects meta tags into HTML + proxies WebSockets
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
ST_URL = f"http://127.0.0.1:{STREAMLIT_PORT}"
ST_WS  = f"ws://127.0.0.1:{STREAMLIT_PORT}"

SITE_VERIFICATION = "8MpJT70JgoawSi-Z8yz-ZOHphQiFAsmJTq2622M41Us"
ADSENSE_PUB_ID    = "ca-pub-5050768956635718"

META_INJECT = f"""<meta name="google-site-verification" content="{SITE_VERIFICATION}">
<meta name="google-adsense-account" content="{ADSENSE_PUB_ID}">"""


async def serve_verification(request):
    """Serve Google verification HTML file."""
    filename = request.match_info["filename"]
    fp = Path("static") / f"google{filename}.html"
    if fp.exists():
        return web.FileResponse(fp, content_type="text/html")
    return web.Response(text="Not found", status=404)


async def health(request):
    return web.Response(text="OK")


async def websocket_proxy(request):
    """Full-duplex WebSocket proxy to Streamlit."""
    ws_server = web.WebSocketResponse()
    await ws_server.prepare(request)

    skip = {"host","connection","upgrade","sec-websocket-key",
            "sec-websocket-version","sec-websocket-extensions"}
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in skip}

    try:
        async with aiohttp.ClientSession() as s:
            async with s.ws_connect(f"{ST_WS}{request.path_qs}",
                                    headers=headers) as ws_back:

                async def fwd(src, dst):
                    async for msg in src:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await dst.send_str(msg.data)
                        elif msg.type == aiohttp.WSMsgType.BINARY:
                            await dst.send_bytes(msg.data)
                        else:
                            break

                await asyncio.gather(
                    fwd(ws_server, ws_back),
                    fwd(ws_back,   ws_server),
                )
    except Exception as e:
        print(f"WS error: {e}")
    return ws_server


async def http_proxy(request):
    """HTTP proxy; injects verification meta tags into Streamlit's HTML."""
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return await websocket_proxy(request)

    url = f"{ST_URL}{request.path_qs}"
    skip_req  = {"host", "connection"}
    skip_resp = {"transfer-encoding", "connection", "keep-alive", "content-length"}
    headers   = {k: v for k, v in request.headers.items()
                 if k.lower() not in skip_req}

    try:
        async with aiohttp.ClientSession() as s:
            async with s.request(
                request.method, url, headers=headers,
                data=await request.read(),
                allow_redirects=False,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                body = await resp.read()
                ctype = resp.headers.get("Content-Type", "")

                # Inject meta tags into the main HTML page
                if "text/html" in ctype:
                    try:
                        text = body.decode("utf-8")
                        if "<head>" in text:
                            text = text.replace("<head>",
                                                f"<head>\n{META_INJECT}")
                            body = text.encode("utf-8")
                    except Exception:
                        pass

                resp_headers = {k: v for k, v in resp.headers.items()
                                if k.lower() not in skip_resp}
                return web.Response(body=body, status=resp.status,
                                    headers=resp_headers)

    except aiohttp.ClientConnectorError:
        return web.Response(text="Streamlit starting, please refresh in 10s...",
                            status=503,
                            content_type="text/html")
    except Exception as e:
        return web.Response(text=f"Proxy error: {e}", status=502)


def make_app():
    app = web.Application()
    app.router.add_get("/google{filename}.html", serve_verification)
    app.router.add_get("/health", health)
    app.router.add_route("*", "/",              http_proxy)
    app.router.add_route("*", "/{path:.*}",     http_proxy)
    return app


def start_streamlit():
    print("Starting Streamlit...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py",
         f"--server.port={STREAMLIT_PORT}",
         "--server.address=127.0.0.1",
         "--server.headless=true",
         "--server.enableCORS=true",
         "--server.enableXsrfProtection=false"],
        env={**os.environ, "STREAMLIT_SERVER_HEADLESS": "true"},
    )
    # Poll until Streamlit responds
    for i in range(40):
        time.sleep(1)
        try:
            import urllib.request
            urllib.request.urlopen(
                f"http://127.0.0.1:{STREAMLIT_PORT}/healthz", timeout=2)
            print(f"Streamlit ready after {i+1}s")
            return proc
        except Exception:
            print(f"  waiting... {i+1}/40")
    print("Streamlit did not respond in 40s, continuing anyway")
    return proc


if __name__ == "__main__":
    start_streamlit()
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting aiohttp proxy on port {port}")
    web.run_app(make_app(), host="0.0.0.0", port=port)
