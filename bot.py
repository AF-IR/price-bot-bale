#!/usr/bin/env python3
"""
📊 ربات استعلام قیمت ارز - بازوی بله
نسخه پیشرفته:
1. استخراج قیمت تتر (USDT) از نوبیتکس (نوبیتکس.ir)
2. محاسبه سایر قیمت‌ها بر اساس قیمت تتر
3. فرمت‌بندی متنوع با هشتگ‌ها
4. ارسال به کانال و اطلاع به ادمین
"""

import json
import os
import logging
import requests
import pytz
import re
from datetime import datetime

# ═══════════════════════════════════════════════════════════
#                    تنظیمات اولیه
# ═══════════════════════════════════════════════════════════

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BALE_API = "https://tapi.bale.ai"

# لینک نوبیتکس برای استخراج قیمت
NOBITEX_URL = "https://nobitex.ir/price/usdt/"

# ═══════════════════════════════════════════════════════════
#                    خواندن تنظیمات
# ═══════════════════════════════════════════════════════════

def load_config():
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # جایگزینی مقادیر از Environment Variables (Secrets)
    config['bot_token'] = os.environ.get('BOT_TOKEN', config['bot_token'])
    config['admin_id'] = int(os.environ.get('ADMIN_ID', config['admin_id']))
    config['channel_id'] = os.environ.get('CHANNEL_ID', config['channel_id'])
    config['channel_link'] = os.environ.get('CHANNEL_LINK', config['channel_link'])
    config['ad_link'] = os.environ.get('AD_LINK', config['ad_link'])
    
    return config

# ═══════════════════════════════════════════════════════════
#                    استخراج قیمت تتر از نوبیتکس
# ═══════════════════════════════════════════════════════════

