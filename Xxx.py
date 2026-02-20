import telebot
import requests
from bs4 import BeautifulSoup
import random
import json
import time
import os
import re 
from datetime import datetime

# ---------------------------------------------------------
# ১. বটের টোকেন
BOT_TOKEN = "8195990732:AAGdnFVAbqlOiSIELOWHk7ArS1gm80AFDLY"

# ২. অ্যাডমিন আইডি
ADMIN_ID = "YOUR_ADMIN_ID_HERE" 

# ৩. সাধারণ ভিডিওর ওয়েবসাইট
REGULAR_SITES = [
    "https://fry99.cc/latest-videos/",
    "https://desibf.com/tag/desi-49/page/4/",
    "https://www.desitales2.com/videos/tag/desi49/",
    "https://www.desitales2.com/videos/category/bangla-sex/"
]

# ৪. লাইভ ভিডিওর ওয়েবসাইট
LIVE_SITES = [
    "https://desibf.com/live/", 
    "https://www.desitales2.com/live-cams/"
]

# ৫. ক্লিন প্লেয়ার (যেখানে ভিডিও চলবে)
CLEAN_PLAYER_URL = "https://hlsjs.video-dev.org/demo/?src="
# ---------------------------------------------------------

bot = telebot.TeleBot(BOT_TOKEN)
HISTORY_FILE = "video_history.json"
DEFAULT_THUMB = "https://cdn-icons-png.flaticon.com/512/12560/12560376.png"

# স্ট্যাটাস মেকার
def get_video_stats():
    views = random.randint(5000, 80000)
    likes = int(views * random.uniform(0.05, 0.15))
    return f"{views/1000:.1f}K", f"{likes/1000:.1f}K"

def get_live_watching():
    return f"{random.randint(500, 5000)} Watching Now"

