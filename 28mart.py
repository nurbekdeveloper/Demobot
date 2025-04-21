import ccxt
import time
from datetime import datetime
import requests

# Telegram bot sozlamalari
TELEGRAM_BOT_TOKEN = '8004221998:AAG9Dla2J1_oBYsjXD6ZDkx9GYqG-Jbd_Wc'
CHAT_IDS = ['5420443671']  # 5420443671 nurik

# Birja API sozlamalari
BIRJALAR = {
    'MEXC': ccxt.mexc({'apiKey': 'mx0vgla3g7IOztovJm', 'secret': '317a1a6871db47019462cf1afee4bf9a', 'enableRateLimit': True}),
    'DigiFinex': ccxt.digifinex({'apiKey': '3e5a26fcdeacc6', 'secret': '64a0b6a1b4302175ecd9e2a98da508a1b3dcf5eab6', 'enableRateLimit': True}),
    'Binance': ccxt.binance({'apiKey': 'AYRtXtmyzYcG3M8yBeOWl3PM7JSeYccVeHokbBvGrkuylYk0KTKbRQEKWn4qvrtS', 'secret': '89HxAY4ci6onvb7YlvpIqvZuov5R8TgFTdwyL52rHibWx3w365nJ7xIzlSYshar8', 'enableRateLimit': True})
}

# Hamma birjalarda mavjud bo'lgan .../USDT juftliklarini olish
def get_usdt_pairs():
    mexc_symbols = set(BIRJALAR['MEXC'].load_markets().keys())
    digifinex_symbols = set(BIRJALAR['DigiFinex'].load_markets().keys())
    binance_symbols = set(BIRJALAR['Binance'].load_markets().keys())

    juftliklar = list(mexc_symbols & digifinex_symbols & binance_symbols)
    return [p for p in juftliklar if p.endswith('/USDT')]

JUFTLIKLAR = get_usdt_pairs()
KUTILISH_VAQTI = 5  # Sekund

# Telegram xabar yuborish funksiyasi
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chat_id in CHAT_IDS:
        try:
            data = {"chat_id": chat_id, "text": message}
            response = requests.post(url, data=data)
            result = response.json()

            if not result.get("ok"):
                error_description = result.get("description", "Noma'lum xatolik")
                print(f"❌ Telegram xatosi ({chat_id}): {error_description}")
            else:
                print(f"✅ Xabar {chat_id} ga yuborildi!")

        except Exception as e:
            print(f"⚠️ Telegram API xatosi: {e}")

# Narxlarni solishtirish funksiyasi
def narxlarni_solishtir():
    try:
        vaqt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        for juftlik in JUFTLIKLAR:
            try:
                # Narxlarni olish
                mex = BIRJALAR['MEXC'].fetch_ticker(juftlik).get('bid')
                digi = BIRJALAR['DigiFinex'].fetch_ticker(juftlik).get('ask')
                binance = BIRJALAR['Binance'].fetch_ticker(juftlik).get('bid')

                # Narxlardan biri None bo‘lsa, bu juftlikni o'tkazib yuboramiz
                if mex is None or digi is None or binance is None:
                    print(f"⚠️ {juftlik} uchun narx mavjud emas, o'tkazib yuborildi.")
                    continue

                # Foiz farqlarni hisoblash
                farq_mex_digi = abs(((digi - mex) / mex) * 100)
                farq_mex_binance = abs(((binance - mex) / mex) * 100)
                farq_digi_binance = abs(((binance - digi) / digi) * 100)

                # 100% dan katta natijalarni ham o'tkazib yuboramiz
                if farq_mex_digi > 100 or farq_mex_binance > 100 or farq_digi_binance > 100:
                    print(f"⚠️ {juftlik} uchun natija juda katta ({farq_mex_digi:.2f}%, {farq_mex_binance:.2f}%, {farq_digi_binance:.2f}%), o'tkazib yuborildi.")
                    continue

                # Agar natija |0.5%| yoki undan katta bo'lsa, Telegramga yuboramiz
                if farq_mex_digi >= 0.5 or farq_mex_binance >= 0.5 or farq_digi_binance >= 0.5:
                    message = f"📊 {vaqt}\n\n"
                    message += f"🔹 *{juftlik}*\n"
                    message += f"  📌 *MEXC:* `{mex:.8f}`\n"
                    message += f"  📌 *DigiFinex:* `{digi:.8f}`\n"
                    message += f"  📌 *Binance:* `{binance:.8f}`\n"
                    message += f"  🔸 *MEXC - DigiFinex:* `{farq_mex_digi:.2f}%`\n"
                    message += f"  🔸 *MEXC - Binance:* `{farq_mex_binance:.2f}%`\n"
                    message += f"  🔸 *DigiFinex - Binance:* `{farq_digi_binance:.2f}%`\n"

                    send_telegram_message(message)

                time.sleep(1)  # API bloklanishining oldini olish

            except Exception as e:
                print(f"⚠️ {juftlik} uchun xato: {e}")

    except Exception as e:
        print(f"Xato yuz berdi: {e}")

# Botni ishga tushirish
if __name__ == '__main__':
    print("✅ Narx farqi monitori ishga tushdi...")
    print("📌 Quyidagi USDT juftliklari uchun narx farqlari tekshiriladi:\n", ', '.join(JUFTLIKLAR))

    send_telegram_message("🚀 Bot ishga tushdi! Narxlarni tekshirish boshlanmoqda...")

    try:
        while True:
            narxlarni_solishtir()
            time.sleep(KUTILISH_VAQTI)
    except KeyboardInterrupt:
        print("❌ Dastur to'xtatildi")
        send_telegram_message("⚠️ Bot to'xtatildi!")
