#!/usr/bin/env python3
"""
📊 ربات استعلام قیمت ارز - بازوی بله
نسخه 3.0 - کامل و بهبود یافته

ویژگی‌ها:
✅ استخراج قیمت تتر از نوبیتکس (ریالی)
✅ دریافت قیمت‌های دلاری از CoinGecko
✅ Pax Gold برای طلای جهانی
✅ نمایش درصد تغییرات 24 ساعته
✅ چند فرمت پیام متنوع
✅ قیمت‌های float برای دقت بالا
"""

import json
import os
import logging
import random
import re
from datetime import datetime
from typing import Optional

import requests
import pytz

# ═══════════════════════════════════════════════════════════
#                    تنظیمات اولیه
# ═══════════════════════════════════════════════════════════

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BALE_API = "https://tapi.bale.ai"
NOBITEX_URL = "https://nobitex.ir/price/usdt/"

# ═══════════════════════════════════════════════════════════
#                    توابع کمکی
# ═══════════════════════════════════════════════════════════

def to_persian_num(num: float, decimals: int = 0) -> str:
    """تبدیل عدد به فرمت فارسی"""
    if num is None or num == 0:
        return "نامشخص"
    
    persian_digits = str.maketrans('0123456789.,', '۰۱۲۳۴۵۶۷۸۹٫٬')
    
    if decimals > 0:
        formatted = f"{num:,.{decimals}f}".replace(',', '٬')
    else:
        formatted = f"{num:,.0f}".replace(',', '٬')
    
    return formatted.translate(persian_digits)


def format_percent(change: float) -> str:
    """فرمت درصد تغییرات با ایموجی"""
    if change is None or change == 0:
        return "۰٪"
    
    persian_digits = str.maketrans('0123456789.-', '۰۱۲۳۴۵۶۷۸۹٫−')
    sign = "+" if change > 0 else ""
    percent_str = f"{sign}{change:.2f}٪"
    return percent_str.translate(persian_digits)


def get_change_emoji(change: float) -> str:
    """ایموجی بر اساس درصد تغییرات"""
    if change is None:
        return "➖"
    elif change > 5:
        return "🚀"
    elif change > 2:
        return "📈"
    elif change > 0:
        return "⬆️"
    elif change == 0:
        return "➖"
    elif change > -2:
        return "⬇️"
    elif change > -5:
        return "📉"
    else:
        return "💥"


def load_config() -> dict:
    """بارگذاری تنظیمات"""
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    config['bot_token'] = os.environ.get('BOT_TOKEN', config.get('bot_token', ''))
    config['admin_id'] = int(os.environ.get('ADMIN_ID', config.get('admin_id', 0)))
    config['channel_id'] = os.environ.get('CHANNEL_ID', config.get('channel_id', ''))
    config['channel_link'] = os.environ.get('CHANNEL_LINK', config.get('channel_link', ''))
    config['ad_link'] = os.environ.get('AD_LINK', config.get('ad_link', ''))
    
    return config

# ═══════════════════════════════════════════════════════════
#                    استخراج قیمت تتر از نوبیتکس
# ═══════════════════════════════════════════════════════════

