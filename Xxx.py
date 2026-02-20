import telebot
import requests
from bs4 import BeautifulSoup
import random
import json
import time
import os
import re 
from datetime import datetime, timedelta

# ---------------------------------------------------------
# ১. বটের কনফিগ
BOT_TOKEN = "8195990732:AAGdnFVAbqlOiSIELOWHk7ArS1gm80AFDLY"
ADMIN_ID = 1933498659  # এখানে আপনার আসল Telegram Numerical ID দিন (উদ্ধৃতি চিহ্ন ছাড়া)

# ২. সাধারণ ভিডিওর ওয়েবসাইট
REGULAR_SITES = [
    "https://fry99.cc/latest-videos/",
    "https://desibf.com/tag/desi-49/page/4/",
    "https://www.desitales2.com/videos/tag/desi49/",
    "https://www.desitales2.com/videos/category/bangla-sex/"
]

# ৩. লাইভ ভিডিওর ওয়েবসাইট
LIVE_SITES = [
    "https://desibf.com/live/", 
    "https://www.desitales2.com/live-cams/"
]

# ৪. ক্লিন প্লেয়ার
CLEAN_PLAYER_URL = "https://hlsjs.video-dev.org/demo/?src="
# ---------------------------------------------------------

bot = telebot.TeleBot(BOT_TOKEN)

# ডাটাবেস ফাইলসমূহ
HISTORY_FILE = "video_history.json"
USER_DATA_FILE = "users_db.json"
KEYS_FILE = "keys_db.json"
DEFAULT_THUMB = "https://cdn-icons-png.flaticon.com/512/12560/12560376.png"

# --- ডাটাবেস ফাংশন ---
def load_db(file):
    if not os.path.exists(file): return {}
    try:
        with open(file, "r") as f: return json.load(f)
    except: return {}

def save_db(file, data):
    with open(file, "w") as f: json.dump(data, f, indent=4)

# --- সাবস্ক্রিপশন চেক ---
def is_subscribed(user_id):
    users = load_db(USER_DATA_FILE)
    uid = str(user_id)
    if uid in users:
        expiry_date = datetime.strptime(users[uid], "%Y-%m-%d %H:%M:%S")
        if expiry_date > datetime.now():
            return True, users[uid]
    return False, None

# --- কি জেনারেটর ---
def generate_key(days):
    key = f"PREMIUM-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
    keys = load_db(KEYS_FILE)
    keys[key] = days
    save_db(KEYS_FILE, keys)
    return key

# --- ভিডিও স্ক্র্যাপার ও অন্যান্য ---
def get_video_stats():
    views = random.randint(5000, 80000)
    likes = int(views * random.uniform(0.05, 0.15))
    return f"{views/1000:.1f}K", f"{likes/1000:.1f}K"

def get_live_watching():
    return f"{random.randint(500, 5000)} Watching Now"

