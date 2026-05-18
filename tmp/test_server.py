# /tmp/test_server.py
import ssl
from aiohttp import web

async def hello(request):
    return web.Response(text="OK")

app = web.Application()
app.router.add_get('/webhook', hello)
app.router.add_post('/webhook', hello)

ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_ctx.load_cert_chain(
    '/home/ubuntu/certs/fullchain.pem',
    '/home/ubuntu/certs/privkey.pem'
)

if __name__ == '__main__':
    print("🚀 Запуск тестового сервера на :8443")
    web.run_app(app, host='0.0.0.0', port=8443, ssl_context=ssl_ctx)