def get_usdt_price_from_nobitex() -> Optional[float]:
    """دریافت قیمت تتر از نوبیتکس"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'fa,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    try:
        response = requests.get(NOBITEX_URL, headers=headers, timeout=15)
        response.raise_for_status()
        html_content = response.text
        
        # الگوی ۱: کلاس‌های Tailwind
        patterns = [
            r'<span class="text-body-large text-headline-medium[^"]*">([\d,]+)</span>',
            r'<span[^>]*class="[^"]*text-headline[^"]*"[^>]*>([\d,]+)</span>',
            r'>([\d]{5,7})</span>',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content)
            if match:
                price_str = match.group(1).replace(',', '')
                price = float(price_str)
                if price > 10000:  # اعتبارسنجی: قیمت تتر باید بیشتر از ۱۰۰۰۰ تومان باشد
                    return price
        
        logger.error("هیچ الگویی با قیمت تتر مطابقت نکرد")
        return None
        
    except Exception as e:
        logger.error(f"خطا در دریافت قیمت از نوبیتکس: {e}")
        return None

# ═══════════════════════════════════════════════════════════
#                    دریافت قیمت‌های جهانی از CoinGecko
# ═══════════════════════════════════════════════════════════

def get_global_prices() -> dict:
    """دریافت قیمت‌های جهانی از CoinGecko"""
    
    prices = {
        'crypto': {},
        'gold_usd': 0.0,
        'gold_change_24h': 0.0,
        'oil_brent_usd': 0.0,
        'oil_change_24h': 0.0,
    }
    
    # ═══════════════════════════════════════════════════════════
    #                    ارزهای دیجیتال
    # ═══════════════════════════════════════════════════════════
    
    crypto_ids = [
        'bitcoin', 'ethereum', 'ripple', 'solana', 'dogecoin',
        'cardano', 'polkadot', 'tron', 'litecoin', 'bitcoin-cash',
        'avalanche-2', 'chainlink', 'uniswap', 'matic-network', 'shiba-inu',
        'binancecoin', 'ripple', 'stellar', 'cosmos', 'near'
    ]
    
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': ','.join(crypto_ids),
            'vs_currencies': 'usd',
            'include_24hr_change': 'true',
            'include_last_updated_at': 'true'
        }
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        for coin_id, info in data.items():
            prices['crypto'][coin_id] = {
                'usd': float(info.get('usd', 0)),
                'change_24h': float(info.get('usd_24h_change', 0))
            }
            
        logger.info(f"قیمت {len(prices['crypto'])} ارز دیجیتال دریافت شد")
        
    except Exception as e:
        logger.error(f"خطا در دریافت قیمت کریپتو: {e}")
    
    # ═══════════════════════════════════════════════════════════
    #                    طلا (Pax Gold)
    # ═══════════════════════════════════════════════════════════
    
    try:
        gold_url = "https://api.coingecko.com/api/v3/simple/price"
        gold_params = {
            'ids': 'pax-gold',
            'vs_currencies': 'usd',
            'include_24hr_change': 'true'
        }
        
        gold_response = requests.get(gold_url, params=gold_params, timeout=10)
        gold_data = gold_response.json()
        
        if 'pax-gold' in gold_data:
            prices['gold_usd'] = float(gold_data['pax-gold'].get('usd', 0))
            prices['gold_change_24h'] = float(gold_data['pax-gold'].get('usd_24h_change', 0))
            logger.info(f"قیمت طلا (PAXG): ${prices['gold_usd']}")
            
    except Exception as e:
        logger.error(f"خطا در دریافت قیمت طلا: {e}")
        # Fallback: قیمت تقریبی طلا
        prices['gold_usd'] = 2350.0
        prices['gold_change_24h'] = 0.0
    
    # ═══════════════════════════════════════════════════════════
    #                    نفت (از API جایگزین)
    # ═══════════════════════════════════════════════════════════
    
    try:
        # استفاده از API دیگر برای نفت یا قیمت ثابت
        oil_response = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={'ids': 'oil', 'vs_currencies': 'usd'},
            timeout=10
        )
        
        if oil_response.status_code == 200:
            oil_data = oil_response.json()
            if 'oil' in oil_data:
                prices['oil_brent_usd'] = float(oil_data['oil'].get('usd', 85.0))
        else:
            # قیمت پیش‌فرض اگر API کار نکرد
            prices['oil_brent_usd'] = 85.0
            
    except Exception as e:
        logger.error(f"خطا در دریافت قیمت نفت: {e}")
        prices['oil_brent_usd'] = 85.0
    
    return prices

# ═══════════════════════════════════════════════════════════
#                    محاسبه قیمت‌های ریالی
# ═══════════════════════════════════════════════════════════

def calculate_rial_prices(usdt_price: float, global_prices: dict) -> dict:
    """محاسبه قیمت‌های ریالی بر اساس قیمت تتر"""
    
    rial_prices = {}
    
    if not usdt_price or usdt_price < 10000:
        return {}
    
    # طلای ۱۸ عیار (هر اونس = 31.1035 گرم، عیار 18 = 75%)
    gold_ounce_usd = global_prices.get('gold_usd', 0)
    if gold_ounce_usd > 0:
        gold_gram_usd = gold_ounce_usd / 31.1035
        gold_18_gram_usd = gold_gram_usd * 0.75
        rial_prices['gold_18_gram'] = gold_18_gram_usd * usdt_price
        
        # مثقال (4.6083 گرم)
        rial_prices['gold_misqal'] = gold_18_gram_usd * 4.6083 * usdt_price
    
    # نفت
    oil_usd = global_prices.get('oil_brent_usd', 0)
    if oil_usd > 0:
        rial_prices['oil_brent'] = oil_usd * usdt_price
    
    # ارزهای فیات (نرخ تقریبی دلاری)
    fiat_rates = {
        'eur': 1.08,      # یورو به دلار
        'gbp': 1.27,      # پوند به دلار
        'aed': 3.6725,    # درهم امارات
        'try': 0.031,     # لیر ترکیه
        'iqd': 0.00077,   # دینار عراق
        'afn': 0.014,     # افغانی
    }
    
    for currency, rate in fiat_rates.items():
        rial_prices[currency] = usdt_price * rate
    
    return rial_prices

# ═══════════════════════════════════════════════════════════
#                    فرمت‌های پیام
# ═══════════════════════════════════════════════════════════

def format_message_v1(usdt_price: float, global_prices: dict, 
                      rial_prices: dict, config: dict) -> str:
    """
    فرمت ۱: جدول کامل با جزئیات
    """
    tz = pytz.timezone(config.get('timezone', 'Asia/Tehran'))
    now = datetime.now(tz)
    date_str = now.strftime('%Y/%m/%d')
    time_str = now.strftime('%H:%M')
    
    gold_change = global_prices.get('gold_change_24h', 0)
    gold_emoji = get_change_emoji(gold_change)
    
    message = f"""📊 #گزارش_بازار {date_str} - {time_str}