def get_hidden_stream_link(page_url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(page_url, headers=headers, timeout=8)
        if ".m3u8" in response.text:
            links = re.findall(r'(https?://[^\s"\'<>]+\.m3u8)', response.text)
            if links: return links[0], "m3u8"
        if ".mp4" in response.text:
            links = re.findall(r'(https?://[^\s"\'<>]+\.mp4)', response.text)
            if links: return links[0], "mp4"
        return None, None
    except: return None, None

def scrape_from_list(url_list, is_live_mode):
    candidates = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    for site in url_list:
        try:
            response = requests.get(site, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            for link in soup.find_all('a'):
                img_tag = link.find('img')
                if img_tag and link.get('href'):
                    video_url = link.get('href')
                    thumb_url = img_tag.get('src') or img_tag.get('data-src') or img_tag.get('data-original')
                    title = img_tag.get('alt') or ("Live Cam" if is_live_mode else "Hot Video")
                    if not video_url.startswith("http"):
                        base = "/".join(site.split("/")[:3])
                        video_url = base + video_url if video_url.startswith("/") else base + "/" + video_url
                    if thumb_url and not thumb_url.startswith("http"):
                        thumb_url = "https:" + thumb_url if thumb_url.startswith("//") else thumb_url
                    if len(video_url) > 20:
                        candidates.append({"title": title.replace("[", "").replace("]", "").strip(), "url": video_url, "thumb": thumb_url})
        except: continue
    return candidates

# --- কমান্ড হ্যান্ডলার ---

@bot.message_handler(commands=['start'])
def welcome(message):
    uid = message.chat.id
    subscribed, expiry = is_subscribed(uid)
    
    if subscribed:
        msg = f"✅ আপনি একজন প্রিমিয়াম ইউজার।\n📅 মেয়াদ শেষ হবে: {expiry}\n\nভিডিও দেখতে 'video' অথবা 'live' লিখুন।"
    else:
        msg = (f"👋 স্বাগতম! ভিডিও দেখতে সাবস্ক্রিপশন প্রয়োজন।\n\n"
               f"💰 কি (Key) কিনতে আমাদের অ্যাডমিনের সাথে যোগাযোগ করুন।\n"
               f"👤 অ্যাডমিন: [Contact Admin](tg://user?id={ADMIN_ID})\n\n"
               f"আপনার কাছে কি থাকলে সেটি রিডিম করতে লিখুন:\n`/redeem YOUR_KEY`")
    bot.send_message(uid, msg, parse_mode='Markdown')

# অ্যাডমিন কমান্ড: কি জেনারেট করা (/gen 30)
@bot.message_handler(commands=['gen'])
def admin_gen_key(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        days = int(message.text.split()[1])
        new_key = generate_key(days)
        bot.reply_to(message, f"🔑 **নতুন কি তৈরি হয়েছে:**\n`{new_key}`\n⏳ মেয়াদ: {days} দিন")
    except:
        bot.reply_to(message, "ব্যবহার: `/gen দিন` (যেমন: /gen 30)")

# অ্যাডমিন কমান্ড: ইউজার সংখ্যা দেখা
@bot.message_handler(commands=['stats'])
def admin_stats(message):
    if message.from_user.id != ADMIN_ID: return
    users = load_db(USER_DATA_FILE)
    active_users = 0
    for uid in users:
        if datetime.strptime(users[uid], "%Y-%m-%d %H:%M:%S") > datetime.now():
            active_users += 1
    bot.reply_to(message, f"📊 **বট পরিসংখ্যান:**\n👤 মোট ইউজার: {len(users)}\n✅ সক্রিয় সাবস্ক্রিপশন: {active_users}")

# ইউজার কমান্ড: কি রিডিম করা
@bot.message_handler(commands=['redeem'])
def redeem_key(message):
    try:
        key_input = message.text.split()[1]
        keys = load_db(KEYS_FILE)
        
        if key_input in keys:
            days = keys[key_input]
            users = load_db(USER_DATA_FILE)
            uid = str(message.chat.id)
            
            # মেয়াদ ক্যালকুলেট করা
            expiry_date = datetime.now() + timedelta(days=days)
            users[uid] = expiry_date.strftime("%Y-%m-%d %H:%M:%S")
            
            save_db(USER_DATA_FILE, users)
            del keys[key_input] # কি একবার ব্যবহার হলে ডিলিট
            save_db(KEYS_FILE, keys)
            
            bot.reply_to(message, f"🎉 অভিনন্দন! আপনার একাউন্ট {days} দিনের জন্য প্রিমিয়াম করা হয়েছে।")
        else:
            bot.reply_to(message, "❌ ভুল কি! সঠিক কি দিন অথবা অ্যাডমিনের থেকে কিনুন।")
    except:
        bot.reply_to(message, "ব্যবহার: `/redeem YOUR_KEY`")

# মূল ভিডিও লজিক (সাবস্ক্রিপশন চেকসহ)
@bot.message_handler(func=lambda message: True)
def handle_requests(message):
    chat_id = str(message.chat.id)
    text = message.text.lower()
    
    # সাবস্ক্রিপশন চেক
    subscribed, _ = is_subscribed(message.chat.id)
    if not subscribed:
        bot.send_message(chat_id, f"🚫 আপনার সাবস্ক্রিপশন নেই!\n\nভিডিও দেখতে কি (Key) কিনতে হবে।\n👤 অ্যাডমিন আইডি: `{ADMIN_ID}`\n\nকি কিনলে `/redeem KEY` লিখে মেসেজ দিন।", parse_mode='Markdown')
        return

    # ২. ভিডিও বা লাইভ চাইলে
    is_live_request = "live" in text
    is_video_request = "video" in text

    if is_live_request or is_video_request:
        bot.send_chat_action(chat_id, 'upload_photo')
        
        target_list = LIVE_SITES if is_live_request else REGULAR_SITES
        items = scrape_from_list(target_list, is_live_request)
        
        if not items:
            bot.reply_to(message, "⚠️ ডাটা পাওয়া যাচ্ছে না।")
            return

        history = load_db(HISTORY_FILE)
        user_history = history.get(chat_id, {})
        current_time = time.time()
        random.shuffle(items)
        
        selected = None
        for item in items:
            if item['url'] in user_history:
                if current_time - user_history[item['url']] < 86400: continue
            selected = item
            break
        
        if selected:
            bot.send_chat_action(chat_id, 'record_video')
            final_url = selected['url']
            is_clean = False
            hidden_stream, file_type = get_hidden_stream_link(final_url)
            
            if hidden_stream:
                is_clean = True
                final_url = CLEAN_PLAYER_URL + hidden_stream if file_type == "m3u8" else hidden_stream

            status_txt = "🛡 Ad-Free Player ✅" if is_clean else "🔗 Web Player"
            
            if is_live_request:
                watching = get_live_watching()
                caption = f"🔴 **LIVE NOW**\n📺 *{selected['title']}*\n📝 **Status:** {status_txt}\n👥 **{watching}**\n\n▶️ [Watch Live]({final_url})"
            else:
                views, likes = get_video_stats()
                caption = f"🎬 *{selected['title']}*\n📝 **Status:** {status_txt}\n👁 *Views:* {views}   ❤️ *Likes:* {likes}\n\n👉 [Play Video]({final_url})"

            thumb = selected['thumb'] if selected['thumb'] else DEFAULT_THUMB
            try:
                bot.send_photo(chat_id, thumb, caption=caption, parse_mode='Markdown')
            except:
                bot.send_message(chat_id, caption, parse_mode='Markdown')

            user_history[selected['url']] = current_time
            history[chat_id] = user_history
            save_db(HISTORY_FILE, history)
        else:
            bot.reply_to(message, "🕒 সব দেখা শেষ! কিছুক্ষণ পর আবার চেষ্টা করুন।")

print("Premium Video Bot Started...")
bot.infinity_polling()