def get_usdt_price_from_nobitex():
    """
    دریافت قیمت تتر از نوبیتکس با Parse کردن HTML
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(NOBITEX_URL, headers=headers, timeout=10)
        response.raise_for_status()
        
        html_content = response.text
        
        # الگوی استخراج قیمت از span با کلاس مشخص شده
        # مثال: <span class="text-body-large text-headline-medium desktop:text-headline-large">170,994</span>
        pattern = r'<span class="text-body-large text-headline-medium desktop:text-headline-large">([\d,]+)</span>'
        match = re.search(pattern, html_content)
        
        if match:
            price_str = match.group(1).replace(',', '')
            return float(price_str)
        else:
            logger.error("الگوی HTML در نوبیتکس پیدا نشد. ممکن است ساختار صفحه تغییر کرده باشد.")
            return None
            
    except Exception as e:
        logger.error(f"خطا در دریافت قیمت از نوبیتکس: {e}")
        return None

# ═══════════════════════════════════════════════════════════
#                    دریافت قیمت‌های جهانی (دلاری)
# ═══════════════════════════════════════════════════════════

def get_global_prices():
    """
    دریافت قیمت‌های جهانی ارزهای دیجیتال، طلا، نفت و ...
    """
    prices = {}
    
    # 1. ارزهای دیجیتال (CoinGecko)
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': 'bitcoin,ethereum,ripple,solana,dogecoin,cardano,polkadot,tron,litecoin,bitcoin-cash',
            'vs_currencies': 'usd',
            'include_24hr_change': 'true'
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        crypto_data = {}
        for coin, info in data.items():
            crypto_data[coin] = {
                'usd': info.get('usd', 0),
                'change_24h': info.get('usd_24h_change', 0)
            }
        prices['crypto'] = crypto_data
    except Exception as e:
        logger.error(f"خطا در دریافت قیمت کریپتو: {e}")

    # 2. طلا، نفت و ارزهای fiat (از APIهای عمومی یا محاسبه دستی)
    # برای سادگی و پایداری، قیمت‌های ثابت یا APIهای رایگان دیگر را استفاده می‌کنیم
    # توجه: برای قیمت دقیق طلا و نفت در ایران، معمولاً باید از سایت‌های داخلی parse کرد
    # اینجا از یک API عمومی برای قیمت جهانی طلا و نفت استفاده می‌کنیم
    
    try:
        # قیمت جهانی انس طلا
        gold_url = "https://api.gold-api.com/price/XAU"
        gold_resp = requests.get(gold_url, timeout=10)
        gold_data = gold_resp.json()
        prices['gold_ounce_usd'] = gold_data.get('price', 0)
        
        # قیمت نفت برنت (تخمینی از API عمومی یا جایگزین)
        # نکته: API رایگان پایدار برای نفت کمیاب است. اینجا از یک منبع جایگزین استفاده می‌کنیم
        oil_url = "https://api.metals.live/v1/spot/gold" # فقط طلاست، برای نفت باید منبع دیگری داشت
        # برای نفت، از یک قیمت تقریبی یا API دیگر استفاده می‌کنیم. 
        # چون API رایگان پایدار نداریم، اینجا قیمت را به صورت نمونه می‌گذاریم.
        # شما می‌توانید API اختصاصی خود را جایگزین کنید.
        prices['oil_brent_usd'] = 85.0 # قیمت نمونه - لطفاً API واقعی جایگزین کنید
        prices['oil_light_usd'] = 80.0 # قیمت نمونه
        
    except Exception as e:
        logger.error(f"خطا در دریافت قیمت جهانی طلا و نفت: {e}")
        prices['gold_ounce_usd'] = 0
        prices['oil_brent_usd'] = 0
        prices['oil_light_usd'] = 0

    return prices

# ═══════════════════════════════════════════════════════════
#                    محاسبه قیمت‌های ریالی
# ═══════════════════════════════════════════════════════════

def calculate_rial_prices(usdt_price, global_prices):
    """
    محاسبه قیمت‌های ریالی بر اساس قیمت تتر
    """
    rial_prices = {}
    
    if not usdt_price:
        return None

    # نرخ‌های تبدیل (تقریبی برای مثال)
    # در واقعیت باید از APIهای معتبر داخلی برای هر کدام استفاده کرد
    # اینجا فرض می‌کنیم قیمت‌های جهانی را داریم و ضرب می‌کنیم
    
    # 1. طلا (گرم 18 عیار)
    # فرمول تقریبی: (انس طلا * نرخ تبدیل انس به گرم) / 0.9 * نرخ دلار
    # انس طلا = 31.1035 گرم
    # طلای 18 عیار = 75% خلوص
    if global_prices.get('gold_ounce_usd'):
        gold_ounce_usd = global_prices['gold_ounce_usd']
        gold_gram_usd = gold_ounce_usd / 31.1035
        gold_18_gram_usd = gold_gram_usd * 0.75
        rial_prices['gold_18_gram'] = gold_18_gram_usd * usdt_price
        
        # مثقال طلا (4.608 گرم)
        rial_prices['gold_misghal'] = (gold_18_gram_usd * 4.608) * usdt_price
    
    # 2. سکه (تخمینی بر اساس انس طلا و حباب)
    # سکه امامی تقریباً معادل 8.133 گرم طلای 18 عیار + حباب
    # حباب متغیر است، اینجا یک فاکتور تقریبی می‌گذاریم
    if global_prices.get('gold_ounce_usd'):
        gold_gram_usd = global_prices['gold_ounce_usd'] / 31.1035
        gold_18_gram_usd = gold_gram_usd * 0.75
        base_coin_price = (8.133 * gold_18_gram_usd) * usdt_price
        # حباب فرضی 50%
        rial_prices['coin_imami'] = base_coin_price * 1.5
        rial_prices['coin_bahar'] = base_coin_price * 1.4 # تقریبی
        rial_prices['coin_half'] = base_coin_price * 0.7
        rial_prices['coin_quarter'] = base_coin_price * 0.35
        rial_prices['coin_gram'] = base_coin_price * 0.1
    
    # 3. ارزهای fiat (یورو، پوند، درهم)
    # نیاز به نرخ تبدیل دلاری دارند
    # فرض: یورو ~ 1.1 دلار، پوند ~ 1.3 دلار، درهم ~ 3.67 دلار
    rial_prices['eur'] = usdt_price * 1.1
    rial_prices['gbp'] = usdt_price * 1.3
    rial_prices['aed'] = usdt_price * 3.67
    rial_prices['cny'] = usdt_price * 0.14 # یوآن
    
    # 4. نفت
    rial_prices['oil_brent'] = global_prices.get('oil_brent_usd', 0) * usdt_price
    rial_prices['oil_light'] = global_prices.get('oil_light_usd', 0) * usdt_price
    
    return rial_prices

# ═══════════════════════════════════════════════════════════
#                    فرمت‌بندی پیام‌ها
# ═══════════════════════════════════════════════════════════

def format_message_v1(usdt_price, global_prices, rial_prices, crypto_prices, config):
    """
    فرمت ۱: جدول کامل با هشتگ‌ها
    """
    tz = pytz.timezone(config.get('timezone', 'Asia/Tehran'))
    now = datetime.now(tz)
    date_str = now.strftime('%A %d %B %Y') # مثلا: سه‌شنبه ۸ اردیبهشت ۱۴۰۵
    
    # تبدیل اعداد به فارسی و فرمت‌بندی
    def to_persian_num(num):
        if num is None or num == 0:
            return "نامشخص"
        # فرمت عدد با جداکننده هزار
        formatted = f"{num:,.0f}".replace(',', '.')
        return formatted

    message = f"""🗓 #قیمت‌های_{date_str.replace(' ', '_')}