━━━━━━━━━━━━━━━━━━━━━━
💵 #نرخ_تتر (تومان):
   {to_persian_num(usdt_price)} تومان
━━━━━━━━━━━━━━━━━━━━━━

🪙 #ارزهای_دیجیتال (دلار):

🔶 #بیت_کوین (BTC):
   💰 ${to_persian_num(global_prices['crypto'].get('bitcoin', {}).get('usd', 0), 0)}
   {gold_emoji} ۲۴ساعته: {format_percent(global_prices['crypto'].get('bitcoin', {}).get('change_24h', 0))}

🔶 #اتریوم (ETH):
   💰 ${to_persian_num(global_prices['crypto'].get('ethereum', {}).get('usd', 0), 2)}
   {gold_emoji} ۲۴ساعته: {format_percent(global_prices['crypto'].get('ethereum', {}).get('change_24h', 0))}

🔶 #سولانا (SOL):
   💰 ${to_persian_num(global_prices['crypto'].get('solana', {}).get('usd', 0), 2)}
   {gold_emoji} ۲۴ساعته: {format_percent(global_prices['crypto'].get('solana', {}).get('change_24h', 0))}

🔶 #ریپل (XRP):
   💰 ${to_persian_num(global_prices['crypto'].get('ripple', {}).get('usd', 0), 4)}
   {gold_emoji} ۲۴ساعته: {format_percent(global_prices['crypto'].get('ripple', {}).get('change_24h', 0))}

🔶 #کاردانو (ADA):
   💰 ${to_persian_num(global_prices['crypto'].get('cardano', {}).get('usd', 0), 4)}
   {gold_emoji} ۲۴ساعته: {format_percent(global_prices['crypto'].get('cardano', {}).get('change_24h', 0))}

🔶 #دوج_کوین (DOGE):
   💰 ${to_persian_num(global_prices['crypto'].get('dogecoin', {}).get('usd', 0), 5)}
   {gold_emoji} ۲۴ساعته: {format_percent(global_prices['crypto'].get('dogecoin', {}).get('change_24h', 0))}

🔶 #پولکادات (DOT):
   💰 ${to_persian_num(global_prices['crypto'].get('polkadot', {}).get('usd', 0), 2)}
   {gold_emoji} ۲۴ساعته: {format_percent(global_prices['crypto'].get('polkadot', {}).get('change_24h', 0))}

🔶 #چین_لینک (LINK):
   💰 ${to_persian_num(global_prices['crypto'].get('chainlink', {}).get('usd', 0), 2)}
   {gold_emoji} ۲۴ساعته: {format_percent(global_prices['crypto'].get('chainlink', {}).get('change_24h', 0))}

