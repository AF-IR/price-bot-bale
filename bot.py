#!/usr/bin/env python3
"""
📊 ربات استعلام قیمت ارز - بازوی بله
ارسال خودکار قیمت‌ها به کانال
⏰ اجرا: 6 صبح تا 12 شب (به وقت ایران)
"""

import json
import os
import logging
import requests
import pytz
from datetime import datetime

# ═══════════════════════════════════════════════════════════
#                    تنظیمات اولیه
# ═══════════════════════════════════════════════════════════

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# آدرس API بله
BALE_API = "https://tapi.bale.ai"

# ═══════════════════════════════════════════════════════════
#                    خواندن تنظیمات
# ═══════════════════════════════════════════════════════════

def load_config():
    """خواندن تنظیمات از فایل و محیط"""
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
#                    ارسال درخواست به API بله
# ═══════════════════════════════════════════════════════════

def send_request(method, data=None):
    """ارسال درخواست به API بله"""
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

# ═══════════════════════════════════════════════════════════
#                    دریافت قیمت کریپتو
# ═══════════════════════════════════════════════════════════

def get_crypto_prices():
    """دریافت قیمت ارزهای دیجیتال از CoinGecko"""
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        'ids': 'bitcoin,ethereum,ripple,solana,binancecoin,dogecoin,cardano,polkadot',
        'vs_currencies': 'usd',
        'include_24hr_change': 'true'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        # نرخ تقریبی دلار به تومان
        dollar_rate = 42000
        
        crypto_data = {}
        for coin, prices in data.items():
            usd = prices.get('usd', 0)
            toman = usd * dollar_rate
            
            crypto_data[coin] = {
                'usd': usd,
                'toman': toman,
                'change_24h': prices.get('usd_24h_change', 0)
            }
        
        return crypto_data
    except Exception as e:
        logger.error(f"خطا در دریافت قیمت کریپتو: {e}")
        return None

# ═══════════════════════════════════════════════════════════
#                    دریافت قیمت طلا و دلار
# ═══════════════════════════════════════════════════════════

def get_market_prices():
    """دریافت قیمت طلا و دلار از tgju.org"""
    try:
        url = "https://tgju.org/api/v1/market/indicator/sana.json"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('data'):
            items = data['data']
            return {
                'gold_18k': items.get('geram18', {}).get('p', 'نامشخص'),
                'gold_24k': items.get('geram24', {}).get('p', 'نامشخص'),
                'dollar': items.get('price_dollar_rl', {}).get('p', 'نامشخص'),
                'euro': items.get('price_eur', {}).get('p', 'نامشخص'),
                'pound': items.get('gbp', {}).get('p', 'نامشخص'),
                'dirham': items.get('aed', {}).get('p', 'نامشخص')
            }
    except Exception as e:
        logger.error(f"خطا در دریافت قیمت بازار: {e}")
    
    return None

# ═══════════════════════════════════════════════════════════
#                    فرمت پیام
# ═══════════════════════════════════════════════════════════

def format_message(crypto_data, market_data, config):
    """فرمت‌بندی پیام نهایی"""
    
    # نام فارسی ارزها
    coin_names = {
        'bitcoin': 'بیت‌کوین ₿',
        'ethereum': 'اتریوم Ξ',
        'ripple': 'ریپل',
        'solana': 'سولانا',
        'binancecoin': 'بایننس کوین',
        'dogecoin': 'دوج‌کوین',
        'cardano': 'کاردانو',
        'polkadot': 'پولکادات'
    }
    
    # زمان فعلی به وقت ایران
    tz = pytz.timezone(config.get('timezone', 'Asia/Tehran'))
    now = datetime.now(tz)
    date_str = now.strftime('%Y/%m/%d')
    time_str = now.strftime('%H:%M')
    
    # ═══════════════════════════════════════════════════════
    #                    ساخت پیام
    # ═══════════════════════════════════════════════════════
    
    message = f"""📊 *جدول قیمت ارز و طلا*

📅 {date_str}  ⏰ {time_str}

🔷 *━━━ ارزهای دیجیتال ━━━* 🔷
"""
    
    # اضافه کردن قیمت کریپتو
    if crypto_data:
        for coin, info in crypto_data.items():
            name = coin_names.get(coin, coin)
            usd = f"{info['usd']:,.0f}".replace(',', '.')
            toman = f"{int(info['toman']):,}".replace(',', '.')
            change = info['change_24h']
            
            # ایموجی تغییر قیمت
            emoji = '🟢' if change >= 0 else '🔴'
            change_str = f"{'+' if change >= 0 else ''}{change:.2f}%"
            
            message += f"""
{emoji} *{name}*
   💵 {usd} دلار
   💰 {toman} تومان
   📈 تغییر ۲۴ ساعته: {change_str}
"""
    
    # اضافه کردن قیمت بازار
    if market_data:
        message += """
🔶 *━━━ طلا و ارز ━━━* 🔶
"""
        
        if market_data.get('dollar'):
            message += f"""
💵 دلار آمریکا: {market_data['dollar']} تومان
"""
        
        if market_data.get('euro'):
            message += f"""
💶 یورو: {market_data['euro']} تومان
"""
        
        if market_data.get('pound'):
            message += f"""
💷 پوند: {market_data['pound']} تومان
"""
        
        if market_data.get('gold_18k'):
            message += f"""
🥇 طلای ۱۸ عیار: {market_data['gold_18k']} تومان
"""
        
        if market_data.get('gold_24k'):
            message += f"""
🏆 طلای ۲۴ عیار: {market_data['gold_24k']} تومان
"""
    
    # تبلیغات کانال
    message += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{config.get('ad_text', '📢')}
🔗 {config.get('ad_link', '')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    return message

# ═══════════════════════════════════════════════════════════
#                    ارسال به کانال
# ═══════════════════════════════════════════════════════════

def send_message(chat_id, text):
    """ارسال پیام به کانال"""
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    }
    return send_request('sendMessage', data)

# ═══════════════════════════════════════════════════════════
#                    اطلاع به ادمین
# ═══════════════════════════════════════════════════════════

def notify_admin(admin_id, status, details=""):
    """اطلاع‌رسانی به ادمین"""
    
    status_emoji = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️'
    }
    
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
    """تابع اصلی اجرای ربات"""
    
    global config
    config = load_config()
    
    logger.info("🤖 ربات استعلام قیمت شروع به کار کرد...")
    
    try:
        # دریافت قیمت‌ها
        crypto_data = get_crypto_prices()
        market_data = get_market_prices()
        
        if not crypto_data and not market_data:
            notify_admin(
                config['admin_id'], 'error',
                'خطا در دریافت قیمت‌ها از API'
            )
            return
        
        # فرمت پیام
        message = format_message(crypto_data, market_data, config)
        
        # ارسال به کانال
        result = send_message(config['channel_id'], message)
        
        if result:
            logger.info("پیام با موفقیت ارسال شد!")
            notify_admin(
                config['admin_id'], 'success',
                f'قیمت‌ها با موفقیت ارسال شد\n'
                f'تعداد ارزهای دیجیتال: {len(crypto_data) if crypto_data else 0}'
            )
        else:
            notify_admin(
                config['admin_id'], 'error',
                'خطا در ارسال پیام به کانال'
            )
            
    except Exception as e:
        logger.error(f"خطای کلی: {e}")
        notify_admin(config['admin_id'], 'error', str(e))

# ═══════════════════════════════════════════════════════════
#                    اجرا
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    main()