🔰 ‌نرخ #ارز_آزاد_(تومان):
‌🇺🇸 (USD)  #دلار: {to_persian_num(usdt_price)}
‌🇪🇺 (EUR)  #یورو: {to_persian_num(rial_prices.get('eur', 0))}
‌🇬🇧 (GBP)  #پوند: {to_persian_num(rial_prices.get('gbp', 0))}
‌🇦🇪 (AED)  #درهم: {to_persian_num(rial_prices.get('aed', 0))}
🇨🇳 یوآن: {to_persian_num(rial_prices.get('cny', 0))} تومان

🔰 قیمت #طلا:
🔅 انس #نقره: (در دسترس نیست)
🔆 #انس_طلا: {to_persian_num(global_prices.get('gold_ounce_usd', 0))} دلار
🔆 #مثقال_طلا: {to_persian_num(rial_prices.get('gold_misghal', 0))} تومان
🔆 #گرم_طلای_۱۸: {to_persian_num(rial_prices.get('gold_18_gram', 0))} تومان

🔰 قیمت #سکه:
🌕 سکه امامی: {to_persian_num(rial_prices.get('coin_imami', 0))}
🌕 بهار آزادی: {to_persian_num(rial_prices.get('coin_bahar', 0))}
🌕 نیم سکه: {to_persian_num(rial_prices.get('coin_half', 0))}
🌕 ربع سکه: {to_persian_num(rial_prices.get('coin_quarter', 0))}
🌕 سکه گرمی: {to_persian_num(rial_prices.get('coin_gram', 0))}

🔰 #سوخت_و_#انرژی:
🛢 نفت برنت: {to_persian_num(global_prices.get('oil_brent_usd', 0))} دلار
🛢 #نفت_سبک: {to_persian_num(global_prices.get('oil_light_usd', 0))} دلار

🔰 #ارز_دیجیتال_(دلار):
"""
    
    # اضافه کردن ارزهای دیجیتال
    coin_names = {
        'bitcoin': 'بیت‌کوین', 'ethereum': 'اتریوم', 'ripple': 'ریپل',
        'solana': 'سولانا', 'dogecoin': 'دوج‌کوین', 'cardano': 'کاردانو',
        'polkadot': 'پولکادات', 'tron': 'تون کوین', 'litecoin': 'لایت‌کوین',
        'bitcoin-cash': 'بیت‌کوین‌کش'
    }
    
    for coin, info in crypto_prices.items():
        name = coin_names.get(coin, coin)
        usd = info['usd']
        change = info['change_24h']
        emoji = '🔸' if change >= 0 else '🔹'
        message += f"{emoji} #{name.replace(' ', '_')}: {to_persian_num(usd)}\n"
    
    message += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{config.get('ad_text', '📢')}
🔗 {config.get('ad_link', '')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return message

def format_message_v2(usdt_price, global_prices, rial_prices, crypto_prices, config):
    """
    فرمت ۲: خلاصه و سریع
    """
    tz = pytz.timezone(config.get('timezone', 'Asia/Tehran'))
    now = datetime.now(tz)
    time_str = now.strftime('%H:%M')
    
    def to_persian_num(num):
        if num is None or num == 0:
            return "نامشخص"
        return f"{num:,.0f}".replace(',', '.')

    message = f"""⚡ #بروزرسانی_سریع_{time_str.replace(':', '_')}