# --- ইউনিভার্সাল লিংক এক্সট্র্যাক্টর (ভিডিও এবং লাইভ দুটোর জন্যই) ---
def get_hidden_stream_link(page_url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(page_url, headers=headers, timeout=8)
        
        # ১. প্রথমে .m3u8 খোঁজা (সবচেয়ে ভালো কোয়ালিটি)
        if ".m3u8" in response.text:
            links = re.findall(r'(https?://[^\s"\'<>]+\.m3u8)', response.text)
            if links:
                return links[0], "m3u8"
        
        # ২. যদি না পায়, .mp4 খোঁজা
        if ".mp4" in response.text:
            links = re.findall(r'(https?://[^\s"\'<>]+\.mp4)', response.text)
            if links:
                return links[0], "mp4"
                
        return None, None
    except: return None, None

# হিস্ট্রি
def load_history():
    if not os.path.exists(HISTORY_FILE): return {}
    try:
        with open(HISTORY_FILE, "r") as f: return json.load(f)
    except: return {}

def save_history(history):
    with open(HISTORY_FILE, "w") as f: json.dump(history, f)

# লগ পাঠানো
def send_log(user, title, url, type_str):
    try:
        if ADMIN_ID != "YOUR_ADMIN_ID_HERE":
            now = datetime.now().strftime("%I:%M %p")
            bot.send_message(ADMIN_ID, f"🔥 **Activity:**\n👤 {user.first_name}\n📌 {type_str}\n📺 {title}\n🔗 {url}", parse_mode='Markdown')
    except: pass

# স্ক্র্যাপার
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
                        candidates.append({
                            "title": title.replace("[", "").replace("]", "").strip(),
                            "url": video_url,
                            "thumb": thumb_url
                        })
        except: continue
    return candidates

@bot.message_handler(func=lambda message: True)
def handle_requests(message):
    chat_id = str(message.chat.id)
    text = message.text.lower()
    
    # ১. ম্যানুয়াল লিংক দিলে
    if text.startswith("http"):
        bot.send_chat_action(chat_id, 'upload_photo')
        
        # ম্যানুয়াল লিংককেও ক্লিন করার চেষ্টা
        hidden_link, ftype = get_hidden_stream_link(text)
        final_url = text
        if hidden_link and ftype == "m3u8":
            final_url = CLEAN_PLAYER_URL + hidden_link
        elif hidden_link and ftype == "mp4":
            final_url = hidden_link

        caption = (
            f"🔴 **CUSTOM PLAYER**\n"
            f"📺 **Title:** Custom Video\n"
            f"🛡 **Status:** Ad-Free Ready ✅\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"▶️ [Click To Play Stream]({final_url})"
        )
        bot.send_photo(chat_id, DEFAULT_THUMB, caption=caption, parse_mode='Markdown')
        send_log(message.from_user, "Manual Link", final_url, "Custom")
        return

    # ২. ভিডিও বা লাইভ চাইলে
    is_live_request = "live" in text
    is_video_request = "video" in text

    if is_live_request or is_video_request:
        bot.send_chat_action(chat_id, 'upload_photo') # টাইপিং দেখাবে
        
        if is_live_request:
            target_list = LIVE_SITES
            mode_live = True
        else:
            target_list = REGULAR_SITES
            mode_live = False

        items = scrape_from_list(target_list, mode_live)
        
        if not items:
            bot.reply_to(message, "⚠️ ডাটা পাওয়া যাচ্ছে না।")
            return

        history = load_history()
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
            # --- ইউনিভার্সাল ক্লিন প্লেয়ার লজিক ---
            bot.send_chat_action(chat_id, 'record_video') # লিংক খুঁজতে একটু সময় নেয়, তাই স্ট্যাটাস দেখাবে
            
            final_url = selected['url']
            is_clean = False
            
            # গোপন লিংক খোঁজা (ভিডিও এবং লাইভ উভয়ের জন্যই)
            hidden_stream, file_type = get_hidden_stream_link(final_url)
            
            if hidden_stream:
                is_clean = True
                if file_type == "m3u8":
                    # m3u8 হলে ক্লিন প্লেয়ারে র‍্যাপ করবে
                    final_url = CLEAN_PLAYER_URL + hidden_stream
                else:
                    # mp4 হলে ডাইরেক্ট লিংক দেবে (ব্রাউজারে অটো প্লে হবে)
                    final_url = hidden_stream

            # --- ডিজাইন ---
            status_txt = "🛡 Ad-Free Player ✅" if is_clean else "🔗 Web Player"
            
            if mode_live:
                watching = get_live_watching()
                caption = (
                    f"🔴 **LIVE NOW**\n"
                    f"📺 *{selected['title']}*\n"
                    f"📝 **Status:** {status_txt}\n"
                    f"👥 **{watching}**\n"
                    f"➖➖➖➖➖➖➖➖➖➖\n"
                    f"▶️ [Click Here To Watch Live]({final_url})"
                )
            else:
                views, likes = get_video_stats()
                caption = (
                    f"🎬 *{selected['title']}*\n"
                    f"📝 **Status:** {status_txt}\n"
                    f"👁 *Views:* {views}   ❤️ *Likes:* {likes}\n"
                    f"➖➖➖➖➖➖➖➖➖➖\n"
                    f"👉 [Click Here To Play Video]({final_url})"
                )

            thumb = selected['thumb'] if selected['thumb'] else DEFAULT_THUMB
            try:
                bot.send_photo(chat_id, thumb, caption=caption, parse_mode='Markdown')
                
                log_type = f"{'🔴 LIVE' if mode_live else '🎬 VIDEO'} ({'Clean' if is_clean else 'Web'})"
                send_log(message.from_user, selected['title'], final_url, log_type)
            except:
                bot.send_message(chat_id, caption, parse_mode='Markdown')

            user_history[selected['url']] = current_time
            history[chat_id] = user_history
            save_history(history)

        else:
            bot.reply_to(message, "🕒 সব দেখা শেষ! কিছুক্ষণ পর আবার চেষ্টা করুন।")

print("Universal Clean Player Bot Started...")
bot.infinity_polling()
