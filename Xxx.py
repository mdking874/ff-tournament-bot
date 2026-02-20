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
ADMIN_ID = 1933498659  # এখানে আপনার আসল Numerical ID দিন (উদ্ধৃতি চিহ্ন ছাড়া)

# ২. ওয়েবসাইট লিস্ট (আগের মতোই)
REGULAR_SITES = [
    "https://fry99.cc/latest-videos/",
    "https://desibf.com/tag/desi-49/page/4/",
    "https://www.desitales2.com/videos/tag/desi49/",
    "https://www.desitales2.com/videos/category/bangla-sex/"
]
LIVE_SITES = ["https://desibf.com/live/", "https://www.desitales2.com/live-cams/"]
CLEAN_PLAYER_URL = "https://hlsjs.video-dev.org/demo/?src="
# ---------------------------------------------------------

bot = telebot.TeleBot(BOT_TOKEN)

# ফাইল ডাটাবেস
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

# --- কি জেনারেটর (দিন এবং কতজন ইউজ করতে পারবে) ---
def generate_key(days, slots):
    key = f"PREMIUM-{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(100, 999)}"
    keys = load_db(KEYS_FILE)
    keys[key] = {
        "days": days,
        "slots": slots  # কতগুলো ডিভাইসে/আইডিতে চলবে
    }
    save_db(KEYS_FILE, keys)
    return key

# --- ভিডিও স্ক্র্যাপার (সংক্ষিপ্ত রাখা হয়েছে) ---
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
                    title = img_tag.get('alt') or ("Live" if is_live_mode else "Video")
                    if not video_url.startswith("http"):
                        base = "/".join(site.split("/")[:3])
                        video_url = base + video_url if video_url.startswith("/") else base + "/" + video_url
                    if len(video_url) > 20:
                        candidates.append({"title": title.strip(), "url": video_url, "thumb": thumb_url})
        except: continue
    return candidates

# --- কমান্ড হ্যান্ডলার ---

@bot.message_handler(commands=['start'])
def welcome(message):
    uid = message.chat.id
    subscribed, expiry = is_subscribed(uid)
    if subscribed:
        msg = f"✅ আপনি প্রিমিয়াম ইউজার।\n📅 মেয়াদ শেষ: {expiry}\n\nভিডিও পেতে 'video' অথবা 'live' লিখুন।"
    else:
        msg = (f"👋 স্বাগতম!\n\nভিডিও দেখতে কি (Key) প্রয়োজন।\n"
               f"💰 কি কিনতে যোগাযোগ করুন: [ADMIN](tg://user?id={ADMIN_ID})\n\n"
               f"কি থাকলে রিডিম করুন: `/redeem YOUR_KEY`")
    bot.send_message(uid, msg, parse_mode='Markdown')

# প্রোফাইল দেখার কমান্ড
@bot.message_handler(commands=['profile'])
def profile(message):
    subscribed, expiry = is_subscribed(message.chat.id)
    if subscribed:
        bot.reply_to(message, f"👤 **আপনার প্রোফাইল:**\n✅ স্ট্যাটাস: প্রিমিয়াম\n⏳ মেয়াদ শেষ হবে: {expiry}")
    else:
        bot.reply_to(message, "❌ আপনার কোনো সক্রিয় সাবস্ক্রিপশন নেই।")

