# /tmp/test_no_ssl.py
from aiohttp import web

async def handler(request):
    return web.Response(text="OK")

app = web.Application()
app.router.add_get('/webhook', handler)
app.router.add_post('/webhook', handler)

if __name__ == '__main__':
    print("🚀 Запуск тестового сервера на HTTP :8080")
    web.run_app(app, host='0.0.0.0', port=8080)