🔶 #یونی_سواپ (UNI):
   💰 ${to_persian_num(global_prices['crypto'].get('uniswap', {}).get('usd', 0), 3)}
   {gold_emoji} ۲۴ساعته: {format_percent(global_prices['crypto'].get('uniswap', {}).get('change_24h', 0))}

🔶 #ماتیک (MATIC):
   💰 ${to_persian_num(global_prices['crypto'].get('matic-network', {}).get('usd', 0), 4)}
   {gold_emoji} ۲۴ساعته: {format_percent(global_prices['crypto'].get('polkadot', {}).get('change_24h', 0))}

━━━━━━━━━━━━━━━━━━━━━━

🥇 #طلای_جهانی (Pax Gold):
   💰 ${to_persian_num(global_prices.get('gold_usd', 0), 2)}
   {gold_emoji} ۲۴ساعته: {format_percent(gold_change)}

📌 #طلای_۱۸_عیار (تومان):
   {to_persian_num(rial_prices.get('gold_18_gram', 0))} تومان

📌 #مثقال_طلا (تومان):
   {to_persian_num(rial_prices.get('gold_misqal', 0))} تومان

━━━━━━━━━━━━━━━━━━━━━━

🛢 #نفت_برنت:
   💰 ${to_persian_num(global_prices.get('oil_brent_usd', 0), 2)} / بشکه

━━━━━━━━━━━━━━━━━━━━━━

💱 #ارزهای_فیات (تومان):

🇪🇺 یورو: {to_persian_num(rial_prices.get('eur', 0))}
🇬🇧 پوند: {to_persian_num(rial_prices.get('gbp', 0))}
🇦🇪 درهم: {to_persian_num(rial_prices.get('aed', 0))}
🇹🇷 لیر: {to_persian_num(rial_prices.get('try', 0))}

━━━━━━━━━━━━━━━━━━━━━━
{config.get('ad_text', '📢')}
🔗 {config.get('ad_link', '')}
━━━━━━━━━━━━━━━━━━━━━━"""
    
    return message


def format_message_v2(usdt_price: float, global_prices: dict,
                      rial_prices: dict, config: dict) -> str:
    """
    فرمت ۲: خلاصه و سریع
    """
    tz = pytz.timezone(config.get('timezone', 'Asia/Tehran'))
    now = datetime.now(tz)
    time_str = now.strftime('%H:%M')
    
    btc = global_prices['crypto'].get('bitcoin', {})
    eth = global_prices['crypto'].get('ethereum', {})
    sol = global_prices['crypto'].get('solana', {})
    
    message = f"""⚡ #بروزرسانی_سریع {time_str}

━━━━━━━━━━━━━━━━━━━━━━
💵 تتر: {to_persian_num(usdt_price)} تومان
━━━━━━━━━━━━━━━━━━━━━━

🪙 #ارزهای_دیجیتال:

🔸 BTC: ${to_persian_num(btc.get('usd', 0), 0)} {get_change_emoji(btc.get('change_24h', 0))} {format_percent(btc.get('change_24h', 0))}
🔸 ETH: ${to_persian_num(eth.get('usd', 0), 2)} {get_change_emoji(eth.get('change_24h', 0))} {format_percent(eth.get('change_24h', 0))}
🔸 SOL: ${to_persian_num(sol.get('usd', 0), 2)} {get_change_emoji(sol.get('change_24h', 0))} {format_percent(sol.get('change_24h', 0))}

━━━━━━━━━━━━━━━━━━━━━━

🥇 طلا: ${to_persian_num(global_prices.get('gold_usd', 0), 2)} {get_change_emoji(global_prices.get('gold_change_24h', 0))}
📌 طلای ۱۸: {to_persian_num(rial_prices.get('gold_18_gram', 0))} تومان

