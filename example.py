"""
example.py — topluyo_bot kütüphanesi kullanım örneği
"""

from topluyobot import TopluyoBOT, BotMessage

bot = TopluyoBOT("BURAYA_TOKEN")


@bot.on("connected")
def on_connected():
    print("✅ Bota bağlandı!")


@bot.on("close")
def on_close():
    print("🔌 Bağlantı kapandı, yeniden bağlanılıyor...")


@bot.on("auth_problem")
def on_auth_problem():
    print("❌ Token geçersiz! Lütfen token'ı kontrol edin.")


@bot.on("error")
def on_error(err):
    print(f"⚠️  Hata: {err}")


@bot.on("message")
def on_message(data: BotMessage):
    action = data.get("action")

    # ── Direkt mesaj ──────────────────────────────────────────────────
    if action == "message/send":
        user_id = data["user_id"]
        text    = data["message"]
        print(f"[DM] kullanıcı {user_id}: {text}")

        # Örnek yanıt (senkron POST)
        bot.post_sync("messages.send", {
            "user_id": user_id,
            "message": f"Merhaba! Şunu yazdın: {text}"
        })

    # ── Kanal postu ───────────────────────────────────────────────────
    elif action == "post/add":
        print(f"[POST] kanal {data['channel_id']} | kullanıcı {data['user_id']}: {data['message']}")

    # ── Bot mention ───────────────────────────────────────────────────
    elif action == "post/mention":
        print(f"[MENTION] {data['user_id']} seni mention etti: {data['message']}")

    # ── Bumote formu ──────────────────────────────────────────────────
    elif action == "post/bumote":
        form   = data["message"]["form"]
        submit = data["message"]["submit"]
        print(f"[BUMOTE] form: {form} | submit: {submit}")

    # ── Grup olayları ─────────────────────────────────────────────────
    elif action == "group/join":
        print(f"[GROUP] kullanıcı {data['user_id']} gruba katıldı: {data['group_id']}")

    elif action == "group/leave":
        print(f"[GROUP] kullanıcı {data['user_id']} gruptan ayrıldı: {data['group_id']}")

    elif action == "group/kick":
        print(f"[GROUP] kullanıcı {data['user_id']} gruptan atıldı: {data['group_id']}")

    # ── Turbo transferi ───────────────────────────────────────────────
    elif action == "turbo/transfer":
        qty  = data["message"]["quantity"]
        note = data["message"]["message"]
        print(f"[TURBO] {data['user_id']} → {qty} turbo gönderdi. Not: {note}")


# Botu başlat (bloklayıcı)
bot.run()