# অ্যাডমিন কমান্ড: কি জেনারেট করা (/gen দিন ডিভাইস_সংখ্যা)
# উদাহরণ: /gen 30 5 (এর মানে ৩০ দিন মেয়াদী কি, যা ৫ জন ইউজ করতে পারবে)
@bot.message_handler(commands=['gen'])
def admin_gen_key(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = message.text.split()
        days = int(args[1])
        slots = int(args[2])
        new_key = generate_key(days, slots)
        bot.reply_to(message, f"🔑 **নতুন কি তৈরি হয়েছে:**\n`{new_key}`\n⏳ মেয়াদ: {days} দিন\n👥 ব্যবহারকারী সীমা: {slots} জন")
    except:
        bot.reply_to(message, "ব্যবহার নিয়ম: `/gen দিন ডিভাইস_সংখ্যা` \nউদাহরণ: `/gen 30 5`")

# অ্যাডমিন কমান্ড: পরিসংখ্যান
@bot.message_handler(commands=['stats'])
def admin_stats(message):
    if message.from_user.id != ADMIN_ID: return
    users = load_db(USER_DATA_FILE)
    keys = load_db(KEYS_FILE)
    bot.reply_to(message, f"📊 **পরিসংখ্যান:**\n👤 মোট প্রিমিয়াম ইউজার: {len(users)}\n🔑 অব্যবহৃত কি আছে: {len(keys)}")

# ইউজার কমান্ড: কি রিডিম করা
@bot.message_handler(commands=['redeem'])
def redeem_key(message):
    try:
        key_input = message.text.split()[1]
        keys = load_db(KEYS_FILE)
        
        if key_input in keys:
            key_data = keys[key_input]
            days = key_data['days']
            slots_left = key_data['slots']
            
            users = load_db(USER_DATA_FILE)
            uid = str(message.chat.id)
            
            # মেয়াদ হিসাব করা
            expiry_date = datetime.now() + timedelta(days=days)
            users[uid] = expiry_date.strftime("%Y-%m-%d %H:%M:%S")
            save_db(USER_DATA_FILE, users)
            
            # স্লট বা ডিভাইস কমানো
            if slots_left > 1:
                keys[key_input]['slots'] = slots_left - 1
            else:
                del keys[key_input] # স্লট শেষ হলে কি ডিলিট
            
            save_db(KEYS_FILE, keys)
            bot.reply_to(message, f"🎉 সফল! আপনার একাউন্ট {days} দিনের জন্য অ্যাক্টিভ হয়েছে।\n(বাকি স্লট: {slots_left - 1})")
        else:
            bot.reply_to(message, "❌ এই কি-টি ভুল অথবা এর ব্যবহারের সীমা শেষ হয়ে গেছে।")
    except:
        bot.reply_to(message, "ব্যবহার: `/redeem YOUR_KEY`")

# মূল ভিডিও লজিক
@bot.message_handler(func=lambda message: True)
def handle_requests(message):
    chat_id = str(message.chat.id)
    text = message.text.lower()
    
    # সাবস্ক্রিপশন চেক
    subscribed, _ = is_subscribed(message.chat.id)
    if not subscribed:
        bot.send_message(chat_id, f"🚫 সাবস্ক্রিপশন নেই!\n\nভিডিও দেখতে কি কিনুন।\n👤 অ্যাডমিন: [যোগাযোগ করুন](tg://user?id={ADMIN_ID})", parse_mode='Markdown')
        return

    if "live" in text or "video" in text:
        bot.send_chat_action(chat_id, 'upload_photo')
        is_live = "live" in text
        target_list = LIVE_SITES if is_live else REGULAR_SITES
        items = scrape_from_list(target_list, is_live)
        
        if not items:
            bot.reply_to(message, "⚠️ ডাটা পাওয়া যাচ্ছে না।")
            return

        random.shuffle(items)
        selected = items[0]
        
        bot.send_chat_action(chat_id, 'record_video')
        final_url = selected['url']
        hidden_stream, ftype = get_hidden_stream_link(final_url)
        
        if hidden_stream:
            final_url = CLEAN_PLAYER_URL + hidden_stream if ftype == "m3u8" else hidden_stream

        caption = f"🎬 *{selected['title']}*\n🛡 Ad-Free Player Ready\n\n▶️ [Watch Now]({final_url})"
        thumb = selected['thumb'] if selected['thumb'] else DEFAULT_THUMB
        
        try:
            bot.send_photo(chat_id, thumb, caption=caption, parse_mode='Markdown')
        except:
            bot.send_message(chat_id, caption, parse_mode='Markdown')

print("Advanced Multi-User Key Bot Started...")
bot.infinity_polling()