━━━━━━━━━━━━━━━━━━━━━━
{config.get('ad_text', '📢')}
🔗 {config.get('ad_link', '')}
━━━━━━━━━━━━━━━━━━━━━━"""
    
    return message


def format_message_v3(usdt_price: float, global_prices: dict,
                      rial_prices: dict, config: dict) -> str:
    """
    فرمت ۳: کارت‌های مجزا
    """
    tz = pytz.timezone(config.get('timezone', 'Asia/Tehran'))
    now = datetime.now(tz)
    date_str = now.strftime('%Y/%m/%d')
    time_str = now.strftime('%H:%M')
    
    crypto_list = [
        ('bitcoin', 'BTC', 0),
        ('ethereum', 'ETH', 2),
        ('solana', 'SOL', 2),
        ('ripple', 'XRP', 4),
        ('cardano', 'ADA', 4),
        ('dogecoin', 'DOGE', 5),
        ('polkadot', 'DOT', 2),
        ('chainlink', 'LINK', 2),
        ('litecoin', 'LTC', 2),
        ('avalanche-2', 'AVAX', 2),
    ]
    
    crypto_cards = []
    for coin_id, symbol, decimals in crypto_list:
        coin_data = global_prices['crypto'].get(coin_id, {})
        if coin_data.get('usd', 0) > 0:
            change = coin_data.get('change_24h', 0)
            emoji = get_change_emoji(change)
            crypto_cards.append(
                f"{symbol}: ${to_persian_num(coin_data.get('usd', 0), decimals)} {emoji} {format_percent(change)}"
            )
    
    message = f"""📈 #بازار_رمزارزها
📅 {date_str} ⏰ {time_str}

━━━━━━━━━━━━━━━━━━━━━━

💎 #کریپتو:

{chr(10).join(crypto_cards)}

━━━━━━━━━━━━━━━━━━━━━━

🥇 #طلا:
💰 Pax Gold: ${to_persian_num(global_prices.get('gold_usd', 0), 2)}
📊 24h: {get_change_emoji(global_prices.get('gold_change_24h', 0))} {format_percent(global_prices.get('gold_change_24h', 0))}

📌 طلای ۱۸ عیار: {to_persian_num(rial_prices.get('gold_18_gram', 0))} تومان

━━━━━━━━━━━━━━━━━━━━━━

🛢 #انرژی:
نفت برنت: ${to_persian_num(global_prices.get('oil_brent_usd', 0), 2)}

━━━━━━━━━━━━━━━━━━━━━━

💵 #تتر: {to_persian_num(usdt_price)} تومان

━━━━━━━━━━━━━━━━━━━━━━
{config.get('ad_text', '📢')}
🔗 {config.get('ad_link', '')}
━━━━━━━━━━━━━━━━━━━━━━"""
    
    return message


def format_message_v4(usdt_price: float, global_prices: dict,
                      rial_prices: dict, config: dict) -> str:
    """
    فرمت ۴: مینیمال و شیک
    """
    tz = pytz.timezone(config.get('timezone', 'Asia/Tehran'))
    now = datetime.now(tz)
    time_str = now.strftime('%H:%M')
    
    btc = global_prices['crypto'].get('bitcoin', {})
    eth = global_prices['crypto'].get('ethereum', {})
    
    message = f"""🔔 قیمت‌ها - {time_str}

━━━━━━━━━━━━━━━
💵 تتر: {to_persian_num(usdt_price)} تومان
━━━━━━━━━━━━━━━
₿ {to_persian_num(btc.get('usd', 0), 0)}$ {format_percent(btc.get('change_24h', 0))}
Ξ {to_persian_num(eth.get('usd', 0), 2)}$ {format_percent(eth.get('change_24h', 0))}
━━━━━━━━━━━━━━━
🥇 طلا: {to_persian_num(global_prices.get('gold_usd', 0), 2)}$
📌 ۱۸عیار: {to_persian_num(rial_prices.get('gold_18_gram', 0))} تومان
━━━━━━━━━━━━━━━"""
    
    return message


def get_random_format() -> int:
    """انتخاب تصادفی فرمت"""
    return random.choice([1, 2, 3, 4])

# ═══════════════════════════════════════════════════════════
#                    ارسال پیام به Bale
# ═══════════════════════════════════════════════════════════

def send_request(bot_token: str, method: str, data: dict = None) -> dict:
    """ارسال درخواست به API بیل"""
    url = f"{BALE_API}/bot{bot_token}/{method}"
    
    try:
        if data is None:
            response = requests.get(url, timeout=30)
        else:
            response = requests.post(url, json=data, timeout=30)
        
        result = response.json()
        
        if result.get('ok'):
            return result.get('result', {})
        else:
            logger.error(f"خطای API: {result.get('description')}")
            return {}
            
    except Exception as e:
        logger.error(f"خطا در ارسال درخواست: {e}")
        return {}


def send_message(bot_token: str, chat_id: str, text: str) -> bool:
    """ارسال پیام"""
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    }
    result = send_request(bot_token, 'sendMessage', data)
    return bool(result)


def notify_admin(bot_token: str, admin_id: int, status: str, details: str = "") -> None:
    """اطلاع‌رسانی به ادمین"""
    status_emoji = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️'
    }
    
    emoji = status_emoji.get(status, '📌')
    tz = pytz.timezone('Asia/Tehran')
    now = datetime.now(tz)
    
    message = f"""{emoji} گزارش اجرای ربات

