# TopluyoBOTPY 🤖

**Topluyo Bot Python kütüphanesi** – WebSocket tabanlı asenkron bot istemcisi

[![PyPI version](https://img.shields.io/pypi/v/topluyobot)](https://pypi.org/project/topluyobot/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 📋 İçerik

- [Kurulum](#kurulum)
- [Hızlı Başlangıç](#hızlı-başlangıç)
- [Mesaj Türleri](#mesaj-türleri)
- [API Referansı](#api-referansı)
- [Örnekler](#örnekler)
- [Geliştiriciler İçin](#geliştiriciler-için)

---

## 💻 Kurulum

### PyPI'den (Önerilen)

```bash
pip install topluyobot
```

### Geliştirme İçin

```bash
git clone https://github.com/yourusername/TopluyoBOTPY.git
cd TopluyoBOTPY
pip install -e .
```

**Gereksinimler:**
- Python 3.8+
- aiohttp >= 3.9.0
- websockets >= 12.0

---

## 🚀 Hızlı Başlangıç

```python
from topluyobot import TopluyoBOT

# Botu oluştur
bot = TopluyoBOT("YOUR_BOT_TOKEN_HERE")

# Bağlantı başarılı
@bot.on("connected")
def on_connected():
    print("✅ Bota bağlandı!")

# Mesaj al
@bot.on("message")
def on_message(data):
    print(f"Mesaj alındı: {data}")

# Botu başlat
bot.run()
```

---

## 📩 Mesaj Türleri

Bot aşağıdaki mesaj türlerini işleyebilir:

### 1. **Direkt Mesaj** (`message/send`)
```python
@bot.on("message")
def handler(data):
    if data.get("action") == "message/send":
        user_id = data["user_id"]
        text = data["message"]
        print(f"DM from {user_id}: {text}")
```

### 2. **Kanal Postu** (`post/add`)
```python
if data.get("action") == "post/add":
    channel_id = data["channel_id"]
    user_id = data["user_id"]
    message = data["message"]
```

### 3. **Bot Mention** (`post/mention`)
```python
if data.get("action") == "post/mention":
    user_id = data["user_id"]
    message = data["message"]
    print(f"Bot mentioned by {user_id}")
```

### 4. **Bumote Formu** (`post/bumote`)
```python
if data.get("action") == "post/bumote":
    form = data["message"]["form"]
    submit = data["message"]["submit"]
```

### 5. **Grup Olayları**
```python
# Grup katılma
if data.get("action") == "group/join":
    group_id = data["group_id"]

# Grup ayrılma
elif data.get("action") == "group/leave":
    group_id = data["group_id"]

# Grup atılma
elif data.get("action") == "group/kick":
    group_id = data["group_id"]
```

### 6. **Turbo Transfer** (`turbo/transfer`)
```python
if data.get("action") == "turbo/transfer":
    qty = data["message"]["quantity"]
    note = data["message"]["message"]
```

---

## 📚 API Referansı

### `TopluyoBOT`

#### `__init__(token: str)`
Botu token ile oluşturur.

```python
bot = TopluyoBOT("your_token")
```

#### `@bot.on(event: str)`
Event listener kaydeder.

**Desteklenen eventler:**
- `connected` – Bağlantı başarılı
- `close` – Bağlantı kapandı
- `auth_problem` – Token geçersiz
- `error` – Hata oluştu
- `message` – Mesaj alındı

```python
@bot.on("connected")
def handler():
    pass

@bot.on("error")
def handler(err):
    print(f"Error: {err}")
```

#### `bot.run()`
Botu başlatır (bloklayıcı).

```python
bot.run()  # Ctrl+C ile durdur
```

#### `bot.post_sync(method: str, params: dict)`
API'ye senkron POST isteği gönderir.

```python
response = bot.post_sync("messages.send", {
    "user_id": "12345",
    "message": "Merhaba!"
})
```

#### `await bot.post_async(method: str, params: dict)`
API'ye asenkron POST isteği gönderir.

```python
response = await bot.post_async("messages.send", {
    "user_id": "12345",
    "message": "Merhaba!"
})
```

---

## 💡 Örnekler

### Örnek 1: Echo Bot

```python
from topluyobot import TopluyoBOT, BotMessage

bot = TopluyoBOT("YOUR_TOKEN")

@bot.on("message")
def handle_message(data: BotMessage):
    if data.get("action") == "message/send":
        user_id = data["user_id"]
        text = data["message"]

        # Geri yanıt
        bot.post_sync("messages.send", {
            "user_id": user_id,
            "message": f"Echo: {text}"
        })

bot.run()
```

### Örnek 2: Olay Yöneticisi

```python
from topluyobot import TopluyoBOT

bot = TopluyoBOT("YOUR_TOKEN")

@bot.on("connected")
def on_connected():
    print("✅ Bağlandı")

@bot.on("close")
def on_close():
    print("🔌 Bağlantı kapandı")

@bot.on("auth_problem")
def on_auth():
    print("❌ Token geçersiz")

@bot.on("error")
def on_error(err):
    print(f"⚠️ Hata: {err}")

@bot.on("message")
def on_msg(data):
    print(f"📨 {data}")

bot.run()
```

### Örnek 3: Mesaj Türlerine Göre İşlem

Detaylı örnek için `example.py` dosyasına bakın.

---

## 🔧 Geliştiriciler İçin

### Kütüphane Yapısı

```
topluyobot/
├── __init__.py       # Ana exports
├── bot.py            # TopluyoBOT sınıfı
├── py.typed          # PEP 561 type hints
└── ...
```

### Type Hints

Kütüphane tam type hint desteğine sahiptir:

```python
from topluyobot import TopluyoBOT, BotMessage

bot: TopluyoBOT = TopluyoBOT("token")

@bot.on("message")
def handler(data: BotMessage) -> None:
    pass
```

### Test Etme

```bash
pip install pytest pytest-asyncio
pytest
```

### Derleme

```bash
pip install build
python -m build
```

---

## 📝 Lisans

MIT License – Detaylar için [LICENSE](LICENSE) dosyasını okuyun.

---

## 📧 İletişim

- **Resmi Site:** [topluyo.com](https://topluyo.com)
- **Email:** info@topluyo.com
- **Issues:** [GitHub Issues](https://github.com/yourusername/TopluyoBOTPY/issues)

---

## 🤝 Katkıda Bulunma

Pull request'ler hoş karşılanır! Büyük değişiklikler için önce bir issue açın.

1. Fork et
2. Feature branch oluştur (`git checkout -b feature/AmazingFeature`)
3. Commit et (`git commit -m 'Add some AmazingFeature'`)
4. Push et (`git push origin feature/AmazingFeature`)
5. Pull Request aç

---

**Türkçe Dokümantasyon** | [English Docs](README.en.md) (gelecek)
