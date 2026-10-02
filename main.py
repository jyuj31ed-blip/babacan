import os
import traceback
import discord
from discord import app_commands
import aiohttp
from aiohttp import web

# ---- AYARLAR (Render'da Environment Variables olarak gireceksin) ----
TOKEN = os.environ["TOKEN"]              # Bot tokeni
GUILD_ID = int(os.environ["GUILD_ID"])   # Discord sunucu ID
CHANNEL_ID = int(os.environ["CHANNEL_ID"])  # Komutun kullanılabileceği kanal ID
GROUP_ID = int(os.environ["GROUP_ID"])   # Roblox grup ID

# Roblox rank numarası -> isim başı (kendine göre düzenle)
RUTBELER = {
    1: "Acm. Er",
    2: "Er",
    3: "Onb.",
    4: "Çvş.",
    5: "Uz. Onb.",
    6: "Uz. Çvş.",
    7: "Asb. AstÇvş.",
    8: "Asb. Çvş.",
    9: "Asb. Kıd. Çvş.",
    12: "Asb. ÜstÇvş.",
    13: "Asb. Kıd. ÜstÇvş.",
    14: "Asb. BaşÇvş.",
    15: "Asb. Kıd. BaşÇvş.",
    16: "Atğm.",
    17: "Tğm.",
    18: "Ütğm.",
    19: "Yzb.",
    20: "Bnb.",
    21: "Yrb.",
    22: "Alb.",
    23: "Tuğg.",
    24: "Tümg.",
    25: "Korg.",
    26: "Org.",
    27: "Gnl. Krm. Bşk.",
}
# ---------------------------------------------------------------------

TIMEOUT = aiohttp.ClientTimeout(total=10)

intents = discord.Intents.default()


class Bot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

        # Render Web Service için basit bir web sunucusu (port isterler)
        app = web.Application()
        app.add_routes([web.get("/", lambda r: web.Response(text="Bot aktif"))])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000)))
        await site.start()


bot = Bot()
@bot.event
async def on_ready():
    print("GİRİŞ YAPILDI:", bot.user, bot.user.id)

async def roblox_id_al(session, kullanici_adi):
    async with session.post(
        "https://users.roblox.com/v1/usernames/users",
        json={"usernames": [kullanici_adi], "excludeBannedUsers": True},
    ) as r:
        print("Roblox kullanıcı API durum:", r.status)
        if r.status != 200:
            return None, None
        veri = await r.json()
        if not veri.get("data"):
            return None, None
        return veri["data"][0]["id"], veri["data"][0]["name"]


async def grup_rank_al(session, user_id):
    async with session.get(
        f"https://groups.roblox.com/v2/users/{user_id}/groups/roles"
    ) as r:
        print("Roblox grup API durum:", r.status)
        if r.status != 200:
            return None
        veri = await r.json()
        for g in veri.get("data", []):
            if g["group"]["id"] == GROUP_ID:
                return g["role"]["rank"]
    return 0  # grupta değil


@bot.tree.command(name="yenilerütbe", description="Roblox rütbene göre sunucu ismini günceller")
@app_commands.describe(oyuncu_adi="Roblox kullanıcı adın")
async def yenilerutbe(interaction: discord.Interaction, oyuncu_adi: str):
    if interaction.channel_id != CHANNEL_ID:
        await interaction.response.send_message(
            f"Bu komut sadece <#{CHANNEL_ID}> kanalında kullanılabilir.", ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            user_id, gercek_ad = await roblox_id_al(session, oyuncu_adi)
            if not user_id:
                await interaction.followup.send("Bu Roblox kullanıcısı bulunamadı.")
                return

            rank = await grup_rank_al(session, user_id)
            if rank is None:
                await interaction.followup.send("Roblox'a ulaşılamadı, biraz sonra tekrar dene.")
                return

        if rank == 0:
            await interaction.followup.send("Bu kullanıcı grupta değil.")
            return

        prefix = RUTBELER.get(rank)
        if not prefix:
            await interaction.followup.send(f"Rütben ({rank}) için tanımlı bir ünvan yok.")
            return

        yeni_isim = f"{prefix} | {gercek_ad}"[:32]  # Discord limiti 32 karakter

        await interaction.user.edit(nick=yeni_isim)
        await interaction.followup.send(f"İsmin **{yeni_isim}** olarak güncellendi.")

    except discord.Forbidden:
        await interaction.followup.send(
            "İsmini değiştiremedim. (Botun rolü senin rolünün üstünde olmalı; sunucu sahibinin ismi de değiştirilemez.)"
        )
    except Exception:
        traceback.print_exc()
        await interaction.followup.send("Bir hata oluştu, biraz sonra tekrar dene.")


bot.run(TOKEN)