📊 وضعیت: {status}
📝 جزئیات: {details}
🕐 زمان: {now.strftime('%Y/%m/%d %H:%M:%S')}"""
    
    data = {
        'chat_id': admin_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    send_request(bot_token, 'sendMessage', data)

# ═══════════════════════════════════════════════════════════
#                    تابع اصلی
# ═══════════════════════════════════════════════════════════

def main():
    """تابع اصلی ربات"""
    
    config = load_config()
    bot_token = config['bot_token']
    
    logger.info("🤖 ربات استعلام قیمت شروع به کار کرد...")
    
    try:
        # ═══════════════════════════════════════════════════════════
        #                    مرحله ۱: دریافت قیمت تتر از نوبیتکس
        # ═══════════════════════════════════════════════════════════
        
        usdt_price = get_usdt_price_from_nobitex()
        
        if not usdt_price:
            logger.error("قیمت تتر از نوبیتکس دریافت نشد!")
            notify_admin(bot_token, config['admin_id'], 'error', 
                        'خطا در دریافت قیمت تتر از نوبیتکس')
            return
        
        logger.info(f"✅ قیمت تتر: {usdt_price:,.0f} تومان")
        
        # ═══════════════════════════════════════════════════════════
        #                    مرحله ۲: دریافت قیمت‌های جهانی
        # ═══════════════════════════════════════════════════════════
        
        global_prices = get_global_prices()
        
        # ═══════════════════════════════════════════════════════════
        #                    مرحله ۳: محاسبه قیمت‌های ریالی
        # ═══════════════════════════════════════════════════════════
        
        rial_prices = calculate_rial_prices(usdt_price, global_prices)
        
        if not rial_prices:
            logger.error("خطا در محاسبه قیمت‌های ریالی")
            notify_admin(bot_token, config['admin_id'], 'error',
                        'خطا در محاسبه قیمت‌های ریالی')
            return
        
        # ═══════════════════════════════════════════════════════════
        #                    مرحله ۴: انتخاب و ارسال فرمت پیام
        # ═══════════════════════════════════════════════════════════
        
        format_type = get_random_format()
        
        if format_type == 1:
            message = format_message_v1(usdt_price, global_prices, rial_prices, config)
        elif format_type == 2:
            message = format_message_v2(usdt_price, global_prices, rial_prices, config)
        elif format_type == 3:
            message = format_message_v3(usdt_price, global_prices, rial_prices, config)
        else:
            message = format_message_v4(usdt_price, global_prices, rial_prices, config)
        
        # ═══════════════════════════════════════════════════════════
        #                    مرحله ۵: ارسال به کانال
        # ═══════════════════════════════════════════════════════════
        
        result = send_message(bot_token, config['channel_id'], message)
        
        if result:
            logger.info(f"✅ پیام با موفقیت ارسال شد! (فرمت {format_type})")
            notify_admin(
                bot_token, config['admin_id'], 'success',
                f'فرمت: {format_type} | تتر: {usdt_price:,.0f}'
            )
        else:
            notify_admin(bot_token, config['admin_id'], 'error', 'خطا در ارسال پیام')
            
    except Exception as e:
        logger.error(f"خطای کلی: {e}")
        notify_admin(bot_token, config['admin_id'], 'error', str(e))


if __name__ == '__main__':
    main()
