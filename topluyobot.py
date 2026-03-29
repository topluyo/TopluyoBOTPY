"""
topluyo_bot.py
~~~~~~~~~~~~~~
Topluyo platformu için Python bot kütüphanesi.
JavaScript (Node.js) versiyonunun Python karşılığıdır.

Kullanım:
    from topluyo_bot import TopluyoBOT

    bot = TopluyoBOT("TOKEN")

    @bot.on("connected")
    def on_connected():
        print("Bağlandı!")

    @bot.on("message")
    def on_message(data):
        print("Yeni mesaj:", data)

    bot.run()  # Bloklayan döngüyü başlatır
"""

import asyncio
import json
import time
import threading
from typing import Any, Callable, Dict, List, Optional, Union, Literal, TypeVar, TypedDict

F = TypeVar('F', bound=Callable[..., Any])
EventTypes = Literal["open", "connected", "close", "auth_problem", "message", "error", "*"]

# ---------------------------------------------------------------------------
# Mesaj payload yapıları (VS Code IntelliSense için ayrıştırılmış union türler)
# index.js'deki JSDoc türlerine karşılık gelir
# ---------------------------------------------------------------------------

class PostAddMessage(TypedDict):
    action: Literal["post/add"]
    message: str
    channel_id: str
    user_id: int

class PostMentionMessage(TypedDict):
    action: Literal["post/mention"]
    message: str
    channel_id: str
    user_id: int

class PostBumoteFormMessage(TypedDict):
    form: Dict[str, str]
    submit: str

class PostBumoteMessage(TypedDict):
    action: Literal["post/bumote"]
    message: PostBumoteFormMessage
    post_id: int
    user_id: int

class MessageSendMessage(TypedDict):
    action: Literal["message/send"]
    message: str
    user_id: int

class GroupJoinMessage(TypedDict):
    action: Literal["group/join"]
    group_id: int
    user_id: int

class GroupLeaveMessage(TypedDict):
    action: Literal["group/leave"]
    group_id: int
    user_id: int

class GroupKickMessage(TypedDict):
    action: Literal["group/kick"]
    group_id: int
    user_id: int

class TurboTransferDataMessage(TypedDict):
    message: str
    quantity: int

class TurboTransferMessage(TypedDict):
    action: Literal["turbo/transfer"]
    message: TurboTransferDataMessage
    transfer_id: int
    user_id: int

BotMessage = Union[
    PostAddMessage,
    PostMentionMessage,
    PostBumoteMessage,
    MessageSendMessage,
    GroupJoinMessage,
    GroupLeaveMessage,
    GroupKickMessage,
    TurboTransferMessage,
    Dict[str, Any] # Diğer/bilinmeyen olaylar için esneklik (Fallback)
]

import aiohttp
import websockets


# ---------------------------------------------------------------------------
# RouteClass — Toplu (batch) API isteklerini yöneten iç sınıf
# ---------------------------------------------------------------------------