💵 #تتر: {to_persian_num(usdt_price)} تومان
🥇 #طلای_۱۸: {to_persian_num(rial_prices.get('gold_18_gram', 0))} تومان
🪙 #سکه_امامی: {to_persian_num(rial_prices.get('coin_imami', 0))} تومان

📊 #ارز_دیجیتال:
🔹 #بیت_کوین: {to_persian_num(crypto_prices.get('bitcoin', {}).get('usd', 0))}
🔹 #اتریوم: {to_persian_num(crypto_prices.get('ethereum', {}).get('usd', 0))}
🔹 #سولانا: {to_persian_num(crypto_prices.get('solana', {}).get('usd', 0))}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{config.get('ad_text', '📢')}
🔗 {config.get('ad_link', '')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return message

def get_random_format():
    """انتخاب تصادفی فرمت پیام"""
    import random
    return random.choice([1, 2])

# ═══════════════════════════════════════════════════════════
#                    ارسال به کانال
# ═══════════════════════════════════════════════════════════

def send_request(method, data=None):
    url = f"{BALE_API}/bot{config['bot_token']}/{method}"
    try:
        if data is None:
            response = requests.get(url, timeout=30)
        else:
            response = requests.post(url, json=data, timeout=30)
        result = response.json()
        if result.get('ok'):
            return result.get('result')
        else:
            logger.error(f"خطای API: {result.get('description')}")
            return None
    except Exception as e:
        logger.error(f"خطا در ارسال درخواست: {e}")
        return None

def send_message(chat_id, text):
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown' # یا None اگر متن فرمت شده نیست
    }
    return send_request('sendMessage', data)

def notify_admin(admin_id, status, details=""):
    status_emoji = {'success': '✅', 'error': '❌', 'warning': '⚠️'}
    emoji = status_emoji.get(status, '📌')
    tz = pytz.timezone('Asia/Tehran')
    now = datetime.now(tz)
    
    message = f"""{emoji} *گزارش اجرای ربات*
📊 وضعیت: {status}
📝 جزئیات: {details}
🕐 زمان: {now.strftime('%Y/%m/%d %H:%M:%S')}
"""
    data = {
        'chat_id': admin_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    send_request('sendMessage', data)

# ═══════════════════════════════════════════════════════════
#                    تابع اصلی
# ═══════════════════════════════════════════════════════════

def main():
    global config
    config = load_config()
    
    logger.info("🤖 ربات استعلام قیمت شروع به کار کرد...")
    
    try:
        # 1. دریافت قیمت تتر از نوبیتکس
        usdt_price = get_usdt_price_from_nobitex()
        
        if not usdt_price:
            logger.error("قیمت تتر از نوبیتکس دریافت نشد!")
            notify_admin(config['admin_id'], 'error', 'خطا در دریافت قیمت تتر از نوبیتکس')
            return

        logger.info(f"قیمت تتر: {usdt_price} تومان")

        # 2. دریافت قیمت‌های جهانی
        global_prices = get_global_prices()

        # 3. محاسبه قیمت‌های ریالی
        rial_prices = calculate_rial_prices(usdt_price, global_prices)
        
        if not rial_prices:
            logger.error("خطا در محاسبه قیمت‌های ریالی")
            notify_admin(config['admin_id'], 'error', 'خطا در محاسبه قیمت‌های ریالی')
            return

        # 4. استخراج قیمت‌های کریپتو از global_prices
        crypto_prices = global_prices.get('crypto', {})

        # 5. انتخاب فرمت پیام
        format_type = get_random_format()
        
        if format_type == 1:
            message = format_message_v1(usdt_price, global_prices, rial_prices, crypto_prices, config)
        else:
            message = format_message_v2(usdt_price, global_prices, rial_prices, crypto_prices, config)

        # 6. ارسال به کانال
        result = send_message(config['channel_id'], message)
        
        if result:
            logger.info("پیام با موفقیت ارسال شد!")
            notify_admin(
                config['admin_id'], 'success',
                f'فرمت: {format_type}\nقیمت تتر: {usdt_price}'
            )
        else:
            notify_admin(config['admin_id'], 'error', 'خطا در ارسال پیام')
            
    except Exception as e:
        logger.error(f"خطای کلی: {e}")
        notify_admin(config['admin_id'], 'error', str(e))

if __name__ == '__main__':
    main()