class RouteClass:
    """
    Topluyo REST API isteklerini toplu (batch) hâlde gönderen iç sınıf.

    Birden fazla ``api()`` çağrısını biriktirip belirli aralıklarla tek bir
    HTTP isteğiyle ``/!apis`` endpoint'ine gönderir; böylece rate-limit
    baskısını azaltır.
    """

    def __init__(self, api_endpoint: str, auth_token: str, loop: asyncio.AbstractEventLoop):
        """
        :param api_endpoint: Topluyo REST API'nin taban URL'i (ör. ``https://topluyo.com/``)
        :param auth_token:   Bot kimlik doğrulama token'ı
        :param loop:         Kullanılacak asyncio event loop
        """
        self.API_END_POINT: str = api_endpoint
        self.auth_token: str = auth_token
        self.loop: asyncio.AbstractEventLoop = loop

        # Kuyruk: her eleman (request_dict, future_or_none, type_str)
        self.order: List[tuple] = []
        self._lock: asyncio.Lock = asyncio.Lock()

        self.last_sync_time: float = time.time()
        self.rate_limit_s: float = 1.0  # 1 000 ms → 1 s

        # Oto-senkronizasyon görevi (start() ile başlatılır)
        self._auto_sync_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Oto-senkronizasyon
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Periyodik oto-senkronizasyon döngüsünü başlatır."""
        self._auto_sync_task = asyncio.ensure_future(self._auto_sync_loop(), loop=self.loop)

    async def _auto_sync_loop(self) -> None:
        """Her 200 ms'de bir kuyruğu kontrol eder; gerekirse senkronize eder."""
        while True:
            await asyncio.sleep(0.2)
            await self._auto_sync()

    async def _auto_sync(self) -> None:
        """Kuyrukta istek varsa ve rate-limit geçmişse ``sync()`` çağırır."""
        async with self._lock:
            if not self.order:
                return
            now = time.time()
            if now - self.last_sync_time > self.rate_limit_s:
                self.last_sync_time = now
                await self._sync()

    # ------------------------------------------------------------------
    # Senkronizasyon
    # ------------------------------------------------------------------

    async def _sync(self) -> None:
        """
        Kuyruktaki tüm bekleyen API isteklerini tek bir HTTP POST isteğiyle
        gönderir ve her Future'ı ilgili sonuçla tamamlar.
        """
        if not self.order:
            return

        order = self.order[:]
        self.order.clear()

        body = [
            {"api": item[0]["api"], "data": item[0].get("data", {})}
            for item in order
        ]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.API_END_POINT + "!apis",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + self.auth_token,
                    },
                    json=body,
                ) as resp:
                    json_resp = await resp.json()

            response_list = list(json_resp.get("data", {}).values())

            store: List[Any] = []
            for i, d in enumerate(response_list):
                store.append(d)

                if i >= len(order):
                    continue

                future: Optional[asyncio.Future] = order[i][1]
                result_type: str = order[i][2]

                if future is not None and not future.done():
                    if result_type == "array":
                        future.set_result(store[:])
                    else:
                        future.set_result(store[0])
                    store.clear()

        except Exception as err:
            print("SYNC ERROR:", err)
            # Başarısız isteklerin Future'larını hata ile tamamla
            for item in order:
                fut = item[1]
                if fut is not None and not fut.done():
                    fut.set_exception(err)

    # ------------------------------------------------------------------
    # Genel API yardımcısı
    # ------------------------------------------------------------------

    async def api(
        self,
        body: Union[Dict[str, Any], List[Dict[str, Any]]],
    ) -> Any:
        """
        Bir veya birden fazla API isteğini kuyruğa ekler ve sonucu döndürür.

        :param body: Tek bir ``{"api": ..., "data": ...}`` sözlüğü
                     ya da bu tür sözlüklerin listesi.
        :returns:    Tek istek → herhangi bir değer;
                     çoklu istek → değerler listesi.
        """
        loop = self.loop

        async with self._lock:
            if isinstance(body, list):
                futures: List[asyncio.Future] = []
                for i, item in enumerate(body[:-1]):
                    self.order.append((item, None, "array"))

                last_future: asyncio.Future = loop.create_future()
                self.order.append((body[-1], last_future, "array"))
                return await last_future

            else:
                future: asyncio.Future = loop.create_future()
                self.order.append((body, future, "single"))
                return await future


# ---------------------------------------------------------------------------
# TopluyoBOT — Ana bot sınıfı
# ---------------------------------------------------------------------------

class TopluyoBOT:
    """
    Topluyo platformu için WebSocket tabanlı bot istemcisi.

    Desteklenen olaylar
    -------------------
    ``open``         — WebSocket bağlantısı açıldı
    ``connected``    — Bot başarıyla kimlik doğruladı
    ``close``        — Bağlantı kapandı
    ``auth_problem`` — Token geçersiz; yeniden bağlanılmaz
    ``message``      — Sunucudan olay/mesaj geldi
    ``error``        — Hata oluştu
    ``*``            — Tüm olayları dinler; ``callback(event, data)`` şeklinde çağrılır

    ``message`` olayındaki ``data["action"]`` değerleri
    ----------------------------------------------------
    ``post/add``      → ``{action, message, channel_id, user_id}``
    ``post/mention``  → ``{action, message, channel_id, user_id}``
    ``post/bumote``   → ``{action, message:{form,submit}, post_id, user_id}``
    ``message/send``  → ``{action, message, user_id}``
    ``group/join``    → ``{action, group_id, user_id}``
    ``group/leave``   → ``{action, group_id, user_id}``
    ``group/kick``    → ``{action, group_id, user_id}``
    ``turbo/transfer``→ ``{action, message:{message,quantity}, transfer_id, user_id}``

    Kullanım
    --------
    .. code-block:: python

        from topluyobot import TopluyoBOT, BotMessage

        bot = TopluyoBOT("TOKEN")

        @bot.on("connected")
        def bağlandı():
            print("Bağlandı!")

        @bot.on("message")
        def mesaj(data: BotMessage):
            # "data" değişkeni TypedDict union olduğundan
            # if şartınızla Pylance doğru veri tiplerini daraltacaktır
            action = data.get("action", "")

            if action == "message/send":
                print("DM:", data.get("message"))

            elif action == "post/bumote":
                # Şartla kontrol edildiğinde data argümanı PostBumoteMessage olarak tanınır
                print("Bumote form gönderildi:", data["message"]["submit"])

        bot.run()   # Bloklayan döngü
    """

    WS_URL = "wss://topluyo.com/!bot"
    API_URL = "https://topluyo.com/"
    PING_INTERVAL = 30  # saniye

    def __init__(self, token: str):
        """
        :param token: Botun kimlik doğrulama token'ı
        """
        self.token: str = token
        self._triggers: List[Dict[str, Any]] = []
        self._reconnect: bool = True

        self._loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        self._route: RouteClass = RouteClass(
            api_endpoint=self.API_URL,
            auth_token=token,
            loop=self._loop,
        )

    # ------------------------------------------------------------------
    # Event API
    # ------------------------------------------------------------------

    def on(self, event: EventTypes) -> Callable[[F], F]:
        """
        Belirtilen olaya bir dinleyici bağlar; dekoratör olarak kullanılabilir.

        :param event: Dinlenecek olay adı (``'connected'``, ``'message'`` vb.)

        .. code-block:: python

            @bot.on("message")
            def handler(data):
                ...
        """
        def decorator(callback: F) -> F:
            self._triggers.append({"event": event, "callback": callback})
            return callback
        return decorator

    def add_listener(self, event: EventTypes, callback: Callable[..., Any]) -> None:
        """
        Bir dinleyiciyi doğrudan kaydeder (dekoratörsüz kullanım).

        :param event:    Olay adı
        :param callback: Çağrılacak fonksiyon
        """
        self._triggers.append({"event": event, "callback": callback})

    def _emit(self, event: EventTypes, data: Any = None) -> None:
        """Kayıtlı dinleyicilere olayı yayar."""
        for t in self._triggers:
            if t["event"] == event:
                try:
                    if data is None:
                        t["callback"]()
                    else:
                        t["callback"](data)
                except Exception as e:
                    print(f"[TopluyoBOT] '{event}' dinleyicisinde hata: {e}")
            if t["event"] == "*":
                try:
                    t["callback"](event, data)
                except Exception as e:
                    print(f"[TopluyoBOT] '*' dinleyicisinde hata: {e}")

    # ------------------------------------------------------------------
    # REST API yardımcısı
    # ------------------------------------------------------------------

    async def post(self, api: str, data: Optional[Dict[str, Any]] = None) -> Any:
        """
        Topluyo REST API'sine tek bir istek gönderir.

        :param api:  Çağrılacak endpoint adı (ör. ``'messages.send'``)
        :param data: İsteğe eklenecek veri yükü
        :returns:    Sunucu yanıtı
        """
        return await self._route.api({"api": api, "data": data or {}})

    def post_sync(self, api: str, data: Optional[Dict[str, Any]] = None) -> Any:
        """
        ``post()``'un senkron (blocking) sarmalayıcısı.
        Olay dinleyicileri içinde kullanımı kolaylaştırır.

        :param api:  Endpoint adı
        :param data: Veri yükü
        :returns:    Sunucu yanıtı
        """
        future = asyncio.run_coroutine_threadsafe(
            self.post(api, data), self._loop
        )
        return future.result(timeout=15)

    # ------------------------------------------------------------------
    # WebSocket bağlantısı
    # ------------------------------------------------------------------

    async def _connect(self) -> None:
        """WebSocket bağlantısını kurar ve mesaj döngüsünü çalıştırır."""
        try:
            async with websockets.connect(self.WS_URL) as ws:
                # Kimlik doğrulama token'ını gönder
                await ws.send(self.token)
                self._emit("open")

                # Ping görevi
                async def _ping_loop():
                    while True:
                        await asyncio.sleep(self.PING_INTERVAL)
                        try:
                            await ws.ping()
                        except Exception:
                            break

                ping_task = asyncio.ensure_future(_ping_loop())

                try:
                    async for raw in ws:
                        try:
                            message = json.loads(raw)
                        except json.JSONDecodeError:
                            message = raw

                        if message == "AUTH_PROBLEM":
                            self._reconnect = False
                            self._emit("auth_problem")
                            break
                        elif message == "CONNECTED":
                            self._reconnect = True
                            self._emit("connected")
                        else:
                            self._emit("message", message)
                finally:
                    ping_task.cancel()

        except Exception as err:
            self._emit("error", err)
        finally:
            self._emit("close")
            if self._reconnect:
                await asyncio.sleep(1)
                await self._connect()

    async def _start(self) -> None:
        """RouteClass'ı ve WebSocket döngüsünü eş zamanlı başlatır."""
        await self._route.start()
        await self._connect()

    # ------------------------------------------------------------------
    # Başlatma noktaları
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        Botu başlatır ve bağlantı döngüsünü çalıştırır.
        Bu metod **bloklayıcıdır**; program buradan çıkmaz.
        """
        self._loop.run_until_complete(self._start())

    def start_background(self) -> threading.Thread:
        """
        Botu arka plan thread'inde başlatır ve döndürür.
        Ana thread'in serbest kalması gerektiğinde tercih edin.

        :returns: Çalışan ``threading.Thread`` örneği
        """
        def _run():
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._start())

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t