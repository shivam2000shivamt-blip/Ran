#!/usr/bin/env python3
"""
SHIVAM STORE BOT

Render-ready Telegram digital-product store.
Keys are added manually by the owner. Payments are gateway-only; the configured gateway callback verifies payment before delivery.
"""

from __future__ import annotations
import threading
import time

import asyncio
import hashlib
import imaplib
import json
from email import policy
from email.parser import BytesParser
from html import escape
import logging
from math import isfinite
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import os
import re
import secrets
import sqlite3
import struct
import zlib
import urllib.error
import urllib.request
from io import BytesIO
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


# ---------------------------------------------------------------------------
# Localization
# ---------------------------------------------------------------------------
SUPPORTED_LANGUAGES = {
    "en": "🇬🇧 English", "hi": "🇮🇳 हिन्दी", "bn": "🇧🇩 বাংলা",
    "te": "🇮🇳 తెలుగు", "mr": "🇮🇳 मराठी", "ta": "🇮🇳 தமிழ்",
    "gu": "🇮🇳 ગુજરાતી", "kn": "🇮🇳 ಕನ್ನಡ", "ml": "🇮🇳 മലയാളം",
    "pa": "🇮🇳 ਪੰਜਾਬੀ", "or": "🇮🇳 ଓଡ଼ିଆ", "ur": "🇮🇳 اردو",
    "as": "🇮🇳 অসমীয়া",
}

I18N = {
    "en": {
        "shop":"🛍️  Shop Now", "profile":"👤  My Profile", "orders":"📄  My Orders", "wallet":"💰  Wallet",
        "tutorial":"🎓  Tutorial", "reseller":"🤝  Reseller", "support":"🟢  Support", "proof":"📊  Selling Proof",
        "referral":"🤝  Referral", "paid_store":"🏪  Paid Store", "language":"🌐  Language", "back":"‹  Back",
        "back_home":"‹  Back to Main Menu", "choose_language":"🌐 <b>Choose Language</b>\n\nSelect your preferred language:",
        "language_saved":"✅ Language changed successfully.", "choose_category":"📦 <b>Choose a category</b>\n\nSelect where you want to shop.",
        "select_product":"Product select karein:", "plan_select":"<b>Select a plan:</b>", "price":"Price", "reseller_price":"Reseller Price",
        "validity":"Validity", "stock":"Stock", "use_wallet":"💰 Use Wallet Balance", "apply_coupon":"🏷️ Apply Coupon",
        "buy_upi":"💳 Pay via Gateway", "wallet_balance":"Available balance", "recent_activity":"Recent wallet activity",
        "deposit":"➕ Deposit via Gateway", "shop_wallet":"🛒 Shop with Wallet", "completed_orders":"Completed Orders",
        "account":"Account", "balance":"Balance", "role":"Role", "name":"Name", "username":"Username",
        "user_id":"User ID", "verified":"Verified", "not_verified":"Not verified", "successful":"Successful referrals",
        "pending":"Pending referrals", "earned":"Total earned", "reward":"Reward per successful referral",
        "your_link":"🔗 <b>Your referral link</b>", "share_referral":"📤 Share Referral", "referral_program":"🤝 <b>Referral Program</b>",
        "main_menu":"Main Menu", "product":"Product", "plan":"Plan", "days":"Days",
        "profile_title":"👤 <b>My Profile</b>", "joined":"Joined", "completed_orders_label":"Completed Orders",
        "profile_role":"Role", "profile_account":"Account", "profile_balance":"Balance", "profile_overview":"Account Overview", "profile_overview_text":"Your account details, wallet and activity are shown here.",
    },
    "hi": {
        "shop":"🛍️  शॉप नाउ", "profile":"👤  मेरी प्रोफ़ाइल", "orders":"📄  मेरे ऑर्डर", "wallet":"💰  वॉलेट",
        "tutorial":"🎓  ट्यूटोरियल", "reseller":"🤝  रीसेलर", "support":"🟢  सपोर्ट", "proof":"📊  सेलिंग प्रूफ",
        "referral":"🤝  रेफरल", "paid_store":"🏪  पेड स्टोर", "language":"🌐  भाषा", "back":"‹  वापस",
        "back_home":"‹  मुख्य मेनू", "choose_language":"🌐 <b>भाषा चुनें</b>\n\nअपनी पसंदीदा भाषा चुनें:",
        "language_saved":"✅ भाषा सफलतापूर्वक बदल दी गई।", "choose_category":"📦 <b>कैटेगरी चुनें</b>\n\nजहाँ शॉप करना है उसे चुनें।",
        "select_product":"प्रोडक्ट चुनें:", "plan_select":"<b>प्लान चुनें:</b>", "price":"कीमत", "reseller_price":"रीसेलर कीमत",
        "validity":"वैधता", "stock":"स्टॉक", "use_wallet":"💰 वॉलेट बैलेंस इस्तेमाल करें", "apply_coupon":"🏷️ कूपन लगाएँ",
        "buy_upi":"💳 Gateway से भुगतान", "wallet_balance":"उपलब्ध बैलेंस", "recent_activity":"हाल की वॉलेट गतिविधि",
        "deposit":"➕ Gateway से जमा करें", "shop_wallet":"🛒 वॉलेट से शॉप करें", "completed_orders":"पूरे हुए ऑर्डर",
        "account":"अकाउंट", "balance":"बैलेंस", "role":"भूमिका", "name":"नाम", "username":"यूज़रनेम",
        "user_id":"यूज़र ID", "verified":"वेरिफाइड", "not_verified":"वेरिफाइड नहीं", "successful":"सफल रेफरल",
        "pending":"पेंडिंग रेफरल", "earned":"कुल कमाई", "reward":"हर सफल रेफरल का रिवॉर्ड",
        "your_link":"🔗 <b>आपका रेफरल लिंक</b>", "share_referral":"📤 रेफरल शेयर करें", "referral_program":"🤝 <b>रेफरल प्रोग्राम</b>",
        "main_menu":"मुख्य मेनू", "product":"प्रोडक्ट", "plan":"प्लान", "days":"दिन",
        "profile_title":"👤 <b>मेरी प्रोफ़ाइल</b>", "joined":"जॉइन किया", "completed_orders_label":"पूरे हुए ऑर्डर",
        "profile_role":"भूमिका", "profile_account":"अकाउंट", "profile_balance":"बैलेंस", "profile_overview":"अकाउंट ओवरव्यू", "profile_overview_text":"आपकी प्रोफ़ाइल, वॉलेट और गतिविधि यहाँ दिखाई जाती है।",
    },
}
for _code in SUPPORTED_LANGUAGES:
    I18N.setdefault(_code, dict(I18N["en"]))

_SETTINGS_LABELS = {
    "settings": "⚙️  Settings", "settings_title": "⚙️ <b>Settings</b>",
    "account_settings": "👤 Account", "security_settings": "🔐 Security",
    "notification_settings": "🔔 Notifications", "wallet_settings": "💰 Wallet",
    "shopping_settings": "🛒 Shopping", "referral_settings": "🔗 Referral",
    "support_settings": "🎧 Support & Help", "about_settings": "ℹ️ About & Policies",
    "reset_settings": "🔄 Reset Preferences", "theme_settings": "🎨 Theme Preference",
    "back_settings": "‹  Back to Settings",
}
for _code in SUPPORTED_LANGUAGES:
    I18N[_code].update(_SETTINGS_LABELS)

I18N["bn"].update({"shop":"🛍️ এখনই শপ করুন","profile":"👤 আমার প্রোফাইল","orders":"📄 আমার অর্ডার","wallet":"💰 ওয়ালেট","tutorial":"🎓 টিউটোরিয়াল","reseller":"🤝 রিসেলার","support":"🟢 সাপোর্ট","proof":"📊 সেলিং প্রুফ","referral":"🤝 রেফারেল","paid_store":"🏪 পেইড স্টোর","language":"🌐 ভাষা","back_home":"‹ প্রধান মেনু","choose_language":"🌐 <b>ভাষা নির্বাচন করুন</b>\n\nআপনার পছন্দের ভাষা বেছে নিন:","choose_category":"📦 <b>ক্যাটাগরি নির্বাচন করুন</b>\n\nযেখানে শপ করতে চান তা বেছে নিন:","select_product":"প্রোডাক্ট নির্বাচন করুন:","plan_select":"<b>প্ল্যান নির্বাচন করুন:</b>","days":"দিন","price":"মূল্য","reseller_price":"রিসেলার মূল্য","validity":"মেয়াদ","stock":"স্টক","use_wallet":"💰 ওয়ালেট ব্যালেন্স ব্যবহার করুন","apply_coupon":"🏷️ কুপন প্রয়োগ করুন","buy_upi":"💳 UPI দিয়ে কিনুন","reward":"প্রতি সফল রেফারেলের পুরস্কার","successful":"সফল রেফারেল","pending":"অপেক্ষমাণ রেফারেল","earned":"মোট আয়","your_link":"🔗 <b>আপনার রেফারেল লিংক</b>","share_referral":"📤 রেফারেল শেয়ার করুন","referral_program":"🤝 <b>রেফারেল প্রোগ্রাম</b>"})
I18N["mr"].update({"shop":"🛍️ आत्ता खरेदी करा","profile":"👤 माझे प्रोफाइल","orders":"📄 माझे ऑर्डर","wallet":"💰 वॉलेट","tutorial":"🎓 ट्युटोरियल","reseller":"🤝 रिसेलर","support":"🟢 सपोर्ट","proof":"📊 सेलिंग प्रूफ","referral":"🤝 रेफरल","paid_store":"🏪 पेड स्टोअर","language":"🌐 भाषा","back_home":"‹ मुख्य मेनू","choose_language":"🌐 <b>भाषा निवडा</b>\n\nतुमची पसंतीची भाषा निवडा:","choose_category":"📦 <b>कॅटेगरी निवडा</b>\n\nखरेदीसाठी कॅटेगरी निवडा:","select_product":"प्रॉडक्ट निवडा:","plan_select":"<b>प्लॅन निवडा:</b>","days":"दिवस","price":"किंमत","reseller_price":"रिसेलर किंमत","validity":"वैधता","stock":"स्टॉक","use_wallet":"💰 वॉलेट बॅलन्स वापरा","apply_coupon":"🏷️ कूपन लावा","buy_upi":"💳 UPI ने खरेदी करा","reward":"प्रत्येक यशस्वी रेफरलचे बक्षीस","successful":"यशस्वी रेफरल","pending":"प्रलंबित रेफरल","earned":"एकूण कमाई","your_link":"🔗 <b>तुमची रेफरल लिंक</b>","share_referral":"📤 रेफरल शेअर करा","referral_program":"🤝 <b>रेफरल प्रोग्राम</b>"})
I18N["ta"].update({"shop":"🛍️ இப்போது வாங்குங்கள்","profile":"👤 என் சுயவிவரம்","orders":"📄 என் ஆர்டர்கள்","wallet":"💰 வாலெட்","tutorial":"🎓 வழிகாட்டி","reseller":"🤝 மறுவிற்பனையாளர்","support":"🟢 ஆதரவு","proof":"📊 விற்பனை ஆதாரம்","referral":"🤝 பரிந்துரை","paid_store":"🏪 Paid Store","language":"🌐 மொழி","back_home":"‹ முதன்மை மெனு","choose_language":"🌐 <b>மொழியைத் தேர்ந்தெடுக்கவும்</b>\n\nஉங்களுக்கு விருப்பமான மொழியைத் தேர்ந்தெடுக்கவும்:","choose_category":"📦 <b>வகையைத் தேர்ந்தெடுக்கவும்</b>","select_product":"தயாரிப்பைத் தேர்ந்தெடுக்கவும்:","plan_select":"<b>திட்டத்தைத் தேர்ந்தெடுக்கவும்:</b>","days":"நாட்கள்","price":"விலை","reseller_price":"மறுவிற்பனையாளர் விலை","validity":"செல்லுபடியாகும் காலம்","stock":"ஸ்டாக்","use_wallet":"💰 வாலெட் இருப்பைப் பயன்படுத்தவும்","apply_coupon":"🏷️ கூப்பனைப் பயன்படுத்தவும்","buy_upi":"💳 UPI மூலம் வாங்கவும்","reward":"ஒவ்வொரு வெற்றிகரமான பரிந்துரைக்கான பரிசு","successful":"வெற்றிகரமான பரிந்துரைகள்","pending":"நிலுவை பரிந்துரைகள்","earned":"மொத்த வருமானம்","your_link":"🔗 <b>உங்கள் பரிந்துரை இணைப்பு</b>","share_referral":"📤 பகிரவும்","referral_program":"🤝 <b>பரிந்துரை திட்டம்</b>"})
I18N["te"].update({"shop":"🛍️ ఇప్పుడే కొనండి","profile":"👤 నా ప్రొఫైల్","orders":"📄 నా ఆర్డర్లు","wallet":"💰 వాలెట్","tutorial":"🎓 ట్యుటోరియల్","reseller":"🤝 రీసెల్లర్","support":"🟢 సపోర్ట్","proof":"📊 సెల్లింగ్ ప్రూఫ్","referral":"🤝 రిఫరల్","paid_store":"🏪 Paid Store","language":"🌐 భాష","back_home":"‹ ప్రధాన మెనూ","choose_language":"🌐 <b>భాషను ఎంచుకోండి</b>","choose_category":"📦 <b>కేటగిరీ ఎంచుకోండి</b>","select_product":"ప్రొడక్ట్ ఎంచుకోండి:","plan_select":"<b>ప్లాన్ ఎంచుకోండి:</b>","days":"రోజులు","price":"ధర","reseller_price":"రీ-సెల్లర్ ధర","validity":"చెల్లుబాటు","stock":"స్టాక్","use_wallet":"💰 వాలెట్ బ్యాలెన్స్ ఉపయోగించండి","apply_coupon":"🏷️ కూపన్ వర్తింపజేయండి","buy_upi":"💳 UPIతో కొనండి","reward":"ప్రతి విజయవంతమైన రిఫరల్ రివార్డ్","successful":"విజయవంతమైన రిఫరల్స్","pending":"పెండింగ్ రిఫరల్స్","earned":"మొత్తం సంపాదన","your_link":"🔗 <b>మీ రిఫరల్ లింక్</b>","share_referral":"📤 షేర్ చేయండి","referral_program":"🤝 <b>రిఫరల్ ప్రోగ్రామ్</b>"})
I18N["gu"].update({"shop":"🛍️ હમણાં ખરીદો","profile":"👤 મારી પ્રોફાઇલ","orders":"📄 મારા ઓર્ડર","wallet":"💰 વૉલેટ","tutorial":"🎓 ટ્યુટોરીયલ","reseller":"🤝 રીસેલર","support":"🟢 સપોર્ટ","proof":"📊 સેલિંગ પ્રૂફ","referral":"🤝 રેફરલ","paid_store":"🏪 Paid Store","language":"🌐 ભાષા","back_home":"‹ મુખ્ય મેનુ","choose_language":"🌐 <b>ભાષા પસંદ કરો</b>","choose_category":"📦 <b>કેટેગરી પસંદ કરો</b>","select_product":"પ્રોડક્ટ પસંદ કરો:","plan_select":"<b>પ્લાન પસંદ કરો:</b>","days":"દિવસ","price":"કિંમત","reseller_price":"રીસેલર કિંમત","validity":"માન્યતા","stock":"સ્ટોક","use_wallet":"💰 વૉલેટ બેલેન્સ વાપરો","apply_coupon":"🏷️ કૂપન લાગુ કરો","buy_upi":"💳 UPI થી ખરીદો","reward":"દર સફળ રેફરલનું ઇનામ","successful":"સફળ રેફરલ્સ","pending":"પેન્ડિંગ રેફરલ્સ","earned":"કુલ કમાણી","your_link":"🔗 <b>તમારી રેફરલ લિંક</b>","share_referral":"📤 શેર કરો","referral_program":"🤝 <b>રેફરલ પ્રોગ્રામ</b>"})
I18N["kn"].update({"shop":"🛍️ ಈಗ ಖರೀದಿಸಿ","profile":"👤 ನನ್ನ ಪ್ರೊಫೈಲ್","orders":"📄 ನನ್ನ ಆರ್ಡರ್‌ಗಳು","wallet":"💰 ವಾಲೆಟ್","tutorial":"🎓 ಟ್ಯುಟೋರಿಯಲ್","reseller":"🤝 ಮರುಮಾರಾಟಗಾರ","support":"🟢 ಸಹಾಯ","proof":"📊 ಮಾರಾಟದ ಪುರಾವೆ","referral":"🤝 ರೆಫರಲ್","paid_store":"🏪 Paid Store","language":"🌐 ಭಾಷೆ","back_home":"‹ ಮುಖ್ಯ ಮೆನು","choose_language":"🌐 <b>ಭಾಷೆ ಆಯ್ಕೆಮಾಡಿ</b>","choose_category":"📦 <b>ವರ್ಗವನ್ನು ಆಯ್ಕೆಮಾಡಿ</b>","select_product":"ಉತ್ಪನ್ನ ಆಯ್ಕೆಮಾಡಿ:","plan_select":"<b>ಪ್ಲಾನ್ ಆಯ್ಕೆಮಾಡಿ:</b>","days":"ದಿನಗಳು","price":"ಬೆಲೆ","reseller_price":"ಮರುಮಾರಾಟ ಬೆಲೆ","validity":"ಮಾನ್ಯತೆ","stock":"ಸ್ಟಾಕ್","use_wallet":"💰 ವಾಲೆಟ್ ಬ್ಯಾಲೆನ್ಸ್ ಬಳಸಿ","apply_coupon":"🏷️ ಕೂಪನ್ ಅನ್ವಯಿಸಿ","buy_upi":"💳 UPI ಮೂಲಕ ಖರೀದಿಸಿ","reward":"ಪ್ರತಿ ಯಶಸ್ವಿ ರೆಫರಲ್ ಬಹುಮಾನ","successful":"ಯಶಸ್ವಿ ರೆಫರಲ್‌ಗಳು","pending":"ಬಾಕಿ ರೆಫರಲ್‌ಗಳು","earned":"ಒಟ್ಟು ಗಳಿಕೆ","your_link":"🔗 <b>ನಿಮ್ಮ ರೆಫರಲ್ ಲಿಂಕ್</b>","share_referral":"📤 ಹಂಚಿಕೊಳ್ಳಿ","referral_program":"🤝 <b>ರೆಫರಲ್ ಪ್ರೋಗ್ರಾಂ</b>"})
I18N["ml"].update({"shop":"🛍️ ഇപ്പോൾ വാങ്ങുക","profile":"👤 എന്റെ പ്രൊഫൈൽ","orders":"📄 എന്റെ ഓർഡറുകൾ","wallet":"💰 വാലറ്റ്","tutorial":"🎓 ട്യൂട്ടോറിയൽ","reseller":"🤝 റീസെല്ലർ","support":"🟢 പിന്തുണ","proof":"📊 വിൽപ്പന തെളിവ്","referral":"🤝 റഫറൽ","paid_store":"🏪 Paid Store","language":"🌐 ഭാഷ","back_home":"‹ പ്രധാന മെനു","choose_language":"🌐 <b>ഭാഷ തിരഞ്ഞെടുക്കുക</b>","choose_category":"📦 <b>വിഭാഗം തിരഞ്ഞെടുക്കുക</b>","select_product":"ഉൽപ്പന്നം തിരഞ്ഞെടുക്കുക:","plan_select":"<b>പ്ലാൻ തിരഞ്ഞെടുക്കുക:</b>","days":"ദിവസം","price":"വില","reseller_price":"റീസെല്ലർ വില","validity":"കാലാവധി","stock":"സ്റ്റോക്ക്","use_wallet":"💰 വാലറ്റ് ബാലൻസ് ഉപയോഗിക്കുക","apply_coupon":"🏷️ കൂപ്പൺ ഉപയോഗിക്കുക","buy_upi":"💳 UPI വഴി വാങ്ങുക","reward":"ഓരോ വിജയകരമായ റഫറലിനുള്ള റിവാർഡ്","successful":"വിജയകരമായ റഫറലുകൾ","pending":"ബാക്കി റഫറലുകൾ","earned":"ആകെ വരുമാനം","your_link":"🔗 <b>നിങ്ങളുടെ റഫറൽ ലിങ്ക്</b>","share_referral":"📤 പങ്കിടുക","referral_program":"🤝 <b>റഫറൽ പ്രോഗ്രാം</b>"})
I18N["pa"].update({"shop":"🛍️ ਹੁਣੇ ਖਰੀਦੋ","profile":"👤 ਮੇਰੀ ਪ੍ਰੋਫਾਈਲ","orders":"📄 ਮੇਰੇ ਆਰਡਰ","wallet":"💰 ਵਾਲਿਟ","tutorial":"🎓 ਟਿਊਟੋਰਿਅਲ","reseller":"🤝 ਰੀਸੈਲਰ","support":"🟢 ਸਹਾਇਤਾ","proof":"📊 ਸੇਲਿੰਗ ਪ੍ਰੂਫ","referral":"🤝 ਰੈਫਰਲ","paid_store":"🏪 Paid Store","language":"🌐 ਭਾਸ਼ਾ","back_home":"‹ ਮੁੱਖ ਮੀਨੂ","choose_language":"🌐 <b>ਭਾਸ਼ਾ ਚੁਣੋ</b>","choose_category":"📦 <b>ਸ਼੍ਰੇਣੀ ਚੁਣੋ</b>","select_product":"ਪ੍ਰੋਡਕਟ ਚੁਣੋ:","plan_select":"<b>ਪਲਾਨ ਚੁਣੋ:</b>","days":"ਦਿਨ","price":"ਕੀਮਤ","reseller_price":"ਰੀਸੈਲਰ ਕੀਮਤ","validity":"ਮਿਆਦ","stock":"ਸਟਾਕ","use_wallet":"💰 ਵਾਲਿਟ ਬੈਲੈਂਸ ਵਰਤੋ","apply_coupon":"🏷️ ਕੂਪਨ ਲਗਾਓ","buy_upi":"💳 UPI ਨਾਲ ਖਰੀਦੋ","reward":"ਹਰ ਸਫਲ ਰੈਫਰਲ ਦਾ ਇਨਾਮ","successful":"ਸਫਲ ਰੈਫਰਲ","pending":"ਬਕਾਇਆ ਰੈਫਰਲ","earned":"ਕੁੱਲ ਕਮਾਈ","your_link":"🔗 <b>ਤੁਹਾਡਾ ਰੈਫਰਲ ਲਿੰਕ</b>","share_referral":"📤 ਸਾਂਝਾ ਕਰੋ","referral_program":"🤝 <b>ਰੈਫਰਲ ਪ੍ਰੋਗਰਾਮ</b>"})
I18N["or"].update({"shop":"🛍️ ବର୍ତ୍ତମାନ କିଣନ୍ତୁ","profile":"👤 ମୋ ପ୍ରୋଫାଇଲ୍","orders":"📄 ମୋ ଅର୍ଡର୍","wallet":"💰 ୱାଲେଟ୍","tutorial":"🎓 ଟ୍ୟୁଟୋରିଆଲ୍","reseller":"🤝 ରିସେଲର୍","support":"🟢 ସହାୟତା","proof":"📊 ବିକ୍ରୟ ପ୍ରମାଣ","referral":"🤝 ରେଫରାଲ୍","paid_store":"🏪 Paid Store","language":"🌐 ଭାଷା","back_home":"‹ ମୁଖ୍ୟ ମେନୁ","choose_language":"🌐 <b>ଭାଷା ବାଛନ୍ତୁ</b>","choose_category":"📦 <b>ଶ୍ରେଣୀ ବାଛନ୍ତୁ</b>","select_product":"ପ୍ରଡକ୍ଟ ବାଛନ୍ତୁ:","plan_select":"<b>ପ୍ଲାନ୍ ବାଛନ୍ତୁ:</b>","days":"ଦିନ","price":"ମୂଲ୍ୟ","reseller_price":"ରିସେଲର୍ ମୂଲ୍ୟ","validity":"ବୈଧତା","stock":"ଷ୍ଟକ୍","use_wallet":"💰 ୱାଲେଟ୍ ବ୍ୟାଲାନ୍ସ ବ୍ୟବହାର କରନ୍ତୁ","apply_coupon":"🏷️ କୁପନ୍ ବ୍ୟବହାର କରନ୍ତୁ","buy_upi":"💳 UPI ଦ୍ୱାରା କିଣନ୍ତୁ","reward":"ପ୍ରତ୍ୟେକ ସଫଳ ରେଫରାଲ୍ ପୁରସ୍କାର","successful":"ସଫଳ ରେଫରାଲ୍","pending":"ବକେୟା ରେଫରାଲ୍","earned":"ମୋଟ ଆୟ","your_link":"🔗 <b>ଆପଣଙ୍କ ରେଫରାଲ୍ ଲିଙ୍କ</b>","share_referral":"📤 ସେୟାର୍ କରନ୍ତୁ","referral_program":"🤝 <b>ରେଫରାଲ୍ ପ୍ରୋଗ୍ରାମ୍</b>"})
I18N["ur"].update({"shop":"🛍️ ابھی خریدیں","profile":"👤 میری پروفائل","orders":"📄 میرے آرڈرز","wallet":"💰 والیٹ","tutorial":"🎓 ٹیوٹوریل","reseller":"🤝 ری سیلر","support":"🟢 سپورٹ","proof":"📊 سیلنگ پروف","referral":"🤝 ریفرل","paid_store":"🏪 Paid Store","language":"🌐 زبان","back_home":"‹ مین مینو","choose_language":"🌐 <b>زبان منتخب کریں</b>","choose_category":"📦 <b>کیٹیگری منتخب کریں</b>","select_product":"پروڈکٹ منتخب کریں:","plan_select":"<b>پلان منتخب کریں:</b>","days":"دن","price":"قیمت","reseller_price":"ری سیلر قیمت","validity":"مدت","stock":"اسٹاک","use_wallet":"💰 والیٹ بیلنس استعمال کریں","apply_coupon":"🏷️ کوپن لگائیں","buy_upi":"💳 UPI سے خریدیں","reward":"ہر کامیاب ریفرل کا انعام","successful":"کامیاب ریفرلز","pending":"زیر التوا ریفرلز","earned":"کل کمائی","your_link":"🔗 <b>آپ کا ریفرل لنک</b>","share_referral":"📤 شیئر کریں","referral_program":"🤝 <b>ریفرل پروگرام</b>"})
I18N["as"].update({"shop":"🛍️ এতিয়া কিনক","profile":"👤 মোৰ প্ৰফাইল","orders":"📄 মোৰ অৰ্ডাৰ","wallet":"💰 ৱালেট","tutorial":"🎓 টিউটোৰিয়েল","reseller":"🤝 ৰিচেলাৰ","support":"🟢 সহায়তা","proof":"📊 বিক্ৰীৰ প্ৰমাণ","referral":"🤝 ৰেফাৰেল","paid_store":"🏪 Paid Store","language":"🌐 ভাষা","back_home":"‹ মুখ্য মেনু","choose_language":"🌐 <b>ভাষা বাছনি কৰক</b>","choose_category":"📦 <b>শ্ৰেণী বাছনি কৰক</b>","select_product":"প্ৰডাক্ট বাছনি কৰক:","plan_select":"<b>প্লেন বাছনি কৰক:</b>","days":"দিন","price":"মূল্য","reseller_price":"ৰিচেলাৰ মূল্য","validity":"ম্যাদ","stock":"ষ্টক","use_wallet":"💰 ৱালেট বেলেন্স ব্যৱহাৰ কৰক","apply_coupon":"🏷️ কুপন প্ৰয়োগ কৰক","buy_upi":"💳 UPI-ৰে কিনক","reward":"প্ৰতিটো সফল ৰেফাৰেলৰ পুৰস্কাৰ","successful":"সফল ৰেফাৰেল","pending":"অপেক্ষমাণ ৰেফাৰেল","earned":"মুঠ উপাৰ্জন","your_link":"🔗 <b>আপোনাৰ ৰেফাৰেল লিংক</b>","share_referral":"📤 শ্বেয়াৰ কৰক","referral_program":"🤝 <b>ৰেফাৰেল প্ৰগ্ৰাম</b>"})

# Localized labels for the compact main-menu layout.
_MORE_LABELS = {
    "en": ("✨  More", "✨ <b>More Options</b>"), "hi": ("✨  और विकल्प", "✨ <b>और विकल्प</b>"),
    "bn": ("✨  আরও", "✨ <b>আরও অপশন</b>"), "te": ("✨  మరిన్ని", "✨ <b>మరిన్ని ఎంపికలు</b>"),
    "mr": ("✨  आणखी", "✨ <b>आणखी पर्याय</b>"), "ta": ("✨  மேலும்", "✨ <b>மேலும் விருப்பங்கள்</b>"),
    "gu": ("✨  વધુ", "✨ <b>વધુ વિકલ્પો</b>"), "kn": ("✨  ಇನ್ನಷ್ಟು", "✨ <b>ಇನ್ನಷ್ಟು ಆಯ್ಕೆಗಳು</b>"),
    "ml": ("✨  കൂടുതൽ", "✨ <b>കൂടുതൽ ഓപ്ഷനുകൾ</b>"), "pa": ("✨  ਹੋਰ", "✨ <b>ਹੋਰ ਵਿਕਲਪ</b>"),
    "or": ("✨  ଅଧିକ", "✨ <b>ଅଧିକ ବିକଳ୍ପ</b>"), "ur": ("✨  مزید", "✨ <b>مزید اختیارات</b>"),
    "as": ("✨  অধিক", "✨ <b>অধিক বিকল্প</b>"),
}
for _code, (_more, _more_title) in _MORE_LABELS.items():
    I18N[_code]["more"] = _more
    I18N[_code]["more_menu"] = _more_title


_PROFILE_LABELS = {
    "bn": {"profile_title":"👤 <b>আমার প্রোফাইল</b>","joined":"যোগদানের তারিখ","completed_orders_label":"সম্পন্ন অর্ডার","profile_role":"ভূমিকা","profile_account":"অ্যাকাউন্ট","profile_balance":"ব্যালেন্স"},
    "mr": {"profile_title":"👤 <b>माझे प्रोफाइल</b>","joined":"सामील तारीख","completed_orders_label":"पूर्ण ऑर्डर","profile_role":"भूमिका","profile_account":"खाते","profile_balance":"शिल्लक","profile_overview":"खाते का आढावा","profile_overview_text":"तुमचे प्रोफाइल, वॉलेट आणि गतिविधी येथे दिसतात."},
    "ta": {"profile_title":"👤 <b>என் சுயவிவரம்</b>","joined":"சேர்ந்த தேதி","completed_orders_label":"முடிக்கப்பட்ட ஆர்டர்கள்","profile_role":"பங்கு","profile_account":"கணக்கு","profile_balance":"இருப்பு"},
    "te": {"profile_title":"👤 <b>నా ప్రొఫైల్</b>","joined":"చేరిన తేదీ","completed_orders_label":"పూర్తయిన ఆర్డర్లు","profile_role":"పాత్ర","profile_account":"ఖాతా","profile_balance":"బ్యాలెన్స్"},
    "gu": {"profile_title":"👤 <b>મારી પ્રોફાઇલ</b>","joined":"જોડાયા તારીખ","completed_orders_label":"પૂર્ણ ઓર્ડર","profile_role":"ભૂમિકા","profile_account":"એકાઉન્ટ","profile_balance":"બેલેન્સ","profile_overview":"એકાઉન્ટ ઝલક","profile_overview_text":"તમારી પ્રોફાઇલ, વૉલેટ અને પ્રવૃત્તિ અહીં દેખાશે."},
    "kn": {"profile_title":"👤 <b>ನನ್ನ ಪ್ರೊಫೈಲ್</b>","joined":"ಸೇರಿದ ದಿನಾಂಕ","completed_orders_label":"ಪೂರ್ಣಗೊಂಡ ಆರ್ಡರ್‌ಗಳು","profile_role":"ಪಾತ್ರ","profile_account":"ಖಾತೆ","profile_balance":"ಬ್ಯಾಲೆನ್ಸ್","profile_overview":"ಖಾತೆ ಸಾರಾಂಶ","profile_overview_text":"ನಿಮ್ಮ ಪ್ರೊಫೈಲ್, ವಾಲೆಟ್ ಮತ್ತು ಚಟುವಟಿಕೆ ಇಲ್ಲಿ ತೋರಿಸಲಾಗುತ್ತದೆ."},
    "ml": {"profile_title":"👤 <b>എന്റെ പ്രൊഫൈൽ</b>","joined":"ചേർന്ന തീയതി","completed_orders_label":"പൂർത്തിയായ ഓർഡറുകൾ","profile_role":"പങ്ക്","profile_account":"അക്കൗണ്ട്","profile_balance":"ബാലൻസ്","profile_overview":"അക്കൗണ്ട് അവലോകനം","profile_overview_text":"നിങ്ങളുടെ പ്രൊഫൈൽ, വാലറ്റ്, പ്രവർത്തനം ഇവിടെ കാണാം."},
    "pa": {"profile_title":"👤 <b>ਮੇਰੀ ਪ੍ਰੋਫਾਈਲ</b>","joined":"ਜੁੜਨ ਦੀ ਤਾਰੀਖ","completed_orders_label":"ਪੂਰੇ ਆਰਡਰ","profile_role":"ਭੂਮਿਕਾ","profile_account":"ਖਾਤਾ","profile_balance":"ਬਕਾਇਆ"},
    "or": {"profile_title":"👤 <b>ମୋ ପ୍ରୋଫାଇଲ୍</b>","joined":"ଯୋଗ ତାରିଖ","completed_orders_label":"ସମ୍ପୂର୍ଣ୍ଣ ଅର୍ଡର","profile_role":"ଭୂମିକା","profile_account":"ଆକାଉଣ୍ଟ","profile_balance":"ବ୍ୟାଲାନ୍ସ","profile_overview":"ଆକାଉଣ୍ଟ ସାରାଂଶ","profile_overview_text":"ଆପଣଙ୍କ ପ୍ରୋଫାଇଲ୍, ୱାଲେଟ୍ ଏବଂ କାର୍ଯ୍ୟକଳାପ ଏଠାରେ ଦେଖାଯାଏ."},
    "ur": {"profile_title":"👤 <b>میری پروفائل</b>","joined":"شامل ہونے کی تاریخ","completed_orders_label":"مکمل آرڈرز","profile_role":"کردار","profile_account":"اکاؤنٹ","profile_balance":"بیلنس","profile_overview":"اکاؤنٹ کا جائزہ","profile_overview_text":"آپ کی پروفائل، والیٹ اور سرگرمی یہاں دکھائی جاتی ہے."},
    "as": {"profile_title":"👤 <b>মোৰ প্ৰফাইল</b>","joined":"যোগদানৰ তাৰিখ","completed_orders_label":"সম্পূৰ্ণ অৰ্ডাৰ","profile_role":"ভূমিকা","profile_account":"একাউণ্ট","profile_balance":"বেলেঞ্চ","profile_overview":"একাউণ্টৰ সাৰাংশ","profile_overview_text":"আপোনাৰ প্ৰফাইল, ৱালেট আৰু কাৰ্যকলাপ ইয়াত দেখুওৱা হয়."},
}
for _code, _labels in _PROFILE_LABELS.items():
    I18N[_code].update(_labels)

def user_language(user_id: int | None) -> str:
    if not user_id:
        return "en"
    try:
        with db() as connection:
            row = connection.execute("SELECT language FROM users WHERE id=?", (int(user_id),)).fetchone()
        code = str(row["language"] if row and row["language"] else "en").lower()
        return code if code in SUPPORTED_LANGUAGES else "en"
    except Exception:
        return "en"


def tr(user_id: int | None, key: str) -> str:
    lang = user_language(user_id)
    return I18N.get(lang, I18N["en"]).get(key, I18N["en"].get(key, key))


def localized_json(raw: str | None, lang: str) -> str | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        value = data.get(lang) or data.get("en")
        return str(value) if value else None
    except (TypeError, ValueError, AttributeError):
        return None


def localized_text(row: sqlite3.Row, field: str, lang: str) -> str:
    raw = row[field] if field in row.keys() else ""
    i18n_field = f"{field}_i18n"
    i18n_raw = row[i18n_field] if i18n_field in row.keys() else ""
    return localized_json(i18n_raw, lang) or str(raw or "")


# ---------------------------------------------------------------------------
# Configuration and persistence
# ---------------------------------------------------------------------------

BOT_VERSION = "SHIVAM STORE BOT 3.0.13-CUSTOMER-ONLY-PREMIUM"
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "shivam_store.sqlite3"
TIMEZONE = timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()


def load_dotenv() -> None:
    """Small .env loader so Termux only needs python-telegram-bot."""
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip("\"'")
        os.environ.setdefault(key, value)


load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "shivam_store.sqlite3")))


def resolve_timezone(name: str) -> timezone | ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        # Minimal Termux installs may not ship the system tzdata package.
        # Keep the default India timezone usable without crashing at import.
        if name == "Asia/Kolkata":
            logging.warning("tzdata is missing; using fixed Asia/Kolkata offset")
            return timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")
        logging.warning("Timezone %s is unavailable; using UTC", name)
        return timezone.utc


TIMEZONE = resolve_timezone(os.getenv("STORE_TIMEZONE", "Asia/Kolkata"))
ADMIN_USER_IDS = {
    int(item.strip())
    for item in os.getenv("ADMIN_USER_ID", "").split(",")
    if item.strip().lstrip("-").isdigit()
}
# Exactly one owner: the first valid ID in ADMIN_USER_ID wins.
_owner_ids = [int(item.strip()) for item in os.getenv("ADMIN_USER_ID", "").split(",") if item.strip().lstrip("-").isdigit()]
OWNER_USER_ID = _owner_ids[0] if _owner_ids else None

# Automatic Gmail/IMAP payment verification settings. Secrets are read only from .env.
IMAP_ENABLED = os.getenv("IMAP_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}
IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com").strip()
IMAP_PORT = int(os.getenv("IMAP_PORT", "993") or "993")
IMAP_USERNAME = os.getenv("IMAP_USERNAME", "").strip()
IMAP_APP_PASSWORD = re.sub(r"[\s-]+", "", os.getenv("IMAP_APP_PASSWORD", "").strip())
IMAP_FOLDER = os.getenv("IMAP_FOLDER", "INBOX").strip() or "INBOX"
IMAP_POLL_SECONDS = max(10, int(os.getenv("IMAP_POLL_SECONDS", "15") or "15"))
IMAP_LOOKBACK_MINUTES = max(5, int(os.getenv("IMAP_LOOKBACK_MINUTES", "30") or "30"))
IMAP_ALLOWED_SENDERS = {x.strip().lower() for x in os.getenv("IMAP_ALLOWED_SENDERS", "").split(",") if x.strip()}
IMAP_REQUIRE_TRUSTED_SENDER = os.getenv("IMAP_REQUIRE_TRUSTED_SENDER", "1") == "1"
IMAP_REQUIRE_RECIPIENT_MATCH = os.getenv("IMAP_REQUIRE_RECIPIENT_MATCH", "1").strip().lower() in {"1", "true", "yes", "on"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat(timespec="seconds")


def expire_stale_orders() -> None:
    cutoff = (utc_now() - timedelta(minutes=20)).isoformat()
    with db() as connection:
        connection.execute(
            "UPDATE orders SET status = 'expired', delivery_status = 'not_required' "
            "WHERE status IN ('awaiting_utr','pending') AND COALESCE(expiry_at, created_at) < ?",
            (iso_now(),),
        )
        connection.commit()


def display_date(value: str | None) -> str:
    if not value:
        return "—"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(TIMEZONE).strftime("%d %b %Y, %I:%M %p")
    except ValueError:
        return value


def decimal_amount(value: Any) -> Decimal:
    """Parse monetary values without binary floating-point arithmetic."""
    try:
        if isinstance(value, Decimal):
            amount = value
        else:
            amount = Decimal(str(value if value is not None else "0").replace(",", "").strip() or "0")
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")


def money(value: float | int | str | Decimal | None) -> str:
    amount = decimal_amount(value)
    return f"₹{amount:,.2f}".replace(".00", "")


def safe(value: Any) -> str:
    """Escape every dynamic value before inserting it into Telegram HTML."""
    return escape("" if value is None else str(value), quote=False)


def parse_amount(value: str, *, minimum: float = 0, maximum: float = 500_000) -> float | None:
    amount = decimal_amount(value)
    low = decimal_amount(minimum)
    high = decimal_amount(maximum)
    if amount.is_nan() or amount < low or amount > high:
        return None
    # SQLite schema remains REAL for backward compatibility; arithmetic is Decimal.
    return float(amount)


def valid_url(value: str) -> bool:
    return bool(re.fullmatch(r"https?://[^\s<>]+", value.strip(), re.IGNORECASE))


def valid_upi_id(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9._-]{2,100}@[A-Za-z0-9.-]{2,50}", value.strip()))


def _qr_matrix_to_png(matrix: list[list[bool]], scale: int = 8, border: int = 4) -> bytes:
    """Render a QR matrix to PNG using only Python stdlib (no Pillow/libjpeg)."""
    size = len(matrix)
    total = (size + border * 2) * scale
    raw = bytearray()
    width = size + border * 2
    for y in range(total):
        raw.append(0)  # PNG filter byte
        module_y = y // scale - border
        for x in range(total):
            module_x = x // scale - border
            dark = 0 <= module_x < size and 0 <= module_y < size and matrix[module_y][module_x]
            value = 0 if dark else 255
            raw.extend((value, value, value))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data +
                struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    png = bytearray(b"\x89PNG\r\n\x1a\n")
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", total, total, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    return bytes(png)


def generate_upi_qr(upi_id: str, amount: float, order_no: str) -> BytesIO | None:
    """Create an exact-amount UPI QR without Pillow, JPEG libraries, or native builds."""
    upi_id = upi_id.strip()
    if not valid_upi_id(upi_id):
        return None
    try:
        import qrcode
        payload = "upi://pay?" + urlencode({
            "pa": upi_id,
            "pn": setting("store_name", "SHIVAM STORE"),
            "am": f"{float(amount):.2f}",
            "cu": "INR",
            "tn": order_no,
        })
        qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=1, border=0)
        qr.add_data(payload)
        qr.make(fit=True)
        png = _qr_matrix_to_png(qr.get_matrix(), scale=8, border=4)
        buffer = BytesIO(png)
        buffer.seek(0)
        buffer.name = f"{order_no}.png"
        return buffer
    except Exception:
        logging.exception("Could not generate UPI QR for %s", order_no)
        return None


async def delete_incoming(update: Update) -> None:
    """Best-effort cleanup for passwords, UTRs and admin form input."""
    message = update.effective_message
    if message:
        try:
            await message.delete()
        except Exception:
            logging.debug("Could not delete incoming message", exc_info=True)


async def safe_query_answer(update: Update) -> None:
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            logging.debug("Callback query was already answered", exc_info=True)


@contextmanager
def db():
    """Open a SQLite connection and always close it after the with-block.

    sqlite3.Connection's own context manager commits/rolls back but does not
    close the connection; wrapping it here prevents connection leaks.
    """
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        yield connection
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def audit(actor_user_id: int, action: str, entity_type: str = "", entity_id: int | None = None, details: str = "") -> None:
    try:
        with db() as connection:
            connection.execute(
                "INSERT INTO audit_logs(actor_user_id, action, entity_type, entity_id, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (actor_user_id, action, entity_type, entity_id, details[:1000], iso_now()),
            )
            connection.commit()
    except Exception:
        logging.debug("Audit log failed", exc_info=True)


def add_risk_flag(user_id: int, risk_type: str, details: str = "", order_id: int | None = None) -> None:
    with db() as connection:
        connection.execute(
            "INSERT INTO risk_flags(user_id, order_id, risk_type, details, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, order_id, risk_type[:80], details[:1000], iso_now()),
        )
        connection.commit()


def ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {
        row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in existing:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with db() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL DEFAULT '',
                first_name TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                phone_verified INTEGER NOT NULL DEFAULT 0,
                balance REAL NOT NULL DEFAULT 0,
                is_reseller INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                channel_link TEXT NOT NULL DEFAULT '',
                maintenance_mode INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY(category_id) REFERENCES categories(id)
            );
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                days INTEGER NOT NULL,
                customer_price REAL NOT NULL,
                reseller_price REAL NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(product_id) REFERENCES products(id)
            );
            CREATE TABLE IF NOT EXISTS stock_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                key_value TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'available',
                assigned_order_id INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY(plan_id) REFERENCES plans(id)
            );
            CREATE TABLE IF NOT EXISTS coupons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                discount_type TEXT NOT NULL,
                discount_value REAL NOT NULL,
                max_uses INTEGER NOT NULL DEFAULT 0,
                used_count INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                expires_at TEXT
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_no TEXT NOT NULL UNIQUE,
                user_id INTEGER NOT NULL,
                plan_id INTEGER,
                order_type TEXT NOT NULL DEFAULT 'product',
                amount REAL NOT NULL,
                original_amount REAL NOT NULL,
                topup_amount REAL NOT NULL DEFAULT 0,
                coupon_code TEXT NOT NULL DEFAULT '',
                utr TEXT NOT NULL DEFAULT '',
                payment_method TEXT NOT NULL DEFAULT 'gateway',
                status TEXT NOT NULL DEFAULT 'awaiting_utr',
                created_at TEXT NOT NULL,
                approved_at TEXT,
                rejected_at TEXT,
                expiry_at TEXT,
                key_id INTEGER,
                delivery_status TEXT NOT NULL DEFAULT 'not_required',
                delivery_attempts INTEGER NOT NULL DEFAULT 0,
                delivery_error TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(plan_id) REFERENCES plans(id)
            );
            CREATE TABLE IF NOT EXISTS wallet_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                order_id INTEGER,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                balance_before REAL NOT NULL,
                balance_after REAL NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(order_id) REFERENCES orders(id)
            );
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL DEFAULT '',
                entity_id INTEGER,
                details TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS scheduled_broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                run_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'scheduled',
                created_at TEXT NOT NULL,
                processing_at TEXT,
                sent_count INTEGER NOT NULL DEFAULT 0,
                error_count INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS payment_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                provider_event_id TEXT NOT NULL,
                order_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                received_at TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '',
                UNIQUE(provider, provider_event_id),
                FOREIGN KEY(order_id) REFERENCES orders(id)
            );
            CREATE TABLE IF NOT EXISTS risk_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                order_id INTEGER,
                risk_type TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_user_id INTEGER NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'pending',
                qualified_order_id INTEGER,
                reward_amount REAL NOT NULL DEFAULT 0,
                rewarded_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(referrer_id) REFERENCES users(id),
                FOREIGN KEY(referred_user_id) REFERENCES users(id),
                FOREIGN KEY(qualified_order_id) REFERENCES orders(id)
            );
            CREATE INDEX IF NOT EXISTS referrals_referrer_status_idx
                ON referrals(referrer_id, status, created_at);
            CREATE INDEX IF NOT EXISTS risk_flags_status_idx ON risk_flags(status, created_at);
            CREATE INDEX IF NOT EXISTS scheduled_broadcast_status_idx ON scheduled_broadcasts(status, run_at);
            CREATE UNIQUE INDEX IF NOT EXISTS unique_nonempty_utr
                ON orders(utr) WHERE utr != '';
            CREATE UNIQUE INDEX IF NOT EXISTS unique_plan_key
                ON stock_keys(plan_id, key_value);
            CREATE UNIQUE INDEX IF NOT EXISTS unique_assigned_stock_order
                ON stock_keys(assigned_order_id) WHERE assigned_order_id IS NOT NULL;
            CREATE INDEX IF NOT EXISTS orders_user_status_idx
                ON orders(user_id, status, created_at);
            CREATE INDEX IF NOT EXISTS orders_status_idx
                ON orders(status, order_type, created_at);
            CREATE INDEX IF NOT EXISTS stock_plan_status_idx
                ON stock_keys(plan_id, status, id);
            """
        )
        # Migrate databases created by the original ZIP without deleting data.
        ensure_column(connection, "users", "language", "TEXT NOT NULL DEFAULT 'en'")
        ensure_column(connection, "users", "phone", "TEXT NOT NULL DEFAULT ''")
        ensure_column(connection, "users", "phone_verified", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(connection, "users", "bot_password_hash", "TEXT NOT NULL DEFAULT ''")
        ensure_column(connection, "users", "bot_password_salt", "TEXT NOT NULL DEFAULT ''")
        ensure_column(connection, "users", "password_remember_until", "TEXT NOT NULL DEFAULT ''")
        ensure_column(connection, "users", "password_remember_minutes", "INTEGER NOT NULL DEFAULT 60")
        ensure_column(connection, "users", "password_lock_enabled", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(connection, "users", "theme_preference", "TEXT NOT NULL DEFAULT 'default'")
        ensure_column(connection, "users", "notifications_enabled", "INTEGER NOT NULL DEFAULT 1")
        ensure_column(connection, "users", "payment_notifications", "INTEGER NOT NULL DEFAULT 1")
        ensure_column(connection, "users", "order_notifications", "INTEGER NOT NULL DEFAULT 1")
        ensure_column(connection, "users", "referral_notifications", "INTEGER NOT NULL DEFAULT 1")
        ensure_column(connection, "users", "wallet_notifications", "INTEGER NOT NULL DEFAULT 1")
        ensure_column(connection, "users", "announcement_notifications", "INTEGER NOT NULL DEFAULT 1")
        ensure_column(connection, "categories", "description", "TEXT NOT NULL DEFAULT ''")
        ensure_column(connection, "categories", "name_i18n", "TEXT NOT NULL DEFAULT '{}'")
        ensure_column(connection, "categories", "description_i18n", "TEXT NOT NULL DEFAULT '{}'")
        ensure_column(connection, "products", "channel_link", "TEXT NOT NULL DEFAULT ''")
        ensure_column(connection, "products", "name_i18n", "TEXT NOT NULL DEFAULT '{}'")
        ensure_column(connection, "products", "description_i18n", "TEXT NOT NULL DEFAULT '{}'")
        ensure_column(connection, "products", "maintenance_mode", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(connection, "plans", "description", "TEXT NOT NULL DEFAULT ''")
        ensure_column(connection, "plans", "name_i18n", "TEXT NOT NULL DEFAULT '{}'")
        ensure_column(connection, "plans", "description_i18n", "TEXT NOT NULL DEFAULT '{}'")
        ensure_column(connection, "orders", "payment_method", "TEXT NOT NULL DEFAULT 'gateway'")
        ensure_column(connection, "orders", "rejected_at", "TEXT")
        ensure_column(connection, "orders", "delivery_status", "TEXT NOT NULL DEFAULT 'not_required'")
        ensure_column(connection, "orders", "delivery_attempts", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(connection, "orders", "delivery_error", "TEXT NOT NULL DEFAULT ''")
        ensure_column(connection, "orders", "pending_message_chat_id", "INTEGER")
        ensure_column(connection, "orders", "pending_message_id", "INTEGER")
        ensure_column(connection, "scheduled_broadcasts", "processing_at", "TEXT")
        defaults = {
            "store_name": "SHIVAM STORE",
            "store_tagline": "Premium digital products • Fast delivery • Trusted support",
            "payment_gateway_url": os.getenv("PAYMENT_GATEWAY_URL", "https://gatewaybliss.co/payment_api.php"),
            "payment_gateway_api_key": os.getenv("PAYMENT_GATEWAY_API_KEY", ""),
            "payment_gateway_enabled": os.getenv("PAYMENT_GATEWAY_ENABLED", "0"),
            "reseller_join_fee": "499",
            "support_url": "",
            "tutorial_url": "",
            "selling_proof_url": "",
            "paid_store_url": "",
            "maintenance_mode": "0",
            "low_stock_threshold": "5",
            "store_announcement": "",
            "auto_payment_last_run": "",
            "referral_reward": "20",
            "referral_share_text": "SHIVAM STORE par join karein aur digital products dekhein.",
        }
        for key, value in defaults.items():
            connection.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
                (key, value),
            )
        # Remove legacy security/payment settings that are no longer supported.
        connection.execute("DELETE FROM settings WHERE key IN ('qr_file_id', 'admin_password_hash')")
        for user_id in ADMIN_USER_IDS:
            connection.execute(
                "INSERT OR IGNORE INTO admins(user_id, active, created_at) VALUES (?, 1, ?)",
                (user_id, iso_now()),
            )
        connection.commit()


def setting(key: str, default: str = "") -> str:
    with db() as connection:
        row = connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return str(row["value"]) if row else default


def set_setting(key: str, value: str) -> None:
    with db() as connection:
        connection.execute(
            "INSERT INTO settings(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        connection.commit()


def _hash_user_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210_000)
    return salt.hex(), digest.hex()


def _verify_user_password(password: str, salt_hex: str, digest_hex: str) -> bool:
    if not password or not salt_hex or not digest_hex:
        return False
    try:
        _, candidate = _hash_user_password(password, salt_hex)
        return secrets.compare_digest(candidate, digest_hex)
    except (ValueError, TypeError):
        return False


def user_password_lock_active(user_id: int) -> bool:
    with db() as connection:
        row = connection.execute("SELECT password_lock_enabled, bot_password_hash, password_remember_until FROM users WHERE id=?", (int(user_id),)).fetchone()
    if not row or not row["password_lock_enabled"] or not row["bot_password_hash"]:
        return False
    until = str(row["password_remember_until"] or "")
    if until:
        try:
            if datetime.fromisoformat(until.replace("Z", "+00:00")) > utc_now():
                return False
        except ValueError:
            pass
    return True


def user_password_is_configured(user_id: int) -> bool:
    with db() as connection:
        row = connection.execute("SELECT bot_password_hash FROM users WHERE id=?", (int(user_id),)).fetchone()
    return bool(row and row["bot_password_hash"])


def set_user_password(user_id: int, password: str) -> None:
    salt, digest = _hash_user_password(password)
    with db() as connection:
        connection.execute("UPDATE users SET bot_password_hash=?, bot_password_salt=?, password_lock_enabled=1, password_remember_until='', updated_at=? WHERE id=?", (digest, salt, iso_now(), int(user_id)))
        connection.commit()


def disable_user_password(user_id: int) -> None:
    with db() as connection:
        connection.execute("UPDATE users SET bot_password_hash='', bot_password_salt='', password_lock_enabled=0, password_remember_until='', updated_at=? WHERE id=?", (iso_now(), int(user_id)))
        connection.commit()


def lock_user_now(user_id: int) -> None:
    with db() as connection:
        connection.execute("UPDATE users SET password_lock_enabled=CASE WHEN bot_password_hash != '' THEN 1 ELSE 0 END, password_remember_until='', updated_at=? WHERE id=?", (iso_now(), int(user_id)))
        connection.commit()


def set_password_remember(user_id: int, minutes: int) -> None:
    until = (utc_now() + timedelta(minutes=max(0, int(minutes)))).isoformat() if minutes > 0 else ""
    with db() as connection:
        connection.execute("UPDATE users SET password_remember_until=?, updated_at=? WHERE id=?", (until, iso_now(), int(user_id)))
        connection.commit()


def user_password_record(user_id: int):
    with db() as connection:
        return connection.execute("SELECT bot_password_hash, bot_password_salt, password_lock_enabled FROM users WHERE id=?", (int(user_id),)).fetchone()


def notifications_enabled(user_id: int) -> bool:
    with db() as connection:
        row = connection.execute("SELECT notifications_enabled FROM users WHERE id=?", (int(user_id),)).fetchone()
    return bool(row["notifications_enabled"]) if row else True


def theme_preference(user_id: int) -> str:
    with db() as connection:
        row = connection.execute("SELECT theme_preference FROM users WHERE id=?", (int(user_id),)).fetchone()
    return str(row["theme_preference"] or "default") if row else "default"


def upsert_user(user: Any) -> None:
    now = iso_now()
    with db() as connection:
        connection.execute(
            """
            INSERT INTO users(id, username, first_name, language, created_at, updated_at)
            VALUES (?, ?, ?, 'en', ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                updated_at = excluded.updated_at
            """,
            (
                user.id,
                user.username or "",
                user.first_name or "",
                now,
                now,
            ),
        )
        connection.commit()


def is_admin(user_id: int) -> bool:
    """Only the configured owner can ever access admin functionality."""
    return OWNER_USER_ID is not None and int(user_id) == int(OWNER_USER_ID)


def user_is_verified(user_id: int) -> bool:
    with db() as connection:
        row = connection.execute(
            "SELECT phone_verified FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return bool(row and row["phone_verified"])


def referral_reward_amount() -> Decimal:
    try:
        value = Decimal(str(setting("referral_reward", "20")))
        if not value.is_finite() or value < 0 or value > Decimal("500000"):
            return Decimal("0.00")
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def referral_code_for(user_id: int) -> str:
    return f"ref_{int(user_id)}"


def register_referral(referrer_id: int, referred_user_id: int) -> bool:
    referrer_id, referred_user_id = int(referrer_id), int(referred_user_id)
    if referrer_id <= 0 or referred_user_id <= 0 or referrer_id == referred_user_id:
        return False
    with db() as connection:
        referrer = connection.execute("SELECT id, active FROM users WHERE id=?", (referrer_id,)).fetchone()
        referred = connection.execute("SELECT id FROM users WHERE id=?", (referred_user_id,)).fetchone()
        if not referrer or not referrer["active"] or not referred:
            return False
        exists = connection.execute("SELECT 1 FROM referrals WHERE referred_user_id=?", (referred_user_id,)).fetchone()
        if exists:
            return False
        try:
            connection.execute(
                "INSERT INTO referrals(referrer_id,referred_user_id,status,reward_amount,created_at) VALUES(?,?, 'pending',0,?)",
                (referrer_id, referred_user_id, iso_now()),
            )
            connection.commit()
            return True
        except sqlite3.IntegrityError:
            connection.rollback()
            return False


def reward_referral_for_order(connection: sqlite3.Connection, referred_user_id: int, order_id: int, now: str) -> tuple[bool, Decimal, int | None]:
    """Qualify the first successful product order and credit the exact configured reward once."""
    referral = connection.execute(
        "SELECT * FROM referrals WHERE referred_user_id=? AND status='pending'",
        (int(referred_user_id),),
    ).fetchone()
    if not referral:
        return False, Decimal("0.00"), None
    reward = referral_reward_amount()
    connection.execute(
        "UPDATE referrals SET status='qualified', qualified_order_id=?, reward_amount=?, rewarded_at=? WHERE id=? AND status='pending'",
        (int(order_id), float(reward), now, int(referral["id"])),
    )
    if reward > 0:
        user = connection.execute("SELECT balance FROM users WHERE id=?", (int(referral["referrer_id"]),)).fetchone()
        if not user:
            raise sqlite3.IntegrityError("Referral referrer account missing")
        before = Decimal(str(user["balance"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        after = (before + reward).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        connection.execute("UPDATE users SET balance=?, updated_at=? WHERE id=?", (float(after), now, int(referral["referrer_id"])))
        connection.execute(
            "INSERT INTO wallet_transactions(user_id,order_id,type,amount,balance_before,balance_after,note,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (int(referral["referrer_id"]), int(order_id), "referral_reward", float(reward), float(before), float(after), f"Referral reward for user {referred_user_id}", now),
        )
    return True, reward, int(referral["referrer_id"])


async def referral_screen(update: Update, back_callback: str = "home") -> None:
    user_id = int(update.effective_user.id)
    bot_user = await update.get_bot().get_me()
    username = bot_user.username or ""
    link = f"https://t.me/{username}?start={referral_code_for(user_id)}" if username else "Referral link unavailable"
    with db() as connection:
        stats = connection.execute("SELECT COUNT(*) AS total, COALESCE(SUM(reward_amount),0) AS earned FROM referrals WHERE referrer_id=? AND status='qualified'", (user_id,)).fetchone()
        pending = connection.execute("SELECT COUNT(*) AS total FROM referrals WHERE referrer_id=? AND status='pending'", (user_id,)).fetchone()["total"]
    reward = referral_reward_amount()
    blue_link = f'<a href="{safe(link)}">{safe(link)}</a>' if username else "Referral link unavailable"
    text = (f"{tr(user_id, 'referral_program')}\n\n"
            f"💰 {tr(user_id, 'reward')}: <b>{money(reward)}</b>\n"
            f"👥 {tr(user_id, 'successful')}: <b>{stats['total']}</b>\n"
            f"⏳ {tr(user_id, 'pending')}: <b>{pending}</b>\n"
            f"💵 {tr(user_id, 'earned')}: <b>{money(stats['earned'])}</b>\n\n"
            f"{tr(user_id, 'your_link')}\n{blue_link}\n\n"
            "Reward successful referred user's first completed product purchase ke baad wallet mein automatically credit hoga.\n"
            "Wallet balance ko store purchases mein use kiya ja sakta hai.")
    from urllib.parse import quote
    share_text = setting("referral_share_text", "SHIVAM STORE par join karein aur digital products dekhein.")
    share_url = f"https://t.me/share/url?url={quote(link, safe='')}&text={quote(share_text, safe='')}" if username else ""
    keyboard = []
    if share_url:
        keyboard.append([InlineKeyboardButton(tr(user_id, "share_referral"), url=share_url)])
    back_label = tr(user_id, "back_settings") if back_callback == "settings" else tr(user_id, "back_home")
    keyboard.append([button(back_label, back_callback)])
    await edit_or_send(update, text, InlineKeyboardMarkup(keyboard))


async def admin_referrals(update: Update) -> None:
    with db() as connection:
        reward = referral_reward_amount()
        summary = connection.execute(
            "SELECT COUNT(*) AS total, SUM(CASE WHEN status='qualified' THEN 1 ELSE 0 END) AS qualified, COALESCE(SUM(reward_amount),0) AS paid FROM referrals"
        ).fetchone()
        top = connection.execute(
            "SELECT r.referrer_id, u.username, u.first_name, COUNT(*) AS referrals, COALESCE(SUM(r.reward_amount),0) AS earned "
            "FROM referrals r JOIN users u ON u.id=r.referrer_id WHERE r.status='qualified' "
            "GROUP BY r.referrer_id ORDER BY referrals DESC, earned DESC LIMIT 15"
        ).fetchall()
    lines = [
        "🤝 <b>Referral Management</b>",
        "",
        f"💰 Reward per successful referral: <b>{money(reward)}</b>",
        f"👥 Total referrals: <b>{summary['total'] or 0}</b>",
        f"✅ Successful: <b>{summary['qualified'] or 0}</b>",
        f"💵 Total rewards paid: <b>{money(summary['paid'] or 0)}</b>",
        "", "🏆 <b>Top Referrers</b>",
    ]
    if top:
        for i, row in enumerate(top, 1):
            name = safe(row['username'] or row['first_name'] or str(row['referrer_id']))
            lines.append(f"{i}. <code>{row['referrer_id']}</code> • {name} • 👥 {row['referrals']} • 💰 {money(row['earned'])}")
    else:
        lines.append("No referral activity yet.")
    await edit_or_send(update, "\n".join(lines), InlineKeyboardMarkup([[button("💰 Set Referral Reward", "admin:referral_set")], [button("📋 Referral Users", "admin:referral_users")], [button("⬅️ Admin Panel", "admin:main")]]))


async def admin_referral_users(update: Update) -> None:
    with db() as connection:
        rows = connection.execute(
            "SELECT r.referrer_id, r.referred_user_id, r.status, r.reward_amount, r.created_at, r.rewarded_at "
            "FROM referrals r ORDER BY r.id DESC LIMIT 30"
        ).fetchall()
    lines = ["📋 <b>Referral Activity</b>", ""]
    if not rows:
        lines.append("No referral records yet.")
    else:
        for row in rows:
            status = "✅" if row["status"] == "qualified" else "⏳"
            lines.append(f"{status} Referrer <code>{row['referrer_id']}</code> → User <code>{row['referred_user_id']}</code> • {money(row['reward_amount'])} • {display_date(row['created_at'])}")
    await edit_or_send(update, "\n".join(lines), InlineKeyboardMarkup([[button("⬅️ Referral Management", "admin:referrals")]]))


def home_text(user_id: int) -> str:
    with db() as connection:
        user = connection.execute(
            "SELECT first_name, balance, is_reseller FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    name = safe(user["first_name"] if user else "there")
    role = "RESELLER" if user and user["is_reseller"] else "USER"
    balance = money(user["balance"] if user else 0)
    store_name = safe(setting("store_name", "SHIVAM STORE"))
    tagline = safe(setting("store_tagline", "Premium digital products • Fast delivery • Trusted support"))
    lang = user_language(user_id)
    if lang == "hi":
        return (f"✨ <b>— {store_name} —</b> ✨\n\n👋 स्वागत है, <b>{name}</b>\n\n"
                "╭━━━━━━━━━━━━━━━━━━╮\n│  💎 <b>PREMIUM STORE</b>  │\n├━━━━━━━━━━━━━━━━━━┤\n│ 🎮 Premium Digital Products\n│ ⚡ Fast & Secure Delivery\n│ 🔐 Verified Payment Processing\n│ 🎧 Dedicated Support\n╰━━━━━━━━━━━━━━━━━━╯\n\n"
                f"━━━━━━━━━━━━━━━━\n🧑 यूज़र ID: <code>{user_id}</code>\n🏷️ भूमिका: <b>{role}</b>\n💰 वॉलेट बैलेंस: <b>{balance}</b>\n━━━━━━━━━━━━━━━━\n\n✨ {tagline}\n"
                + (f"\n📢 <b>सूचना</b>\n{safe(setting('store_announcement'))}\n" if setting('store_announcement') else "") + "\n🔥 नीचे से शॉप करना शुरू करें!")
    return (f"✨ <b>— {store_name} —</b> ✨\n\n👋 Welcome, <b>{name}</b>\n\n"
            "╭━━━━━━━━━━━━━━━━━━╮\n│  💎 <b>PREMIUM STORE</b>  │\n├━━━━━━━━━━━━━━━━━━┤\n│ 🎮 Premium Digital Products\n│ ⚡ Fast & Secure Delivery\n│ 🔐 Verified Payment Processing\n│ 🎧 Dedicated Support\n╰━━━━━━━━━━━━━━━━━━╯\n\n"
            f"━━━━━━━━━━━━━━━━\n🧑 User ID: <code>{user_id}</code>\n🏷️ Role: <b>{role}</b>\n💰 Wallet Balance: <b>{balance}</b>\n━━━━━━━━━━━━━━━━\n\n✨ {tagline}\n"
            + (f"\n📢 <b>Notice</b>\n{safe(setting('store_announcement'))}\n" if setting('store_announcement') else "") + "\n🔥 Tap <b>Shop Now</b> to start!")


def verification_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("✅ Verify Account", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def verification_screen(update: Update) -> None:
    await update.effective_message.reply_text(
        "🛡️ <b>To start shopping, please verify your account.</b>\n\n"
        "Telegram ka contact share button dabayein. Aapka number sirf "
        "account verification aur support ke liye use hoga.",
        parse_mode=ParseMode.HTML,
        reply_markup=verification_keyboard(),
    )


async def require_verified(update: Update) -> bool:
    user = update.effective_user
    if not user or not user_is_verified(user.id):
        await verification_screen(update)
        return False
    return True


async def deny_admin(update: Update) -> None:
    message = update.effective_message
    if message:
        await message.reply_text("⛔ Aapko admin access nahi hai.")


async def require_admin(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    user = update.effective_user
    if not user or not is_admin(user.id):
        await deny_admin(update)
        return False
    return True


# ---------------------------------------------------------------------------
# Telegram UI
# ---------------------------------------------------------------------------

def button(text: str, callback: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text, callback_data=callback)


def main_keyboard(user_id: int | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [button("🛍️  ✦  " + tr(user_id, "shop") + "  ✦", "shop")],
        [button(tr(user_id, "profile"), "profile"), button(tr(user_id, "wallet"), "balance")],
        [button(tr(user_id, "referral"), "referral"), button(tr(user_id, "orders"), "history")],
        [button(tr(user_id, "support"), "support"), button("🎥  Selling Proof + Tutorial", "proof_tutorial")],
        [button(tr(user_id, "reseller"), "reseller"), button(tr(user_id, "settings"), "settings")],
        [button("🌐  ✦  " + tr(user_id, "language") + "  ✦", "language")],
    ])


async def settings_screen(update: Update) -> None:
    user_id = int(update.effective_user.id)
    text = (f"{tr(user_id, 'settings_title')}\n\n"
            "Choose a section below to manage your account preferences, security and information.")
    keyboard = InlineKeyboardMarkup([
        [button("👤 Account", "settings:account"), button("🔐 Security", "settings:security")],
        [button("🔔 Notifications", "settings:notifications"), button("💰 Wallet", "settings:wallet")],
        [button("🛒 Shopping", "settings:shopping"), button("🔗 Referral", "settings:referral")],
        [button("🎧 Support", "settings:support"), button("ℹ️ About", "settings:about")],
        [button("🔄 Reset Settings", "settings:reset")],
        [button(tr(user_id, "back_home"), "home")],
    ])
    await edit_or_send(update, text, keyboard)


async def settings_account(update: Update) -> None:
    user_id = int(update.effective_user.id)
    with db() as connection:
        user = connection.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        completed = connection.execute("SELECT COUNT(*) AS c FROM orders WHERE user_id=? AND status='approved'", (user_id,)).fetchone()["c"]
        referrals = connection.execute("SELECT COUNT(*) AS c FROM referrals WHERE referrer_id=? AND status='qualified'", (user_id,)).fetchone()["c"]
    joined = display_date(user["created_at"]) if user and user["created_at"] else "—"
    text = ("👤 <b>Account Information</b>\n\n"
            f"👤 Name: <b>{safe(user['first_name'] if user else update.effective_user.first_name)}</b>\n"
            f"🔗 Username: <b>{safe('@'+user['username'] if user and user['username'] else '—')}</b>\n"
            f"🆔 Telegram ID: <code>{user_id}</code>\n"
            f"📅 Joined Date: <b>{safe(joined)}</b>\n"
            f"🏷️ Account Status: <b>{'Active' if user and user['active'] else 'Disabled'}</b>\n"
            f"🌐 Language: <b>{safe(user_language(user_id))}</b>\n"
            f"🎨 Theme Preference: <b>{safe(theme_preference(user_id).title())}</b>\n"
            f"💰 Balance: <b>{money(user['balance'] if user else 0)}</b>\n"
            f"📦 Completed Orders: <b>{completed}</b>\n"
            f"👥 Successful Referrals: <b>{referrals}</b>")
    await edit_or_send(update, text, InlineKeyboardMarkup([
        [button("🎨 Theme Preference", "settings:theme")],
        [button(tr(user_id,'back_settings'),'settings')],
    ]))


async def settings_security(update: Update) -> None:
    user_id = int(update.effective_user.id)
    configured = user_password_is_configured(user_id)
    active = user_password_lock_active(user_id)
    text = ("🔐 <b>Bot Security</b>\n\n"
            "Bot Password Lock protects this bot's user access; it does not lock Telegram itself.\n\n"
            f"🔐 Bot Password Lock: <b>{'ON' if active else ('Set' if configured else 'OFF')}</b>")
    rows=[]
    if configured:
        rows.append([button("🔄 Change Password", "settings:password_change"), button("🔓 Disable Password Lock", "settings:password_disable")])
        rows.append([button("⏱️ Remember Unlock", "settings:remember"), button("🚪 Lock Now", "settings:password_lock")])
    else:
        rows.append([button("🔑 Set Password", "settings:password_set")])
    rows.append([button("🛡️ Failed Password Protection", "settings:failed_protection")])
    rows.append([button(tr(user_id,'back_settings'),'settings')])
    await edit_or_send(update, text, InlineKeyboardMarkup(rows))


async def settings_notifications(update: Update) -> None:
    user_id = int(update.effective_user.id)
    with db() as connection:
        row = connection.execute("SELECT notifications_enabled,payment_notifications,order_notifications,referral_notifications,wallet_notifications,announcement_notifications FROM users WHERE id=?", (user_id,)).fetchone()
    labels = [
        ("🔔 Notifications ON/OFF", "notifications_enabled"),
        ("💳 Payment Notifications", "payment_notifications"),
        ("📦 Order Notifications", "order_notifications"),
        ("🎁 Referral Notifications", "referral_notifications"),
        ("💰 Wallet Activity Notifications", "wallet_notifications"),
        ("📢 Important Announcements", "announcement_notifications"),
    ]
    rows=[]
    for label, key in labels:
        state = bool(row[key]) if row else True
        rows.append([button(f"{label}: {'🟢 ON' if state else '⚪ OFF'}", f"settings:notify:{key}")])
    rows.append([button(tr(user_id,'back_settings'),'settings')])
    await edit_or_send(update, "🔔 <b>Notifications</b>\n\nChoose which notifications you want to receive.", InlineKeyboardMarkup(rows))


async def settings_wallet(update: Update) -> None:
    user_id = int(update.effective_user.id)
    with db() as connection:
        user = connection.execute("SELECT balance FROM users WHERE id=?", (user_id,)).fetchone()
        recent = connection.execute("SELECT type,amount,balance_after,created_at FROM wallet_transactions WHERE user_id=? ORDER BY id DESC LIMIT 10", (user_id,)).fetchall()
    lines=["💰 <b>Wallet</b>", "", f"💵 Wallet Information: <b>{money(user['balance'] if user else 0)}</b>", "", "📊 <b>Wallet Transaction History</b>"]
    if recent:
        for row in recent:
            sign = "+" if row["type"] in {"deposit","admin_credit","referral_reward"} else "-"
            lines.append(f"{sign}{money(row['amount'])} • {safe(row['type'].title())} • {safe(display_date(row['created_at']))}")
    else:
        lines.append("No wallet transactions yet.")
    await edit_or_send(update, "\n".join(lines), InlineKeyboardMarkup([
        [button("📊 Wallet Transaction History", "settings:wallet_history")],
        [button("🎁 Referral Earnings", "settings:referral_earnings")],
        [button("💸 Wallet Activity Notifications", "settings:notify:wallet_notifications")],
        [button("➕ Deposit via Gateway", "deposit")],
        [button(tr(user_id,'back_settings'),'settings')],
    ]))


async def settings_wallet_history(update: Update) -> None:
    user_id=int(update.effective_user.id)
    with db() as connection:
        rows=connection.execute("SELECT type,amount,balance_before,balance_after,note,created_at FROM wallet_transactions WHERE user_id=? ORDER BY id DESC LIMIT 50",(user_id,)).fetchall()
    lines=["📊 <b>Wallet Transaction History</b>", ""]
    for r in rows:
        sign="+" if r['type'] in {"deposit","admin_credit","referral_reward"} else "-"
        lines.append(f"{sign}{money(r['amount'])} • {safe(r['type'].title())} • {safe(display_date(r['created_at']))}")
    if not rows: lines.append("No transactions yet.")
    await edit_or_send(update,"\n".join(lines),InlineKeyboardMarkup([[button(tr(user_id,'back_settings'),'settings:wallet')]]))


async def settings_referral_earnings(update: Update) -> None:
    user_id=int(update.effective_user.id)
    with db() as connection:
        rows=connection.execute("SELECT reward_amount,qualified_order_id,rewarded_at FROM referrals WHERE referrer_id=? AND status='qualified' ORDER BY id DESC LIMIT 50",(user_id,)).fetchall()
    lines=["🎁 <b>Referral Earnings</b>", ""]
    total=Decimal("0")
    for r in rows:
        total += Decimal(str(r['reward_amount'] or 0))
        lines.append(f"🎁 {money(r['reward_amount'])} • Order #{r['qualified_order_id']} • {safe(display_date(r['rewarded_at']))}")
    lines.insert(1,f"Total earned: <b>{money(total)}</b>")
    if not rows: lines.append("No referral earnings yet.")
    await edit_or_send(update,"\n".join(lines),InlineKeyboardMarkup([[button(tr(user_id,'back_settings'),'settings:wallet')]]))


async def settings_shopping(update: Update) -> None:
    user_id = int(update.effective_user.id)
    await edit_or_send(update, "🛒 <b>Shopping</b>\n\n🛍️ Purchase Preferences\n📦 Order Updates\n🧾 Order History Shortcut", InlineKeyboardMarkup([
        [button("🛍️ Purchase Preferences", "settings:purchase_prefs")],
        [button("📦 Order Updates", "settings:notify:order_notifications")],
        [button("🧾 Order History", "history")],
        [button(tr(user_id,'back_settings'),'settings')],
    ]))


async def settings_purchase_prefs(update: Update) -> None:
    user_id=int(update.effective_user.id)
    await edit_or_send(update,"🛍️ <b>Purchase Preferences</b>\n\nYour selected language, reseller status and wallet availability are used automatically during shopping.",InlineKeyboardMarkup([[button(tr(user_id,'back_settings'),'settings:shopping')]]))


async def settings_referral(update: Update) -> None:
    await referral_screen(update, back_callback="settings")


async def settings_support(update: Update) -> None:
    user_id=int(update.effective_user.id)
    await edit_or_send(update,"🎧 <b>Support & Help</b>\n\nGet help with payments, orders, products and account issues.",InlineKeyboardMarkup([
        [button("🎧 Support", "support")],
        [button("❓ Help / FAQ", "settings:faq")],
        [button(tr(user_id,'back_settings'),'settings')],
    ]))


async def settings_about(update: Update) -> None:
    user_id = int(update.effective_user.id)
    rows=[]
    if setting("support_url"): rows.append([InlineKeyboardButton("🎧 Support", url=setting("support_url"))])
    if setting("tutorial_url"): rows.append([InlineKeyboardButton("📖 Tutorial", url=setting("tutorial_url"))])
    if setting("selling_proof_url"): rows.append([InlineKeyboardButton("💰 Selling Proof", url=setting("selling_proof_url"))])
    if setting("paid_store_url"): rows.append([InlineKeyboardButton("🏪 Paid Store", url=setting("paid_store_url"))])
    rows += [[button("📜 Terms & Conditions", "settings:terms")], [button("🔒 Privacy Policy", "settings:privacy")], [button("ℹ️ About Bot", "settings:about_bot")], [button("🆕 What's New / Changelog", "settings:changelog")], [button(tr(user_id,'back_settings'),'settings')]]
    await edit_or_send(update, "🛠️ <b>Support & Information</b>\n\nSupport, Help/FAQ, policies, bot information and changelog.", InlineKeyboardMarkup(rows))


async def settings_info_page(update: Update, title: str, body: str, back: str = "settings:about") -> None:
    user_id=int(update.effective_user.id)
    await edit_or_send(update,f"{title}\n\n{body}",InlineKeyboardMarkup([[button("‹  Back",back)]]))


async def settings_theme(update: Update) -> None:
    user_id = int(update.effective_user.id)
    text = ("🎨 <b>Theme Preference</b>\n\n"
            f"Current preference: <b>{safe(theme_preference(user_id).title())}</b>\n\n"
            "This preference is stored for your account. Telegram chat appearance itself is controlled by Telegram.")
    await edit_or_send(update, text, InlineKeyboardMarkup([
        [button("🌟 Default", "settings:theme:default")],
        [button("✨ Premium", "settings:theme:premium")],
        [button("📦 Compact", "settings:theme:compact")],
        [button(tr(user_id,'back_settings'),'settings:account')],
    ]))


async def settings_reset(update: Update) -> None:
    user_id = int(update.effective_user.id)
    with db() as connection:
        connection.execute("UPDATE users SET notifications_enabled=1,payment_notifications=1,order_notifications=1,referral_notifications=1,wallet_notifications=1,announcement_notifications=1,theme_preference='default',password_remember_until='',password_remember_minutes=60,updated_at=? WHERE id=?", (iso_now(), user_id))
        connection.commit()
    await settings_screen(update)


def back_home(user_id: int | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[button(tr(user_id, "back_home"), "home")]])


def back_button(callback: str = "home", user_id: int | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[button(tr(user_id, "back"), callback)]])


async def edit_or_send(
    update: Update, text: str, reply_markup: InlineKeyboardMarkup | None = None
) -> None:
    query = update.callback_query
    if query:
        try:
            await query.edit_message_text(
                text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
            )
        except Exception:
            if query.message:
                await query.message.reply_text(
                    text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
                )
    elif update.effective_message:
        await update.effective_message.reply_text(
            text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
        )


async def edit_tracked_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    chat_id = context.user_data.get("screen_chat_id")
    message_id = context.user_data.get("screen_message_id")
    if chat_id and message_id:
        try:
            await update.get_bot().edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
            )
            return
        except Exception:
            logging.debug("Tracked screen could not be edited", exc_info=True)
    await edit_or_send(update, text, reply_markup)


def remember_screen(context: ContextTypes.DEFAULT_TYPE, message: Any) -> None:
    if message:
        context.user_data["screen_chat_id"] = message.chat_id
        context.user_data["screen_message_id"] = message.message_id


def remember_admin_message(context: ContextTypes.DEFAULT_TYPE, message: Any) -> None:
    """Track temporary bot messages created during an admin session."""
    if not message:
        return
    ids = context.user_data.setdefault("admin_session_message_ids", [])
    pair = (int(message.chat_id), int(message.message_id))
    if pair not in ids:
        ids.append(pair)


async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, **kwargs: Any) -> Any:
    """Send an admin form message and make it removable on logout."""
    message = update.effective_message
    if not message:
        return None
    sent = await message.reply_text(text, **kwargs)
    if update.effective_user and is_admin(update.effective_user.id):
        remember_admin_message(context, sent)
    return sent


async def cleanup_admin_session_messages(update: Update, context: ContextTypes.DEFAULT_TYPE, delete_screen: bool = False) -> None:
    """Best-effort removal of temporary admin chat messages."""
    pairs = list(context.user_data.get("admin_session_message_ids", []))
    if delete_screen:
        chat_id = context.user_data.get("screen_chat_id")
        message_id = context.user_data.get("screen_message_id")
        if chat_id and message_id:
            pairs.append((int(chat_id), int(message_id)))
    seen = set()
    for chat_id, message_id in pairs:
        key = (int(chat_id), int(message_id))
        if key in seen:
            continue
        seen.add(key)
        try:
            await update.get_bot().delete_message(chat_id=key[0], message_id=key[1])
        except Exception:
            logging.debug("Admin session message could not be deleted", exc_info=True)
    context.user_data.pop("admin_session_message_ids", None)


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [button("📊 Dashboard", "admin:analytics"), button("📦 Catalog", "admin:catalog")],
            [button("🧾 Payments", "admin:pending"), button("👥 Users", "admin:users")],
            [button("🔎 Find Order", "admin:order_search"), button("📦 Stock", "admin:stock")],
            [button("🤝 Resellers", "admin:reseller")],
            [button("📣 Broadcast", "admin:broadcast"), button("⚙️ Settings", "admin:settings")],
            [button("🩺 System Health", "admin:health"), button("💾 Backup DB", "admin:backup")],
            [button("🔁 Failed Deliveries", "admin:failed_delivery"), button("🚧 Maintenance", "admin:maintenance")],
            [button("⚠️ Risk Alerts", "admin:risk"), button("🗓️ Scheduled Broadcast", "admin:schedule")],
            [button("🤝 Referral Management", "admin:referrals")],
            [button("🌐 Content Languages", "admin:translations")],
            [button("🚪 Logout", "admin:logout")],
        ]
    )


def admin_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[button("⬅️ Admin Panel", "admin:main")]])


async def password_gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user:
        return True
    unlocked_until = str(context.user_data.get("password_unlocked_until", "") or "")
    if unlocked_until:
        try:
            if datetime.fromisoformat(unlocked_until.replace("Z", "+00:00")) > utc_now():
                return True
        except ValueError:
            context.user_data.pop("password_unlocked_until", None)
    if not user_password_lock_active(user.id):
        return True
    context.user_data["flow"] = "user_password_unlock"
    await edit_or_send(update, "🔐 <b>Bot Locked</b>\n\nPassword enter karein to continue.", InlineKeyboardMarkup([[button("🚫 Cancel", "home")]]))
    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user:
        upsert_user(update.effective_user)
        args = getattr(context, "args", None) or []
        if args and re.fullmatch(r"ref_(\d+)", str(args[0])):
            register_referral(int(str(args[0]).split("_", 1)[1]), int(update.effective_user.id))
    await cleanup_admin_session_messages(update, context, delete_screen=True)
    context.user_data.clear()
    try:
        if update.effective_message:
            await update.effective_message.delete()
    except Exception:
        logging.debug("/start message could not be deleted", exc_info=True)
    if update.effective_user and not user_is_verified(update.effective_user.id):
        await verification_screen(update)
        return
    if update.effective_user and not await password_gate(update, context):
        return
    sent = await update.get_bot().send_message(
        chat_id=update.effective_chat.id,
        text=home_text(update.effective_user.id),
        reply_markup=main_keyboard(update.effective_user.id),
        parse_mode=ParseMode.HTML,
    )
    remember_screen(context, sent)


async def contact_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    contact = message.contact if message else None
    if not user or not contact:
        return
    if contact.user_id != user.id:
        await message.reply_text(
            "⚠️ Please apna hi Telegram contact share karein.",
            reply_markup=verification_keyboard(),
        )
        return
    with db() as connection:
        connection.execute(
            "UPDATE users SET phone = ?, phone_verified = 1, updated_at = ? WHERE id = ?",
            (contact.phone_number, iso_now(), user.id),
        )
        connection.commit()
    context.user_data.clear()
    await message.reply_text(
        "✅ Account verified successfully.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.reply_text(
        home_text(user.id),
        reply_markup=main_keyboard(update.effective_user.id),
        parse_mode=ParseMode.HTML,
    )


async def version_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        f"✅ <b>{BOT_VERSION}</b>\n\nCustomer shopping features are loaded from this build; admin controls are website-only.",
        parse_mode=ParseMode.HTML,
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    await update.effective_message.reply_text(
        "Current process cancel ho gaya.",
        reply_markup=main_keyboard(update.effective_user.id),
    )


async def language_screen(update: Update) -> None:
    user_id = update.effective_user.id
    current = user_language(user_id)
    rows = []
    items = list(SUPPORTED_LANGUAGES.items())
    for i in range(0, len(items), 2):
        row = []
        for code, label in items[i:i+2]:
            prefix = "✅ " if code == current else ""
            row.append(button(prefix + label, f"language:{code}"))
        rows.append(row)
    rows.append([button(tr(user_id, "back_home"), "home")])
    await edit_or_send(update, tr(user_id, "choose_language"), InlineKeyboardMarkup(rows))


async def show_categories(update: Update) -> None:
    with db() as connection:
        rows = connection.execute(
            "SELECT id, name, name_i18n FROM categories WHERE active = 1 ORDER BY name"
        ).fetchall()
    if not rows:
        await edit_or_send(update, "📦 Abhi koi category available nahi hai.", back_home())
        return
    lang = user_language(update.effective_user.id)
    keyboard = [[button(f"📁 {safe(localized_text(row, 'name', lang))}", f"cat:{row['id']}")] for row in rows]
    keyboard.append([button("‹  Back to Main Menu", "home")])
    await edit_or_send(
        update,
        "📦 <b>Choose a category</b>\n\nSelect where you want to shop.",
        InlineKeyboardMarkup(keyboard),
    )


async def show_products(update: Update, category_id: int) -> None:
    with db() as connection:
        category = connection.execute(
            "SELECT name, description, name_i18n, description_i18n FROM categories WHERE id = ? AND active = 1", (category_id,)
        ).fetchone()
        products = connection.execute(
            "SELECT id, name, maintenance_mode, name_i18n FROM products WHERE category_id = ? AND active = 1 ORDER BY name",
            (category_id,),
        ).fetchall()
    if not category:
        await edit_or_send(update, "Category nahi mili.", back_home())
        return
    if not products:
        await edit_or_send(update, "Is category mein abhi koi product nahi hai.", back_home())
        return
    lang = user_language(update.effective_user.id)
    keyboard = [[button(("🚧 " if row["maintenance_mode"] else "🛍️ ") + safe(localized_text(row, "name", lang)), f'prod:{row["id"]}')] for row in products]
    keyboard.append([button("‹  Back to Categories", "shop")])
    await edit_or_send(
        update,
        f"🛒 <b>{safe(localized_text(category, 'name', lang))}</b>\n"
        + (f"{safe(localized_text(category, 'description', lang))}\n\n" if localized_text(category, 'description', lang) else "\n")
        + tr(update.effective_user.id, "select_product"),
        InlineKeyboardMarkup(keyboard),
    )


async def show_plans(update: Update, product_id: int) -> None:
    with db() as connection:
        product = connection.execute(
            "SELECT id, category_id, name, description, channel_link, maintenance_mode, name_i18n, description_i18n FROM products WHERE id = ? AND active = 1",
            (product_id,),
        ).fetchone()
        plans = connection.execute(
            "SELECT id, name, days, customer_price, reseller_price, name_i18n, description_i18n FROM plans "
            "WHERE product_id = ? AND active = 1 ORDER BY days",
            (product_id,),
        ).fetchall()
        user = connection.execute(
            "SELECT is_reseller FROM users WHERE id = ?",
            (update.effective_user.id,),
        ).fetchone()
    lang = user_language(update.effective_user.id)
    if not product:
        await edit_or_send(update, "Product nahi mila.", back_home())
        return
    if not plans:
        await edit_or_send(update, "Is product ka koi plan available nahi hai.", back_home())
        return
    reseller = bool(user and user["is_reseller"])
    lines = [f"🛍️ <b>{safe(localized_text(product, 'name', lang))}</b>"]
    if product["channel_link"]:
        lines.append(f"📢 Channel: <a href=\"{safe(product['channel_link'])}\">Open Channel</a>")
    product_desc = localized_text(product, "description", lang)
    if product_desc:
        lines.append(f"\n{safe(product_desc)}")
    lines.append("\n" + tr(update.effective_user.id, "plan_select"))
    keyboard = []
    for plan in plans:
        price = plan["reseller_price"] if reseller else plan["customer_price"]
        plan_name = localized_text(plan, "name", lang)
        lines.append(f"• {safe(plan_name)} — {plan['days']} {tr(update.effective_user.id, 'days')} — {money(price)}")
        keyboard.append([button(f"{safe(plan_name)} • {plan['days']} {tr(update.effective_user.id, 'days')} • {money(price)}", f"plan:{plan['id']}")])
    keyboard.append([button("‹  Back to Products", f"cat:{product['category_id']}")])
    await edit_or_send(update, "\n".join(lines), InlineKeyboardMarkup(keyboard))


def plan_details(plan_id: int, user_id: int) -> tuple[sqlite3.Row, bool] | None:
    with db() as connection:
        plan = connection.execute(
            """
            SELECT plans.*, products.name AS product_name, products.channel_link, products.maintenance_mode, products.name_i18n AS product_name_i18n, plans.name_i18n AS plan_name_i18n, plans.description_i18n AS plan_description_i18n
            FROM plans JOIN products ON products.id = plans.product_id
            WHERE plans.id = ? AND plans.active = 1 AND products.active = 1
            """,
            (plan_id,),
        ).fetchone()
        user = connection.execute(
            "SELECT is_reseller FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return (plan, bool(user and user["is_reseller"])) if plan else None


async def show_plan(update: Update, plan_id: int) -> None:
    result = plan_details(plan_id, update.effective_user.id)
    if not result:
        await edit_or_send(update, "Plan available nahi hai.", back_home())
        return
    plan, reseller = result
    if plan["maintenance_mode"]:
        await edit_or_send(update, f"🚧 <b>{safe(plan['product_name'])}</b>\n\nYe product abhi maintenance mein hai. Buying temporarily disabled hai.", back_button(f"prod:{plan['product_id']}"))
        return
    lang = user_language(update.effective_user.id)
    price = plan["reseller_price"] if reseller else plan["customer_price"]
    with db() as connection:
        stock = connection.execute(
            "SELECT COUNT(*) AS count FROM stock_keys WHERE plan_id = ? AND status = 'available'",
            (plan_id,),
        ).fetchone()["count"]
    role_label = tr(update.effective_user.id, "reseller_price") if reseller else tr(update.effective_user.id, "price")
    text = (
        f"🛍️ <b>{safe(plan['product_name'])}</b>\n"
        f"📌 {tr(update.effective_user.id, 'plan')}: <b>{safe(localized_json(plan['plan_name_i18n'], lang) or plan['name'])}</b>\n"
        f"⏳ {tr(update.effective_user.id, 'validity')}: <b>{plan['days']} {tr(update.effective_user.id, 'days')}</b>\n"
        f"💰 {role_label}: <b>{money(price)}</b>\n"
        f"📦 {tr(update.effective_user.id, 'stock')}: <b>{stock}</b>\n\n"
    )
    plan_desc = localized_json(plan["plan_description_i18n"], lang) or plan["description"]
    if plan_desc:
        text += f"📝 {safe(plan_desc)}\n\n"
    text += "Payment automatically verify hone ke baad key ke saath start date aur expiry date milegi."
    keyboard = [
        [button(f"{tr(update.effective_user.id, 'buy_upi')} — {money(price)}", f"buy:{plan_id}")],
        [button(tr(update.effective_user.id, "use_wallet"), f"walletbuy:{plan_id}")],
        [button("‹  Back to Products", f"prod:{plan['product_id']}")],
    ]
    await edit_or_send(update, text, InlineKeyboardMarkup(keyboard))


def calculate_coupon(code: str, original: float) -> tuple[float, str] | None:
    if not code:
        return original, ""
    with db() as connection:
        coupon = connection.execute(
            "SELECT * FROM coupons WHERE code = ? AND active = 1", (code.upper(),)
        ).fetchone()
    if not coupon:
        return None
    if coupon["max_uses"] and coupon["used_count"] >= coupon["max_uses"]:
        return None
    if coupon["expires_at"] and coupon["expires_at"] < iso_now():
        return None
    if coupon["discount_type"] == "percent":
        if not 0 < float(coupon["discount_value"]) <= 100:
            return None
        final = original - (original * float(coupon["discount_value"]) / 100)
    else:
        if float(coupon["discount_value"]) <= 0:
            return None
        final = original - float(coupon["discount_value"])
    return max(0, round(final, 2)), code.upper()


def gateway_configured() -> bool:
    callback_base = (os.getenv("PUBLIC_BASE_URL", "").strip() or os.getenv("RENDER_EXTERNAL_URL", "").strip()).rstrip("/")
    return (setting("payment_gateway_enabled", "0").strip().lower() in {"1","true","yes","on"}
            and setting("payment_gateway_url", "").strip().lower().startswith("https://")
            and bool(setting("payment_gateway_api_key", "").strip())
            and bool(callback_base))

def _gateway_value(obj: Any, names: tuple[str, ...]) -> str:
    if isinstance(obj, dict):
        for k,v in obj.items():
            if str(k).lower() in names and isinstance(v,(str,int,float)) and str(v).strip(): return str(v).strip()
        for v in obj.values():
            x=_gateway_value(v,names)
            if x: return x
    elif isinstance(obj,list):
        for v in obj:
            x=_gateway_value(v,names)
            if x: return x
    return ""

def _gateway_create_sync(url: str, key: str, order_no: str, amount: float) -> dict[str,Any]:
    callback_url=os.getenv("GATEWAY_CALLBACK_URL", "").strip();params={"api_key":key,"order_id":order_no,"amount":f"{amount:.2f}"};
    if callback_url: params.update({"callback_url":callback_url,"notify_url":callback_url,"webhook_url":callback_url})
    if any(x in url for x in ("{API_KEY}","{ORDER_ID}","{AMOUNT}")):
        target=url.replace("{API_KEY}",key).replace("{ORDER_ID}",order_no).replace("{AMOUNT}",f"{amount:.2f}")
    else:
        target=url+("&" if "?" in url else "?")+urlencode(params)
    req=urllib.request.Request(target,method="GET",headers={"Accept":"application/json,text/html;q=0.9,*/*;q=0.8","User-Agent":"SHIVAM-STORE-BOT/3.0"})
    last_error = "Gateway request failed"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=20) as resp:
                raw=resp.read(512*1024).decode("utf-8",errors="replace")
                try: payload=json.loads(raw)
                except Exception: payload={"raw":raw}
                return {"ok":True,"payload":payload}
        except urllib.error.HTTPError as e:
            last_error=f"Gateway HTTP {e.code}"
            if e.code not in {408,425,429,500,502,503,504}:
                break
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_error=str(e)[:250]
        except Exception as e:
            last_error=str(e)[:250]
        if attempt < 2:
            time.sleep(1.5 * (2 ** attempt))
    return {"ok":False,"error":last_error}

async def create_gateway_payment(order_no: str, amount: float) -> dict[str,Any]:
    if not gateway_configured(): return {"ok":False,"error":"Payment gateway is not configured."}
    r=await asyncio.to_thread(_gateway_create_sync,setting("payment_gateway_url","").strip(),setting("payment_gateway_api_key","").strip(),order_no,amount)
    if not r.get("ok"): logging.warning("Gateway create failed: %s",r.get("error")); return r
    payload=r.get("payload") or {}
    payment_url=_gateway_value(payload,("payment_url","payment_link","checkout_url","checkout","redirect_url","redirect","url","link"))
    qr_url=_gateway_value(payload,("qr_url","qr_code_url","qr","qrcode"))
    if payment_url or qr_url: return {"ok":True,"payment_url":payment_url or qr_url}
    raw=str(payload.get("raw",""))
    if re.fullmatch(r"https://[^\s<>'\"]+",raw): return {"ok":True,"payment_url":raw}
    return {"ok":False,"error":"Gateway response did not include a payment/checkout URL."}

async def require_payment_configured(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if gateway_configured(): return True
    await edit_or_send(update, "⚠️ <b>Payment gateway unavailable</b>\n\nAdmin ko Payment Gateway API configure karna hoga.", back_home())
    return False

async def begin_product_order(update: Update, context: ContextTypes.DEFAULT_TYPE, plan_id: int) -> None:
    if not await require_payment_configured(update, context):
        return
    expire_stale_orders()
    result = plan_details(plan_id, update.effective_user.id)
    if not result:
        await edit_or_send(update, "Plan available nahi hai.", back_home())
        return
    plan, reseller = result
    if plan["maintenance_mode"]:
        await edit_or_send(update, "🚧 Ye product abhi maintenance mein hai. Buying temporarily disabled hai.", back_button(f"prod:{plan['product_id']}"))
        return
    with db() as connection:
        active = connection.execute(
            "SELECT 1 FROM orders WHERE user_id = ? AND status IN ('awaiting_utr','pending') "
            "AND created_at > ? LIMIT 1",
            (update.effective_user.id, (utc_now() - timedelta(minutes=20)).isoformat()),
        ).fetchone()
        stock = connection.execute(
            "SELECT 1 FROM stock_keys WHERE plan_id = ? AND status = 'available' LIMIT 1",
            (plan_id,),
        ).fetchone()
    if active:
        await edit_or_send(update, "Aapka ek payment already verification mein hai. Pehle uska result aane dein.", back_home())
        return
    if not stock:
        await edit_or_send(update, "Is plan ka stock abhi khatam hai. Admin jald keys add karega.", back_home())
        return
    original = float(plan["reseller_price"] if reseller else plan["customer_price"])
    coupon_result = calculate_coupon(str(context.user_data.get("coupon", "")), original)
    if coupon_result is None:
        context.user_data.pop("coupon", None)
        await edit_or_send(update, "Coupon invalid ya expire ho gaya. Dobara Buy Now dabayein.", back_home())
        return
    amount, coupon_code = coupon_result
    created = iso_now()
    with db() as connection:
        cursor = connection.execute(
            """
            INSERT INTO orders(
                order_no, user_id, plan_id, order_type, amount, original_amount,
                coupon_code, status, payment_method, created_at, expiry_at
            ) VALUES (?, ?, ?, 'product', ?, ?, ?, 'awaiting_utr', ?, ?, ?)
            """,
            (
                f"TEMP-{secrets.token_hex(8)}",
                update.effective_user.id,
                plan_id,
                amount,
                original,
                coupon_code,
                'gateway',
                created,
                (datetime.fromisoformat(created) + timedelta(minutes=20)).isoformat(timespec="seconds"),
            ),
        )
        order_id = cursor.lastrowid
        order_no = f"SHV-{datetime.now(TIMEZONE).strftime('%Y%m%d')}-{int(order_id):05d}"
        connection.execute("UPDATE orders SET order_no = ? WHERE id = ?", (order_no, order_id))
        connection.commit()
    context.user_data["flow"] = "payment_wait"
    context.user_data["current_order_id"] = int(order_id)
    context.user_data.pop("coupon", None)
    await send_payment_screen(
        update,
        context,
        order_no,
        amount,
        f"{safe(plan['product_name'])} • {safe(plan['name'])} • {plan['days']} Days",
        f"plan:{plan_id}",
    )


def order_no_to_id(order_no: str) -> int:
    with db() as connection:
        row = connection.execute("SELECT id FROM orders WHERE order_no=?", (order_no,)).fetchone()
        return int(row["id"]) if row else 0



async def delete_tracked_screen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.user_data.get("screen_chat_id")
    message_id = context.user_data.get("screen_message_id")
    if chat_id and message_id:
        try:
            await update.get_bot().delete_message(chat_id=int(chat_id), message_id=int(message_id))
        except Exception:
            logging.debug("Tracked screen could not be deleted", exc_info=True)
    context.user_data.pop("screen_chat_id", None)
    context.user_data.pop("screen_message_id", None)


async def send_clean_text_screen(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup: Any) -> None:
    await delete_tracked_screen(update, context)
    sent = await update.get_bot().send_message(update.effective_chat.id, text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    remember_screen(context, sent)


async def send_payment_screen(update: Update, context: ContextTypes.DEFAULT_TYPE, order_no: str, amount: float, item: str, back_callback: str = "home") -> None:
    context.user_data["payment_back_callback"] = back_callback
    if not gateway_configured():
        clear_flow(context)
        await edit_or_send(update, "⚠️ <b>Payment gateway unavailable</b>\n\nAdmin ko Payment Gateway API configure karna hoga.", back_home())
        return
    result=await create_gateway_payment(order_no,amount)
    if not result.get("ok"):
        clear_flow(context)
        await edit_or_send(update,"❌ Payment gateway se payment request create nahi ho saki. Please thodi der baad try karein.",back_home())
        return
    url=result.get("payment_url")
    try:
        with db() as connection:
            connection.execute(
                "INSERT INTO payment_events(provider,provider_event_id,order_id,event_type,received_at,details) VALUES(?,?,?,?,?,?)",
                ("gateway", "created:" + str(order_no), order_no_to_id(order_no), "payment_created", iso_now(), json.dumps({"payment_url": url}, ensure_ascii=False)[:2000]),
            )
            connection.commit()
    except Exception:
        logging.debug("Payment creation event already exists or could not be recorded", exc_info=True)
    rows=[]
    if url: rows.append([InlineKeyboardButton("💳 OPEN SECURE PAYMENT",url=url)])
    rows += [[button("🔄 PAYMENT STATUS","payment:status")],[button("❌ CANCEL PAYMENT","payment:cancel")],[button("◀️ BACK","payment:back")]]
    text=f"🧾 <b>PAYMENT REQUEST</b>\n\n📋 Order: <code>{safe(order_no)}</code>\n📦 {item}\n💰 Pay Exact: <b>{money(amount)}</b>\n\n🔐 Secure gateway checkout ready hai. Payment complete hone ke baad gateway callback payment verify karega aur delivery automatically process hogi."
    await send_clean_text_screen(update,context,text,InlineKeyboardMarkup(rows))

def _email_text(message) -> str:
    parts = []
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_disposition() == "attachment":
                continue
            if part.get_content_type() in {"text/plain", "text/html"}:
                try:
                    parts.append(part.get_content())
                except Exception:
                    payload = part.get_payload(decode=True) or b""
                    parts.append(payload.decode(part.get_content_charset() or "utf-8", "ignore"))
    else:
        try:
            parts.append(message.get_content())
        except Exception:
            payload = message.get_payload(decode=True) or b""
            parts.append(payload.decode(message.get_content_charset() or "utf-8", "ignore"))
    text = "\n".join(str(x) for x in parts)
    # Gmail bank alerts are often HTML. Remove markup and decode entities before matching.
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(?:p|div|tr|li|td|th)>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    from html import unescape
    return unescape(text)


def _extract_email_sender(message) -> str:
    value = str(message.get("From", "")).lower()
    match = re.search(r"<([^>]+)>", value)
    return (match.group(1) if match else value).strip()


def _extract_utr_candidates(text: str) -> set[str]:
    compact = re.sub(r"\s+", " ", text.upper())
    candidates = set()
    patterns = [
        r"(?:UTR|RRN|TRANSACTION\s*(?:ID|NO|NUMBER)|TXN\s*(?:ID|NO|NUMBER)|REFERENCE\s*(?:ID|NO|NUMBER))\s*[:#\-]?\s*([A-Z0-9]{8,30})",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, compact):
            candidates.add(match.group(1))
    # User's stated UTR format is 12 digits; accept alphanumeric variants only when explicitly labelled above.
    candidates.update(re.findall(r"\b\d{12}\b", compact))
    return candidates


def _extract_amount_candidates(text: str) -> set[Decimal]:
    # Only accept currency-looking values to reduce false matches from dates/order numbers.
    values = set()
    for match in re.finditer(r"(?:₹|INR|RS\.?|AMOUNT\s*[:=])\s*([0-9][0-9,]*(?:\.\d{1,2})?)", text, re.IGNORECASE):
        try:
            values.add(decimal_amount(match.group(1)))
        except ValueError:
            pass
    return values


def _recipient_matches(text: str, upi_id: str) -> bool:
    if not upi_id:
        return False
    from html import unescape
    compact = re.sub(r"\s+", "", unescape(str(text))).lower()
    return upi_id.lower() in compact


def _sender_allowed(sender: str) -> bool:
    """Fail closed for automatic payment verification. Exact address or @domain only."""
    sender = (sender or "").strip().lower()
    if not IMAP_REQUIRE_TRUSTED_SENDER:
        return True
    if not IMAP_ALLOWED_SENDERS:
        return False
    for allowed in IMAP_ALLOWED_SENDERS:
        allowed = allowed.strip().lower()
        if "@" in allowed:
            if sender == allowed:
                return True
        else:
            domain = allowed.lstrip("@")
            if sender.endswith("@" + domain):
                return True
    return False


def _amount_matches_near_utr(text: str, expected_amount: Decimal, utr: str) -> bool:
    """Require the payment amount in the same local transaction block as the UTR.
    Balance/limit/footer amounts elsewhere in the email cannot satisfy the match.
    """
    compact = re.sub(r"\s+", " ", text, flags=re.MULTILINE)
    upper = compact.upper()
    positions = [m.start() for m in re.finditer(re.escape(utr.upper()), upper)]
    if not positions:
        return False
    windows = [compact[max(0, pos - 350):pos + 350] for pos in positions]
    labelled_pattern = re.compile(
        r"(?:AMOUNT|PAID|PAYMENT|RECEIVED|TRANSACTION\s*AMOUNT|AMOUNT\s*PAID)\s*"
        r"(?:[:=]|IS|OF)?\s*(?:₹|INR|RS\.?\s*)\s*"
        r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.I
    )
    for window in windows:
        for value in labelled_pattern.findall(window):
            try:
                if decimal_amount(value) == expected_amount:
                    return True
            except ValueError:
                pass
    # Fallback: currency token must be near the UTR, and balance/limit values are excluded.
    amount_pattern = re.compile(
        r"(?:₹|INR|RS\.?|AMOUNT\s*[:=])\s*"
        r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.I
    )
    for window in windows:
        for match in amount_pattern.finditer(window):
            context_before = window[max(0, match.start() - 60):match.start()].lower()
            if re.search(
                r"(?:available|current|opening|closing|previous|remaining|balance|limit|"
                r"cashback|fee|charge|minimum|maximum)\b", context_before
            ):
                continue
            try:
                if decimal_amount(match.group(1)) == expected_amount:
                    return True
            except ValueError:
                pass
    return False


def _imap_search_uids(mail: object, since: str, search_utr: str | None = None) -> list[int]:
    if search_utr:
        safe_utr = search_utr.replace(chr(92), chr(92)*2).replace(chr(34), chr(92)+chr(34))
        query = f'(SINCE "{since}" BODY "{safe_utr}")'
    else:
        query = f'(SINCE "{since}")'
    typ, data = mail.uid("SEARCH", None, query)
    if typ != "OK" or not data or not data[0]:
        return []
    return [int(x) for x in data[0].split() if x.isdigit()][-500:]


def _fetch_recent_imap_messages(search_utr: str | None = None) -> list[tuple[int, object, str]]:
    """Fetch recent payment emails using one authenticated IMAP session."""
    if not (IMAP_ENABLED and IMAP_USERNAME and IMAP_APP_PASSWORD):
        return []
    since = (datetime.now(timezone.utc) - timedelta(minutes=IMAP_LOOKBACK_MINUTES)).strftime("%d-%b-%Y")
    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, timeout=20)
    try:
        mail.login(IMAP_USERNAME, IMAP_APP_PASSWORD)
        typ, _ = mail.select(IMAP_FOLDER, readonly=True)
        if typ != "OK":
            return []
        results = []
        for uid in _imap_search_uids(mail, since, search_utr):
            typ, fetched = mail.uid("FETCH", str(uid), "(RFC822)")
            if typ != "OK":
                continue
            raw = next((item[1] for item in fetched if isinstance(item, tuple) and len(item) > 1), None)
            if not raw:
                continue
            msg = BytesParser(policy=policy.default).parsebytes(raw)
            sender = _extract_email_sender(msg)
            if not _sender_allowed(sender):
                continue
            results.append((uid, msg, sender))
        return results
    finally:
        try:
            mail.logout()
        except Exception:
            pass


def _fetch_recent_imap_messages_for_utrs(utrs: list[str]) -> dict[str, list[tuple[int, object, str]]]:
    """Search all pending UTRs through a single IMAP login per verification cycle."""
    if not (IMAP_ENABLED and IMAP_USERNAME and IMAP_APP_PASSWORD):
        return {}
    since = (datetime.now(timezone.utc) - timedelta(minutes=IMAP_LOOKBACK_MINUTES)).strftime("%d-%b-%Y")
    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, timeout=20)
    out: dict[str, list[tuple[int, object, str]]] = {}
    try:
        mail.login(IMAP_USERNAME, IMAP_APP_PASSWORD)
        typ, _ = mail.select(IMAP_FOLDER, readonly=True)
        if typ != "OK":
            return {}
        for utr in sorted(set(utrs)):
            if not re.fullmatch(r"[A-Z0-9]{12,30}", utr):
                continue
            messages=[]
            for uid in _imap_search_uids(mail, since, utr):
                typ, fetched = mail.uid("FETCH", str(uid), "(RFC822)")
                if typ != "OK":
                    continue
                raw = next((item[1] for item in fetched if isinstance(item, tuple) and len(item) > 1), None)
                if not raw:
                    continue
                msg = BytesParser(policy=policy.default).parsebytes(raw)
                sender = _extract_email_sender(msg)
                if _sender_allowed(sender):
                    messages.append((uid, msg, sender))
            out[utr] = messages
        return out
    finally:
        try:
            mail.logout()
        except Exception:
            pass

def _message_is_recent(message: object) -> bool:
    raw_date = str(message.get("Date", ""))
    if not raw_date:
        return False
    try:
        from email.utils import parsedate_to_datetime
        parsed = parsedate_to_datetime(raw_date)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)
        return timedelta(0) <= age <= timedelta(minutes=IMAP_LOOKBACK_MINUTES)
    except Exception:
        return False



def _match_payment_email(order: sqlite3.Row, messages: list[tuple[int, object, str]]) -> tuple[bool, str]:
    """Match one submitted UTR against a recent payment notification.

    Matching is deliberately strict: exact 12-digit UTR + exact amount + recipient UPI
    (when strict mode is enabled) + message date inside the configured lookback window.
    """
    expected_utr = re.sub(r"\s+", "", str(order["utr"] or "").upper())
    if not re.fullmatch(r"[A-Z0-9]{12,30}", expected_utr):
        return False, "Invalid order UTR"
    expected_amount = decimal_amount(order["topup_amount"] or order["amount"] or 0)
    upi_id = setting("upi_id", "").strip()
    for uid, msg, sender in messages:
        if not _sender_allowed(sender):
            continue
        if not _message_is_recent(msg):
            continue
        text = (
            f"Subject: {msg.get('Subject','')}\n"
            f"From: {msg.get('From','')}\n"
            f"To: {msg.get('To','')}\n"
            f"Cc: {msg.get('Cc','')}\n"
            f"{_email_text(msg)}"
        )
        normalized = re.sub(r"[^A-Z0-9]", "", text.upper())
        if expected_utr not in normalized:
            continue
        # The UTR is unique enough to bind the surrounding bank notification; exact
        # amount and recipient checks prevent generic email footer values from passing.
        if not _amount_matches_near_utr(text, expected_amount, expected_utr):
            continue
        if IMAP_REQUIRE_RECIPIENT_MATCH and not _recipient_matches(text, upi_id):
            continue
        return True, f"IMAP UID {uid}; sender={sender}; recent UTR + exact amount + recipient matched"
    return False, "No recent matching Gmail/IMAP payment record found"


async def auto_fulfill_verified_order(bot: Any, order_id: int) -> tuple[bool, str]:
    """Atomically approve a verified payment and allocate/deliver its product."""
    with db() as connection:
        connection.execute("BEGIN IMMEDIATE")
        order = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order or order["status"] != "pending":
            connection.rollback()
            return False, "Order is not awaiting automatic verification."
        expiry_value = order["expiry_at"] or (datetime.fromisoformat(order["created_at"]) + timedelta(minutes=20)).isoformat()
        if expiry_value:
            try:
                if utc_now() >= datetime.fromisoformat(expiry_value):
                    connection.execute("UPDATE orders SET status='expired', delivery_status='not_required' WHERE id=? AND status='pending'", (order_id,))
                    connection.commit()
                    return False, "Order expired before payment fulfillment."
            except (TypeError, ValueError):
                connection.rollback()
                return False, "Invalid order expiry timestamp."
        now = iso_now()
        if order["order_type"] == "reseller":
            connection.execute("UPDATE users SET is_reseller = 1, updated_at = ? WHERE id = ?", (now, order["user_id"]))
            connection.execute("UPDATE orders SET status='approved', approved_at=?, delivery_status='delivered' WHERE id=? AND status='pending'", (now, order_id))
            message = "🎉 <b>Reseller payment verified automatically</b>\n\nAapka reseller account active ho gaya hai."
        elif order["order_type"] == "balance":
            user = connection.execute("SELECT balance FROM users WHERE id = ?", (order["user_id"],)).fetchone()
            if not user:
                connection.rollback(); return False, "User account missing"
            before = float(user["balance"])
            after = round(before + float(order["topup_amount"]), 2)
            connection.execute("UPDATE users SET balance=?, updated_at=? WHERE id=?", (after, now, order["user_id"]))
            connection.execute("INSERT INTO wallet_transactions(user_id,order_id,type,amount,balance_before,balance_after,note,created_at) VALUES(?,?,?,?,?,?,?,?)", (order["user_id"], order_id, "deposit", order["topup_amount"], before, after, "Automatic Gmail/IMAP UPI verification", now))
            connection.execute("UPDATE orders SET status='approved', approved_at=?, delivery_status='delivered' WHERE id=? AND status='pending'", (now, order_id))
            message = f"✅ <b>Wallet deposit verified automatically</b>\n\nAmount: <b>{money(order['topup_amount'])}</b>\nNew balance: <b>{money(after)}</b>"
        else:
            plan = connection.execute("SELECT plans.*, products.channel_link, products.name AS product_name FROM plans JOIN products ON products.id=plans.product_id WHERE plans.id=?", (order["plan_id"],)).fetchone()
            key = connection.execute("SELECT * FROM stock_keys WHERE plan_id=? AND status='available' ORDER BY id LIMIT 1", (order["plan_id"],)).fetchone()
            if not plan:
                connection.rollback(); return False, "Product plan is unavailable"
            if not key:
                connection.execute("UPDATE orders SET status='payment_verified_stock_unavailable', delivery_status='failed', delivery_error=? WHERE id=? AND status='pending'", ("Payment verified but stock is unavailable", order_id))
                connection.commit()
                recovery_message = (
                    "✅ <b>Payment Verified</b>\n\n"
                    f"Order: <code>{safe(order['order_no'])}</code>\n"
                    "⚠️ Payment verify ho gaya hai, lekin is waqt stock unavailable hai. "
                    "Owner ko recovery alert mil gaya hai. Stock add hote hi admin retry karke delivery complete kar sakta hai."
                )
                try:
                    chat_id = order["pending_message_chat_id"]
                    message_id = order["pending_message_id"]
                    if chat_id and message_id:
                        await bot.edit_message_text(chat_id=int(chat_id), message_id=int(message_id), text=recovery_message, parse_mode=ParseMode.HTML)
                    else:
                        await bot.send_message(order["user_id"], recovery_message, parse_mode=ParseMode.HTML)
                except Exception:
                    logging.exception("Could not notify stock-unavailable user for %s", order["order_no"])
                try:
                    with db() as alert_db:
                        admin_ids = [int(r["user_id"]) for r in alert_db.execute("SELECT user_id FROM admins WHERE active=1").fetchall()]
                    for admin_id in admin_ids:
                        try:
                            await bot.send_message(admin_id, f"⚠️ <b>Payment verified but stock unavailable</b>\nOrder: <code>{safe(order['order_no'])}</code>\nUser: <code>{order['user_id']}</code>\nAmount: <b>{money(order['amount'])}</b>", parse_mode=ParseMode.HTML)
                        except Exception:
                            logging.debug("Stock recovery admin alert failed", exc_info=True)
                except Exception:
                    logging.debug("Could not load admins for stock recovery alert", exc_info=True)
                return True, "verified but stock unavailable; recovery required"
            claimed = connection.execute("UPDATE stock_keys SET status='sold', assigned_order_id=? WHERE id=? AND status='available'", (order_id, key["id"]))
            if claimed.rowcount != 1:
                connection.rollback(); return False, "Stock was claimed concurrently"
            expiry = utc_now() + timedelta(days=int(plan["days"]))
            connection.execute("UPDATE orders SET status='approved', approved_at=?, expiry_at=?, key_id=?, delivery_status='pending', delivery_attempts=delivery_attempts+1 WHERE id=? AND status='pending'", (now, expiry.isoformat(timespec="seconds"), key["id"], order_id))
            if order["coupon_code"]:
                updated = connection.execute("UPDATE coupons SET used_count=used_count+1 WHERE code=? AND active=1 AND (max_uses=0 OR used_count<max_uses)", (order["coupon_code"],))
                if updated.rowcount != 1:
                    connection.rollback(); return False, "Coupon usage limit changed before delivery"
            message = (
                "🎉 <b>Payment Verified — Automatic Delivery</b>\n\n"
                f"📦 Product: <b>{safe(plan['product_name'])}</b>\n"
                f"📌 Plan: <b>{safe(plan['name'])}</b>\n"
                f"🔑 Key: <code>{safe(key['key_value'])}</code>\n"
                f"⏳ Validity: <b>{plan['days']} Days</b>\n"
                f"🚀 Start Date: <b>{display_date(now)}</b>\n"
                f"📅 Expiry Date: <b>{display_date(expiry.isoformat())}</b>\n"
                + (f"\n📢 <a href=\"{safe(plan['channel_link'])}\">Open Product Channel</a>\n" if plan["channel_link"] else "")
                + "\nPayment automatically verified."
            )
            referral_rewarded, referral_reward, referral_referrer = reward_referral_for_order(connection, order["user_id"], order_id, now)
        connection.commit()
    try:
        chat_id = order["pending_message_chat_id"]
        message_id = order["pending_message_id"]
        edited = False
        if chat_id and message_id:
            try:
                await bot.edit_message_text(
                    chat_id=int(chat_id),
                    message_id=int(message_id),
                    text=message,
                    parse_mode=ParseMode.HTML,
                )
                edited = True
            except Exception:
                logging.debug("Could not edit pending payment message for %s", order["order_no"], exc_info=True)
        if not edited:
            await bot.send_message(order["user_id"], message, parse_mode=ParseMode.HTML)
        with db() as connection:
            connection.execute("UPDATE orders SET delivery_status='delivered', delivery_error='' WHERE id=?", (order_id,)); connection.commit()
        return True, "verified and delivered"
    except Exception as error:
        logging.exception("Automatic delivery failed for order %s", order_id)
        with db() as connection:
            connection.execute("UPDATE orders SET delivery_status='failed', delivery_error=? WHERE id=?", (str(error)[:500], order_id)); connection.commit()
        return True, "verified but delivery failed"


def imap_connection_check() -> tuple[bool, str]:
    """Non-destructive Gmail/IMAP connectivity check. Never logs the App Password."""
    if not IMAP_ENABLED:
        return False, "IMAP_ENABLED is disabled"
    if not IMAP_USERNAME or not IMAP_APP_PASSWORD:
        return False, "IMAP username/App Password is missing"
    mail = None
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, timeout=20)
        mail.login(IMAP_USERNAME, IMAP_APP_PASSWORD)
        typ, _ = mail.select(IMAP_FOLDER, readonly=True)
        if typ != "OK":
            return False, f"IMAP folder '{IMAP_FOLDER}' could not be opened"
        return True, f"Connected to {IMAP_HOST}:{IMAP_PORT}, folder={IMAP_FOLDER}"
    except imaplib.IMAP4.error as exc:
        return False, f"Gmail/IMAP authentication or protocol error: {exc}"
    except (OSError, TimeoutError) as exc:
        return False, f"Gmail/IMAP network error: {exc}"
    finally:
        if mail is not None:
            try:
                mail.logout()
            except Exception:
                pass


async def gateway_callback_fulfillment_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        with db() as connection:
            orders=connection.execute("SELECT id,order_no FROM orders WHERE status='pending' AND payment_method='gateway' ORDER BY id ASC LIMIT 25").fetchall()
        for order in orders:
            try:
                await auto_fulfill_verified_order(context.application.bot, int(order["id"]))
            except Exception:
                logging.exception("Gateway fulfillment failed for %s", order["order_no"])
    except Exception:
        logging.exception("Gateway fulfillment job failed")


async def auto_payment_verification_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    if not (IMAP_ENABLED and IMAP_USERNAME and IMAP_APP_PASSWORD and IMAP_ALLOWED_SENDERS):
        return
    try:
        set_setting("auto_payment_last_run", iso_now())
        with db() as connection:
            rows = connection.execute(
                "SELECT * FROM orders WHERE status='pending' AND utr!='' ORDER BY id ASC LIMIT 50"
            ).fetchall()
        utr_map = {}
        valid_orders = []
        for order in rows:
            utr = re.sub(r"\s+", "", str(order["utr"] or "")).upper()
            if re.fullmatch(r"[A-Z0-9]{12,30}", utr):
                utr_map[utr] = order
                valid_orders.append((order, utr))
        messages_map = await asyncio.to_thread(_fetch_recent_imap_messages_for_utrs, list(utr_map))
        for order, utr in valid_orders:
            messages = messages_map.get(utr, [])
            matched, reason = _match_payment_email(order, messages)
            if not matched:
                logging.info("Payment not matched yet order=%s reason=%s", order["order_no"], reason)
                continue
            event_match = re.search(r"IMAP UID (\d+)", reason)
            event_uid = event_match.group(1) if event_match else None
            if not event_uid:
                continue
            with db() as connection:
                try:
                    connection.execute(
                        "INSERT INTO payment_events(provider,provider_event_id,order_id,event_type,received_at,details) VALUES(?,?,?,?,?,?)",
                        ("gmail_imap", event_uid, int(order["id"]), "payment_verified", iso_now(), reason),
                    )
                    connection.commit()
                except sqlite3.IntegrityError:
                    connection.rollback()
                    logging.info("Payment event already processed uid=%s order=%s", event_uid, order["order_no"])
                    continue
            try:
                await auto_fulfill_verified_order(context.application.bot, int(order["id"]))
            except Exception:
                logging.exception("Automatic verification fulfillment failed for %s", order["order_no"])
                with db() as connection:
                    connection.execute("UPDATE payment_events SET details=? WHERE provider=? AND provider_event_id=?", ("Fulfillment exception: " + reason, "gmail_imap", event_uid))
                    connection.commit()
    except Exception as error:
        set_setting("auto_payment_last_error", str(error)[:500])
        logging.exception("Automatic Gmail/IMAP verification cycle failed")



def deposit_keypad_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [button("💰 1", "deposit:d:1"), button("💰 2", "deposit:d:2"), button("💰 3", "deposit:d:3")],
        [button("💰 4", "deposit:d:4"), button("💰 5", "deposit:d:5"), button("💰 6", "deposit:d:6")],
        [button("💰 7", "deposit:d:7"), button("💰 8", "deposit:d:8"), button("💰 9", "deposit:d:9")],
        [button("❌ Delete", "deposit:delete"), button("💰 0", "deposit:d:0"), button("✅ Confirm", "deposit:confirm")],
        [button("⬅️ Back", "balance")],
    ])


async def show_deposit_keypad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    raw = str(context.user_data.get("deposit_amount", ""))
    amount_text = raw or "0"
    await edit_or_send(
        update,
        "💸 <b>CUSTOM AMOUNT</b>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💰 <b>Min: ₹10 | Max: ₹50,000</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 <b>Amount: {money(amount_text)}</b>\n\n"
        "Number buttons se amount select karein — chat mein amount type karne ki zaroorat nahi.",
        deposit_keypad_markup(),
    )


async def confirm_deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_payment_configured(update, context):
        return
    raw = str(context.user_data.get("deposit_amount", ""))
    amount = parse_amount(raw, minimum=10, maximum=50_000) if raw else None
    if amount is None:
        await edit_or_send(update, "⚠️ Deposit amount ₹10 se ₹50,000 ke beech select karein.", deposit_keypad_markup())
        return
    order_id = await create_balance_order(update.effective_user.id, amount)
    context.user_data["current_order_id"] = order_id
    context.user_data["flow"] = "payment_wait"
    context.user_data["payment_back_callback"] = "balance"
    with db() as connection:
        order = connection.execute("SELECT order_no FROM orders WHERE id = ?", (order_id,)).fetchone()
    await send_payment_screen(update, context, order["order_no"], amount, "Wallet Deposit", "balance")


async def wallet_screen(update: Update) -> None:
    with db() as connection:
        user = connection.execute(
            "SELECT balance FROM users WHERE id = ?", (update.effective_user.id,)
        ).fetchone()
        recent = connection.execute(
            "SELECT type, amount, balance_after, created_at FROM wallet_transactions "
            "WHERE user_id = ? ORDER BY id DESC LIMIT 5",
            (update.effective_user.id,),
        ).fetchall()
    balance = float(user["balance"]) if user else 0
    lines = [
        "💰 <b>Wallet</b>",
        "",
        f"Available balance: <b>{money(balance)}</b>",
        "",
        "Use your wallet balance to buy an in-stock product instantly.",
    ]
    if recent:
        lines.extend(["", "<b>Recent wallet activity</b>"])
        for row in recent:
            if row["type"] in {"deposit", "admin_credit", "referral_reward"}:
                sign = "+"
            else:
                sign = "-"
            lines.append(
                f"{sign}{money(row['amount'])} • {row['type'].title()} • "
                f"{display_date(row['created_at'])}"
            )
    await edit_or_send(
        update,
        "\n".join(lines),
        InlineKeyboardMarkup(
            [
                [button("➕ Deposit via Gateway", "deposit")],
                [button("🛒 Shop with Wallet", "shop")],
                [button("‹  Back to Main Menu", "home")],
            ]
        ),
    )


async def wallet_purchase(
    update: Update, context: ContextTypes.DEFAULT_TYPE, plan_id: int
) -> None:
    result = plan_details(plan_id, update.effective_user.id)
    if not result:
        await edit_or_send(update, "Plan available nahi hai.", back_home())
        return
    plan, reseller = result
    if plan["maintenance_mode"]:
        await edit_or_send(update, "🚧 Ye product abhi maintenance mein hai. Wallet purchase temporarily disabled hai.", back_button(f"prod:{plan['product_id']}"))
        return
    original = float(plan["reseller_price"] if reseller else plan["customer_price"])
    coupon_result = calculate_coupon(str(context.user_data.get("coupon", "")), original)
    if coupon_result is None:
        await edit_or_send(update, "Coupon invalid ya expire ho gaya. Dobara try karein.", back_home())
        return
    amount, coupon_code = coupon_result
    now = iso_now()
    try:
        with db() as connection:
            connection.execute("BEGIN IMMEDIATE")
            user = connection.execute(
                "SELECT balance FROM users WHERE id = ?", (update.effective_user.id,)
            ).fetchone()
            key = connection.execute(
                "SELECT * FROM stock_keys WHERE plan_id = ? AND status = 'available' "
                "ORDER BY id LIMIT 1",
                (plan_id,),
            ).fetchone()
            if not user or float(user["balance"]) < amount:
                connection.rollback()
                await edit_or_send(
                    update,
                    f"Wallet balance kam hai.\nRequired: <b>{money(amount)}</b>\n"
                    f"Available: <b>{money(user['balance'] if user else 0)}</b>",
                    InlineKeyboardMarkup(
                        [
                            [button("➕ Deposit via Gateway", "deposit")],
                            [button("‹  Back to Plan", f"plan:{plan_id}")],
                        ]
                    ),
                )
                return
            if not key:
                connection.rollback()
                await edit_or_send(update, "Is plan ka stock abhi khatam hai.", back_home())
                return
            claimed = connection.execute(
                "UPDATE stock_keys SET status = 'sold', assigned_order_id = ? "
                "WHERE id = ? AND status = 'available'",
                (None, key["id"]),
            )
            if claimed.rowcount != 1:
                connection.rollback()
                await edit_or_send(update, "Stock abhi kisi aur order ne le liya. Dobara try karein.", back_home())
                return
            order_no = f"WAL-{datetime.now(TIMEZONE).strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"
            cursor = connection.execute(
                "INSERT INTO orders(order_no, user_id, plan_id, order_type, amount, original_amount, "
                "coupon_code, payment_method, status, approved_at, expiry_at, key_id, delivery_status, "
                "delivery_attempts, created_at) VALUES (?, ?, ?, 'product', ?, ?, ?, 'wallet', 'approved', ?, ?, ?, "
                "'pending', 1, ?)",
                (
                    order_no,
                    update.effective_user.id,
                    plan_id,
                    amount,
                    original,
                    coupon_code,
                    now,
                    (utc_now() + timedelta(days=int(plan["days"]))).isoformat(timespec="seconds"),
                    key["id"],
                    now,
                ),
            )
            order_id = int(cursor.lastrowid)
            connection.execute(
                "UPDATE stock_keys SET assigned_order_id = ? WHERE id = ?",
                (order_id, key["id"]),
            )
            after = round(float(user["balance"]) - amount, 2)
            connection.execute(
                "UPDATE users SET balance = ?, updated_at = ? WHERE id = ?",
                (after, now, update.effective_user.id),
            )
            connection.execute(
                "INSERT INTO wallet_transactions(user_id, order_id, type, amount, balance_before, balance_after, note, created_at) "
                "VALUES (?, ?, 'purchase', ?, ?, ?, 'Wallet product purchase', ?)",
                (update.effective_user.id, order_id, amount, user["balance"], after, now),
            )
            if coupon_code:
                coupon_update = connection.execute(
                    "UPDATE coupons SET used_count = used_count + 1 "
                    "WHERE code = ? AND active = 1 AND "
                    "(max_uses = 0 OR used_count < max_uses) AND "
                    "(expires_at IS NULL OR expires_at >= ?)",
                    (coupon_code, iso_now()),
                )
                if coupon_update.rowcount != 1:
                    connection.rollback()
                    await edit_or_send(update, "Coupon ab valid nahi hai. Dobara try karein.", back_home())
                    return
            referral_rewarded, referral_reward, referral_referrer = reward_referral_for_order(connection, update.effective_user.id, order_id, now)
            connection.commit()
    except sqlite3.IntegrityError:
        await edit_or_send(update, "Wallet order create nahi ho saka. Dobara try karein.", back_home())
        return
    context.user_data.pop("coupon", None)
    expiry = utc_now() + timedelta(days=int(plan["days"]))
    message = (
        "🎉 <b>Wallet Purchase Successful</b>\n\n"
        f"📦 Product: <b>{safe(plan['product_name'])}</b>\n"
        f"📌 Plan: <b>{safe(plan['name'])}</b>\n"
        f"🔑 Key: <code>{safe(key['key_value'])}</code>\n"
        f"⏳ Validity: <b>{plan['days']} Days</b>\n"
        f"📅 Expiry: <b>{display_date(expiry.isoformat())}</b>\n"
        + (f"📢 <a href=\"{safe(plan['channel_link'])}\">Open Product Channel</a>\n" if plan["channel_link"] else "")
        + f"💰 Remaining wallet: <b>{money(after)}</b>"
    )
    try:
        await update.get_bot().send_message(
            update.effective_user.id, message, parse_mode=ParseMode.HTML
        )
        with db() as connection:
            connection.execute(
                "UPDATE orders SET delivery_status = 'delivered' WHERE order_no = ?",
                (order_no,),
            )
            connection.commit()
    except Exception:
        logging.exception("Wallet delivery failed for %s", order_no)
    await edit_or_send(update, "✅ Wallet se purchase complete ho gaya.", main_keyboard(update.effective_user.id))


async def profile(update: Update) -> None:
    user_id = int(update.effective_user.id)
    with db() as connection:
        user = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        orders = connection.execute(
            "SELECT COUNT(*) AS count FROM orders WHERE user_id = ? AND status = 'approved'",
            (user_id,),
        ).fetchone()["count"]
        referrals = connection.execute(
            "SELECT COUNT(*) AS count FROM referrals WHERE referrer_id = ? AND status = 'qualified'",
            (user_id,),
        ).fetchone()["count"]
    role = ("RESELLER" if user and user["is_reseller"] else "USER")
    role_labels = {
        "hi": {"USER":"यूज़र", "RESELLER":"रीसेलर"}, "bn":{"USER":"ইউজার", "RESELLER":"রিসেলার"},
        "mr":{"USER":"यूजर", "RESELLER":"रिसेलर"}, "ta":{"USER":"பயனர்", "RESELLER":"மறுவிற்பனையாளர்"},
        "te":{"USER":"వినియోగదారు", "RESELLER":"రీ-సెల్లర్"}, "gu":{"USER":"યુઝર", "RESELLER":"રીસેલર"},
        "kn":{"USER":"ಬಳಕೆದಾರ", "RESELLER":"ಮರುಮಾರಾಟಗಾರ"}, "ml":{"USER":"യൂസർ", "RESELLER":"റീസെല്ലർ"},
        "pa":{"USER":"ਯੂਜ਼ਰ", "RESELLER":"ਰੀਸੈਲਰ"}, "or":{"USER":"ୟୁଜର୍", "RESELLER":"ରିସେଲର୍"},
        "ur":{"USER":"صارف", "RESELLER":"ری سیلر"}, "as":{"USER":"ইউজাৰ", "RESELLER":"ৰিচেলাৰ"},
    }
    lang = user_language(user_id)
    role = role_labels.get(lang, {}).get(role, role)
    verified = tr(user_id, "verified") if user and user["phone_verified"] else tr(user_id, "not_verified")
    name = safe(user["first_name"] if user else update.effective_user.first_name)
    username = f"@{safe(user['username'])}" if user and user["username"] else "—"
    joined = "—"
    if user and user["created_at"]:
        try:
            joined = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00")).astimezone(TIMEZONE).strftime("%d-%m-%Y  %H:%M")
        except ValueError:
            joined = str(user["created_at"])
    text = (
        f"{tr(user_id, 'profile_title')}\n\n"
        f"╭━━ <b>{tr(user_id, 'name')}</b> ━━╮\n"
        f"│ 👤 {name}\n"
        f"│ 🔖 {username}\n"
        f"╰━━━━━━━━━━━━╯\n\n"
        f"🆔 {tr(user_id, 'user_id')}: <code>{user_id}</code>\n"
        f"📅 {tr(user_id, 'joined')}: <b>{joined}</b>\n"
        f"🎭 {tr(user_id, 'profile_role')}: <b>{role}</b>\n"
        f"🛡️ {tr(user_id, 'profile_account')}: <b>{verified}</b>\n"
        f"💰 {tr(user_id, 'profile_balance')}: <b>{money(user['balance'] if user else 0)}</b>\n"
        f"📦 {tr(user_id, 'completed_orders_label')}: <b>{orders}</b>\n"
        f"🤝 {tr(user_id, 'successful')}: <b>{referrals}</b>\n\n"
        f"━━━━━━━━━━━━━━━━\n✨ <b>{tr(user_id, 'profile_overview')}</b>\n"
        f"{tr(user_id, 'profile_overview_text')}"
    )
    await edit_or_send(update, text, back_home())


async def history(update: Update) -> None:
    with db() as connection:
        rows = connection.execute(
            """
            SELECT orders.*, products.name AS product_name, plans.name AS plan_name,
                   plans.days, stock_keys.key_value
            FROM orders
            LEFT JOIN plans ON plans.id = orders.plan_id
            LEFT JOIN products ON products.id = plans.product_id
            LEFT JOIN stock_keys ON stock_keys.id = orders.key_id
            WHERE orders.user_id = ? ORDER BY orders.id DESC LIMIT 15
            """,
            (update.effective_user.id,),
        ).fetchall()
    if not rows:
        await edit_or_send(update, "📄 Abhi koi order history nahi hai.", back_home())
        return
    lines = ["📄 <b>All History</b>\n"]
    keyboard = []
    for row in rows:
        item = safe(row["product_name"] or row["order_type"].title())
        plan = f" • {safe(row['plan_name'])}" if row["plan_name"] else ""
        lines.append(
            f"<b>{row['order_no']}</b> — {item}{plan}\n"
            f"{money(row['amount'])} • {row['status'].upper()} • {display_date(row['created_at'])}"
        )
        if row["status"] == "approved" and row["key_value"]:
            lines.append(f"Key: <code>{safe(row['key_value'])}</code>\nExpiry: {display_date(row['expiry_at'])}")
        keyboard.append([button(f"🔎 Track {row['order_no']}", f"track:{row['id']}")])
    keyboard.append([button("‹ Main Menu", "home")])
    await edit_or_send(update, "\n".join(lines), InlineKeyboardMarkup(keyboard))


def order_status_label(status: str, delivery_status: str = "") -> str:
    labels = {
        "awaiting_utr": "⏳ Waiting for Gateway Payment",
        "payment_wait": "⏳ Waiting for Gateway Payment",
        "pending": "🔎 Payment Submitted — Automatic Verification",
        "approved": "📦 Payment Verified",
        "rejected": "❌ Payment Rejected",
        "expired": "⌛ Payment Session Expired",
        "cancelled": "🚫 Cancelled",
    }
    if status == "approved" and delivery_status == "delivered":
        return "✅ Completed — Delivered"
    if status == "approved" and delivery_status == "failed":
        return "⚠️ Payment Verified — Delivery Retry Pending"
    return labels.get(status, status.title())


async def track_order(update: Update, order_id: int) -> None:
    with db() as connection:
        row = connection.execute(
            "SELECT orders.*, products.name AS product_name, plans.name AS plan_name, plans.days, stock_keys.key_value "
            "FROM orders LEFT JOIN plans ON plans.id=orders.plan_id LEFT JOIN products ON products.id=plans.product_id "
            "LEFT JOIN stock_keys ON stock_keys.id=orders.key_id WHERE orders.id=? AND orders.user_id=?",
            (order_id, update.effective_user.id),
        ).fetchone()
    if not row:
        await edit_or_send(update, "❌ Order nahi mila.", back_home()); return
    text=(
        f"🔎 <b>Order Tracking</b>\n\nOrder: <code>{safe(row['order_no'])}</code>\n"
        f"📦 Product: <b>{safe(row['product_name'] or row['order_type'].title())}</b>\n"
        + (f"📌 Plan: <b>{safe(row['plan_name'])}</b>\n" if row['plan_name'] else "")
        + f"💰 Amount: <b>{money(row['amount'])}</b>\n"
        f"📍 Status: <b>{order_status_label(row['status'], row['delivery_status'])}</b>\n"
        f"🕒 Created: {display_date(row['created_at'])}\n"
        + (f"📅 Approved: {display_date(row['approved_at'])}\n" if row['approved_at'] else "")
        + (f"🔑 Key: <code>{safe(row['key_value'])}</code>\n" if row['key_value'] and row['status']=='approved' else "")
        + (f"⏳ Expiry: {display_date(row['expiry_at'])}\n" if row['expiry_at'] else "")
    )
    await edit_or_send(update, text, InlineKeyboardMarkup([[button("‹ My Orders", "history")],[button("‹ Main Menu", "home")]]))




async def link_screen(update: Update, key: str, title: str) -> None:
    url = setting(key)
    if not url or not valid_url(url):
        await edit_or_send(update, f"{title} link admin ne abhi set nahi kiya.", back_home())
        return
    await edit_or_send(
        update,
        f"{safe(title)} ke liye neeche button dabayein.",
        InlineKeyboardMarkup(
            [[InlineKeyboardButton(title, url=url)], [button("‹  Back to Main Menu", "home")]]
        ),
    )


# ---------------------------------------------------------------------------
# Admin views and actions
# ---------------------------------------------------------------------------

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """The Telegram bot has no in-chat admin panel. Admin controls live in the web Control Center."""
    if update.effective_message:
        await update.effective_message.reply_text(
            "🛡️ <b>Admin controls are available in the SHIVAM BOT BUILDER.</b>\n\n"
            "This Telegram bot is customer-facing only: use /start to shop and manage your customer account.",
            parse_mode=ParseMode.HTML,
        )


async def admin_users(update: Update, query_text: str = "") -> None:
    if query_text:
        q = f"%{query_text.lower()}%"
        with db() as connection:
            rows = connection.execute(
                "SELECT id, username, first_name, balance, is_reseller, active, created_at "
                "FROM users WHERE CAST(id AS TEXT) LIKE ? OR lower(username) LIKE ? OR lower(first_name) LIKE ? "
                "ORDER BY id DESC LIMIT 15", (f"%{query_text}%", q, q)
            ).fetchall()
    else:
        with db() as connection:
            rows = connection.execute(
                "SELECT id, username, first_name, balance, is_reseller, active, created_at "
                "FROM users ORDER BY id DESC LIMIT 15"
            ).fetchall()
    if not rows:
        await edit_or_send(update, "👥 Koi user nahi mila.", admin_back())
        return
    lines=["👥 <b>User Manager</b>\n"]
    keyboard=[]
    for r in rows:
        name=safe(r['first_name'] or r['username'] or r['id'])
        role="Reseller" if r['is_reseller'] else "User"
        status="🟢" if r['active'] else "🔴"
        lines.append(f"{status} <code>{r['id']}</code> • {name} • {role} • {money(r['balance'])}")
        if int(r['id']) != int(OWNER_USER_ID or -1):
            action="userban" if r['active'] else "userunban"
            label="🚫 Ban" if r['active'] else "✅ Unban"
            keyboard.append([button(f"{label} {r['id']}", f"{action}:{r['id']}")])
    keyboard.append([button("🔎 Search User", "flow:user_search"), button("⬅️ Admin Panel", "admin:main")])
    await edit_or_send(update, "\n".join(lines), InlineKeyboardMarkup(keyboard))


async def admin_stock(update: Update) -> None:
    with db() as connection:
        rows=connection.execute(
            "SELECT plans.id, products.name AS product_name, plans.name AS plan_name, "
            "SUM(CASE WHEN stock_keys.status='available' THEN 1 ELSE 0 END) AS available, "
            "SUM(CASE WHEN stock_keys.status='sold' THEN 1 ELSE 0 END) AS sold "
            "FROM plans JOIN products ON products.id=plans.product_id "
            "LEFT JOIN stock_keys ON stock_keys.plan_id=plans.id "
            "GROUP BY plans.id ORDER BY available ASC, plans.id DESC"
        ).fetchall()
    if not rows:
        await edit_or_send(update,"📦 Stock empty hai.",admin_back()); return
    lines=["📦 <b>Stock Monitor</b>\n"]
    threshold=int(setting("low_stock_threshold","5") or 5)
    for r in rows:
        flag=" ⚠️ LOW" if int(r['available'] or 0) <= threshold else ""
        lines.append(f"<b>{safe(r['product_name'])}</b> • {safe(r['plan_name'])}\nAvailable: <b>{r['available']}</b> • Sold: {r['sold']}{flag}")
    await edit_or_send(update,"\n".join(lines),InlineKeyboardMarkup([[button("➕ Add Stock","flow:add_key")],[button("⚙️ Set Low-Stock Alert","flow:low_stock"),button("⬅️ Admin Panel","admin:main")]]))


async def admin_coupons(update: Update) -> None:
    with db() as connection:
        rows=connection.execute("SELECT * FROM coupons ORDER BY id DESC LIMIT 30").fetchall()
    lines=["🏷️ <b>Coupon Manager</b>\n"]
    keyboard=[]
    for r in rows:
        expiry=display_date(r['expires_at']) if r['expires_at'] else "Never"
        status="ON" if r['active'] else "OFF"
        lines.append(f"<code>{safe(r['code'])}</code> • {r['discount_value']}{'%' if r['discount_type']=='percent' else '₹'} • {r['used_count']}/{r['max_uses'] or '∞'} • {status} • {expiry}")
        keyboard.append([button(f"{'⛔ Disable' if r['active'] else '✅ Enable'} {r['code']}",f"coupon_toggle:{r['id']}")])
    keyboard += [[button("➕ Add Coupon","flow:add_coupon")],[button("⬅️ Admin Panel","admin:main")]]
    await edit_or_send(update,"\n".join(lines),InlineKeyboardMarkup(keyboard))


async def admin_order_search(update: Update, text: str) -> None:
    q=f"%{text}%"
    with db() as connection:
        rows=connection.execute(
            "SELECT orders.*, users.username, users.first_name, products.name AS product_name, plans.name AS plan_name "
            "FROM orders JOIN users ON users.id=orders.user_id LEFT JOIN plans ON plans.id=orders.plan_id "
            "LEFT JOIN products ON products.id=plans.product_id "
            "WHERE lower(orders.order_no) LIKE lower(?) OR CAST(orders.user_id AS TEXT) LIKE ? OR orders.utr LIKE ? "
            "ORDER BY orders.id DESC LIMIT 15",(q,q,q)
        ).fetchall()
    if not rows:
        await edit_or_send(update,"🔎 Order nahi mila.",admin_back()); return
    lines=["🔎 <b>Order Search</b>\n"]
    for r in rows:
        lines.append(f"<b>{safe(r['order_no'])}</b> • {r['status'].upper()}\nUser: <code>{r['user_id']}</code> • {safe(r['product_name'] or r['order_type'])}\nAmount: {money(r['amount'])} • UTR: <code>{safe(r['utr'] or '—')}</code>")
    await edit_or_send(update,"\n".join(lines),admin_back())


async def admin_failed_deliveries(update: Update) -> None:
    with db() as connection:
        rows = connection.execute(
            "SELECT id, order_no, user_id, order_type, amount, delivery_error, delivery_attempts FROM orders "
            "WHERE (status = 'approved' AND delivery_status = 'failed') "
            "OR status = 'payment_verified_stock_unavailable' "
            "ORDER BY id DESC LIMIT 25"
        ).fetchall()
    if not rows:
        await edit_or_send(update, "✅ Koi failed delivery nahi hai.", admin_back())
        return
    lines = ["🔁 <b>Failed Deliveries</b>\n", "Payment verified tha, lekin Telegram delivery fail hui thi. Retry se dobara send karein."]
    keyboard = []
    for row in rows:
        lines.append(
            f"\n<b>{safe(row['order_no'])}</b> • {safe(row['order_type'])}\n"
            f"User: <code>{row['user_id']}</code> • Amount: <b>{money(row['amount'])}</b>\n"
            f"Attempts: {row['delivery_attempts']} • Error: <code>{safe(row['delivery_error'] or 'Unknown')}</code>"
        )
        keyboard.append([button(f"🔁 Retry {row['order_no']}", f"retrydelivery:{row['id']}")])
    keyboard.append([button("⬅️ Admin Panel", "admin:main")])
    await edit_or_send(update, "\n".join(lines), InlineKeyboardMarkup(keyboard))


async def retry_delivery(update: Update, order_id: int) -> None:
    with db() as connection:
        order = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order or not ((order["status"] == "approved" and order["delivery_status"] == "failed") or order["status"] == "payment_verified_stock_unavailable"):
            await edit_or_send(update, "⚠️ Delivery retry available nahi hai.", admin_back())
            return
        message = None
        if order["order_type"] == "balance":
            message = f"✅ Aapka wallet deposit {money(order['topup_amount'])} automatically verify ho gaya hai.\nNew balance check karne ke liye Wallet open karein."
        elif order["order_type"] == "reseller":
            message = "🎉 <b>Reseller approved</b>\n\nAapka reseller account active ho gaya hai. Ab Shop Now par reseller prices milengi."
        else:
            plan = connection.execute(
                "SELECT plans.*, products.channel_link, products.name AS product_name FROM plans JOIN products ON products.id = plans.product_id WHERE plans.id = ?",
                (order["plan_id"],),
            ).fetchone()
            key = connection.execute("SELECT key_value, id FROM stock_keys WHERE id = ?", (order["key_id"],)).fetchone() if order["key_id"] else None
            if not plan:
                await edit_or_send(update, "❌ Delivery data incomplete hai; order manually inspect karein.", admin_back())
                return
            if not key:
                key = connection.execute("SELECT id, key_value FROM stock_keys WHERE plan_id=? AND status='available' ORDER BY id LIMIT 1", (order["plan_id"],)).fetchone()
                if not key:
                    await edit_or_send(update, "⏳ Payment verified hai, lekin abhi stock available nahi hai.", admin_back())
                    return
                claimed = connection.execute("UPDATE stock_keys SET status='sold', assigned_order_id=? WHERE id=? AND status='available'", (order_id, key["id"]))
                if claimed.rowcount != 1:
                    await edit_or_send(update, "⚠️ Stock concurrently claim ho gaya. Dobara retry karein.", admin_back())
                    return
                expiry_dt = utc_now() + timedelta(days=int(plan["days"]))
                connection.execute("UPDATE orders SET status='approved', key_id=?, expiry_at=?, delivery_status='failed' WHERE id=?", (key["id"], expiry_dt.isoformat(timespec='seconds'), order_id))
            expiry = (expiry_dt.isoformat(timespec="seconds") if "expiry_dt" in locals() else order["expiry_at"]) or "—"
            message = (
                "🎉 <b>Payment Verified — Key Delivery Retry</b>\n\n"
                f"📦 Product: <b>{safe(plan['product_name'])}</b>\n"
                f"📌 Plan: <b>{safe(plan['name'])}</b>\n"
                f"🔑 Key: <code>{safe(key['key_value'])}</code>\n"
                f"⏳ Validity: <b>{plan['days']} Days</b>\n"
                f"📅 Expiry Date: <b>{display_date(expiry)}</b>\n"
                + (f"📢 <a href=\"{safe(plan['channel_link'])}\">Open Product Channel</a>\n" if plan["channel_link"] else "")
            )
        connection.execute("UPDATE orders SET delivery_attempts = delivery_attempts + 1 WHERE id = ?", (order_id,))
        connection.commit()
    try:
        await update.get_bot().send_message(order["user_id"], message, parse_mode=ParseMode.HTML)
    except Exception as error:
        with db() as connection:
            connection.execute("UPDATE orders SET delivery_error = ? WHERE id = ?", (str(error)[:500], order_id))
            connection.commit()
        await edit_or_send(update, "❌ Retry bhi fail ho gaya. Telegram delivery error check karein.", admin_back())
        return
    with db() as connection:
        connection.execute("UPDATE orders SET delivery_status = 'delivered', delivery_error = '' WHERE id = ?", (order_id,))
        connection.commit()
    await edit_or_send(update, f"✅ {safe(order['order_no'])} delivery successfully retry ho gayi.", admin_back())


async def admin_maintenance(update: Update) -> None:
    enabled=setting("maintenance_mode","0")=="1"
    state="ON 🚧" if enabled else "OFF ✅"
    await edit_or_send(update,f"🚧 <b>Maintenance Mode</b>\n\nCurrent status: <b>{state}</b>\n\nON karne par normal users ko shopping/payment flows se roka jayega. Owner/admin access chalta rahega.",InlineKeyboardMarkup([[button("🔴 Turn OFF" if enabled else "🟢 Turn ON", "maintenance:toggle")],[button("⬅️ Admin Panel","admin:main")]]))


async def pending_orders(update: Update, reseller_only: bool = False) -> None:
    query = """
        SELECT orders.*, users.username, users.first_name, products.name AS product_name,
               plans.name AS plan_name, plans.days
        FROM orders JOIN users ON users.id = orders.user_id
        LEFT JOIN plans ON plans.id = orders.plan_id
        LEFT JOIN products ON products.id = plans.product_id
        WHERE orders.status = 'pending'
    """
    if reseller_only:
        query += " AND orders.order_type = 'reseller'"
    query += " ORDER BY orders.id ASC LIMIT 25"
    with db() as connection:
        rows = connection.execute(query).fetchall()
    if not rows:
        await edit_or_send(update, "✅ Koi automatic verification queue pending nahi hai.", admin_keyboard())
        return
    lines = ["🤖 <b>Automatic Verification Queue</b>\n", "Manual payment approval disabled hai. System Gmail/IMAP match ke baad automatically process karega.\n"]
    for row in rows:
        customer = f"@{safe(row['username'])}" if row["username"] else safe(row["first_name"])
        item = safe(row["product_name"] or row["order_type"].title())
        if row["plan_name"]:
            item += f" • {safe(row['plan_name'])}"
        lines.append(f"<b>{safe(row['order_no'])}</b>\n{customer} • {item}\nAmount: <b>{money(row['amount'])}</b> • UTR: <code>{safe(row['utr'] or '—')}</code>")
    await edit_or_send(update, "\n\n".join(lines), admin_keyboard())




async def admin_catalog(update: Update) -> None:
    with db() as connection:
        categories = connection.execute(
            "SELECT id, name FROM categories WHERE active = 1 ORDER BY name"
        ).fetchall()
        products = connection.execute(
            "SELECT id, name, channel_link, maintenance_mode FROM products WHERE active = 1 ORDER BY id DESC LIMIT 50"
        ).fetchall()
        plans = connection.execute(
            "SELECT plans.id, products.name AS product_name, plans.name, plans.days, "
            "plans.customer_price, plans.reseller_price, "
            "(SELECT COUNT(*) FROM stock_keys WHERE stock_keys.plan_id = plans.id "
            "AND stock_keys.status = 'available') AS stock "
            "FROM plans JOIN products ON products.id = plans.product_id "
            "WHERE plans.active = 1 ORDER BY products.name, plans.days"
        ).fetchall()
    lines = ["📦 <b>Catalog Manager</b>\n"]
    if categories:
        lines.append("Categories: " + ", ".join(f"{row['id']}={safe(row['name'])}" for row in categories))
    else:
        lines.append("Abhi category nahi hai.")
    if products:
        lines.append("\nProducts:\n" + "\n".join(
            f"{row['id']}. <b>{safe(row['name'])}</b>"
            + (" • 🚧 MAINTENANCE" if row["maintenance_mode"] else " • 🟢 LIVE")
            + (f" • 📢 {safe(row['channel_link'])}" if row['channel_link'] else "")
            for row in products
        ))
    else:
        lines.append("\nAbhi product nahi hai.")
    if plans:
        lines.append(
            "\nPlans / IDs for adding keys:\n"
            + "\n".join(
                f"Plan ID {row['id']}: {safe(row['product_name'])} • {safe(row['name'])} • "
                f"{row['days']} Days • Stock {row['stock']}"
                for row in plans
            )
        )
    keyboard = [
        [button("➕ Add Category", "flow:add_category"), button("➕ Add Product", "flow:add_product")],
        [button("🔑 Add Keys", "flow:add_key"), button("🚧 Product Maintenance", "admin:product_maintenance")],
        [button("🗑️ Delete Product", "flow:delete_product")],
    ]
    keyboard.extend(
        [button(f"Edit Plan {row['id']}", f"editplan:{row['id']}")] for row in plans
    )
    keyboard.append([button("⬅️ Admin Panel", "admin:main")])
    await edit_or_send(update, "\n".join(lines), InlineKeyboardMarkup(keyboard))


async def reseller_panel(update: Update) -> None:
    fee = setting("reseller_join_fee", "0")
    with db() as connection:
        pending = connection.execute(
            "SELECT COUNT(*) AS count FROM orders WHERE order_type = 'reseller' AND status = 'pending'"
        ).fetchone()["count"]
        total = connection.execute(
            "SELECT COUNT(*) AS count FROM users WHERE is_reseller = 1 AND active = 1"
        ).fetchone()["count"]
    text = (
        "🤝 <b>Reseller Management</b>\n\n"
        f"Joining fee: <b>{money(fee)}</b>\n"
        f"Pending applications: <b>{pending}</b>\n"
        f"Active resellers: <b>{total}</b>"
    )
    keyboard = [
        [button("💰 Set Joining Fee", "flow:set_join_fee")],
        [button("🔎 Verification Queue", "admin:reseller_pending")],
        [button("🏷️ Set Reseller Prices", "admin:reseller_prices")],
        [button("👥 Manage Reseller Accounts", "admin:reseller_accounts")],
        [button("⬅️ Admin Panel", "admin:main")],
    ]
    await edit_or_send(update, text, InlineKeyboardMarkup(keyboard))


async def reseller_prices(update: Update) -> None:
    with db() as connection:
        rows = connection.execute(
            "SELECT plans.id, products.name AS product_name, plans.name, plans.days, "
            "plans.customer_price, plans.reseller_price FROM plans "
            "JOIN products ON products.id = plans.product_id WHERE plans.active = 1 "
            "ORDER BY products.name, plans.days"
        ).fetchall()
    if not rows:
        await edit_or_send(update, "Pehle product aur plan add karein.", reseller_back())
        return
    lines = ["🏷️ <b>Reseller Prices</b>\n"]
    keyboard = []
    for row in rows:
        lines.append(
            f"{safe(row['product_name'])} • {safe(row['name'])} • {row['days']} Days\n"
            f"Customer: {money(row['customer_price'])} | Reseller: {money(row['reseller_price'])}"
        )
        keyboard.append([button(f"Edit {safe(row['product_name'])} • {safe(row['name'])}", f"setrp:{row['id']}")])
    keyboard.append([button("⬅️ Reseller", "admin:reseller")])
    await edit_or_send(update, "\n".join(lines), InlineKeyboardMarkup(keyboard))


def reseller_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[button("⬅️ Reseller", "admin:reseller")]])


async def reseller_accounts(update: Update) -> None:
    with db() as connection:
        rows = connection.execute(
            "SELECT id, username, first_name, created_at FROM users "
            "WHERE is_reseller = 1 AND active = 1 ORDER BY id DESC LIMIT 50"
        ).fetchall()
    if not rows:
        await edit_or_send(update, "Abhi koi active reseller nahi hai.", reseller_back())
        return
    lines = ["👥 <b>Active Reseller Accounts</b>\n"]
    keyboard = []
    for row in rows:
        label = (
            f"{safe(row['first_name'])} (@{safe(row['username'])})"
            if row["username"]
            else safe(row["first_name"])
        )
        lines.append(f"• {label} — ID: <code>{row['id']}</code>")
        keyboard.append([button(f"Deactivate {row['id']}", f"res_remove:{row['id']}")])
    keyboard.append([button("⬅️ Reseller", "admin:reseller")])
    await edit_or_send(update, "\n".join(lines), InlineKeyboardMarkup(keyboard))


async def admin_translations(update: Update) -> None:
    if not await require_admin(update, None):
        return
    text = (
        "🌐 <b>Content Languages</b>\n\n"
        "User language changes the bot UI. Product/category/plan names and descriptions can also be localized.\n\n"
        "Send one line in this format:\n"
        "<code>product|PRODUCT_ID|LANG|NAME|DESCRIPTION</code>\n"
        "<code>category|CATEGORY_ID|LANG|NAME|DESCRIPTION</code>\n"
        "<code>plan|PLAN_ID|LANG|NAME|DESCRIPTION</code>\n\n"
        "LANG examples: en, hi, bn, te, mr, ta, gu, kn, ml, pa, or, ur, as\n"
        "NAME/description are stored for that language; coupon codes and referral links are never translated."
    )
    await edit_or_send(update, text, InlineKeyboardMarkup([[button("🌐 Add / Update Translation", "admin:translation_input")], [button("⬅️ Admin Panel", "admin:main")]]))


async def admin_settings(update: Update) -> None:
    text = (
        "⚙️ <b>Store Control Center</b>\n\n"
        f"💳 UPI: <code>{safe(setting('upi_id', 'Not set'))}</code>\n"
        f"📢 Notice: {'Set' if setting('store_announcement') else 'Not set'}\n"
        f"🟢 Support: {'Set' if setting('support_url') else 'Not set'}\n"
        f"🎓 Tutorial: {'Set' if setting('tutorial_url') else 'Not set'}\n"
        f"📊 Proof: {'Set' if setting('selling_proof_url') else 'Not set'}\n"
        f"📤 Referral Share Text: {'Set' if setting('referral_share_text') else 'Not set'}"
    )
    keyboard = [
        [button("📢 Set Notice", "flow:set_announcement")],
        [button("🔗 Support", "flow:link_support"), button("🔗 Tutorial", "flow:link_tutorial")],
        [button("🔗 Proof", "flow:link_proof"), button("🔗 Paid Store", "flow:link_paid_store")],
        [button("📤 Referral Share Text", "flow:referral_share_text")],
        [button("⬅️ Admin Panel", "admin:main")],
    ]
    await edit_or_send(update, text, InlineKeyboardMarkup(keyboard))


async def product_category_picker(update: Update) -> None:
    with db() as connection:
        rows = connection.execute(
            "SELECT id, name FROM categories WHERE active = 1 ORDER BY name"
        ).fetchall()
    if not rows:
        await edit_or_send(
            update,
            "Pehle kam se kam ek category add karein.",
            InlineKeyboardMarkup([[button("‹  Admin Catalog", "admin:catalog")]]),
        )
        return
    keyboard = [[button(f"📁 {safe(row['name'])}", f"pwcat:{row['id']}")] for row in rows]
    keyboard.append([button("‹  Cancel", "admin:catalog")])
    await edit_or_send(update, "📦 Product kis category mein add karna hai?", InlineKeyboardMarkup(keyboard))


async def stock_product_picker(update: Update) -> None:
    """Step 1 of stock import: choose product, then its plans."""
    with db() as connection:
        rows = connection.execute(
            "SELECT id, name, maintenance_mode FROM products WHERE active=1 ORDER BY name"
        ).fetchall()
    if not rows:
        await edit_or_send(update, "Pehle product add karein.", admin_keyboard())
        return
    keyboard = [[button(f"{'🚧 ' if row['maintenance_mode'] else '🟢 '}{safe(row['name'])}", f"stockprod:{row['id']}")] for row in rows]
    keyboard.append([button("‹  Cancel", "admin:catalog")])
    await edit_or_send(update, "📦 <b>Product select karein</b>\n\nPhir us product ke saare plans alag-alag dikhेंगे.", InlineKeyboardMarkup(keyboard))


async def stock_plan_picker(update: Update, product_id: int | None = None) -> None:
    """Step 2 of stock import: show only the selected product's plans."""
    with db() as connection:
        if product_id is None:
            rows = connection.execute(
                "SELECT plans.id, products.id AS product_id, products.name AS product_name, plans.name, plans.days, "
                "(SELECT COUNT(*) FROM stock_keys WHERE stock_keys.plan_id=plans.id AND stock_keys.status='available') AS stock "
                "FROM plans JOIN products ON products.id=plans.product_id "
                "WHERE plans.active=1 AND products.active=1 ORDER BY products.name, plans.days"
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT plans.id, products.id AS product_id, products.name AS product_name, plans.name, plans.days, "
                "(SELECT COUNT(*) FROM stock_keys WHERE stock_keys.plan_id=plans.id AND stock_keys.status='available') AS stock "
                "FROM plans JOIN products ON products.id=plans.product_id "
                "WHERE plans.active=1 AND products.active=1 AND products.id=? ORDER BY plans.days, plans.id",
                (product_id,),
            ).fetchall()
    if not rows:
        await edit_or_send(update, "Is product mein abhi koi active plan nahi hai.", back_button("admin:catalog"))
        return
    product_name = rows[0]["product_name"]
    lines = [f"🔑 <b>{safe(product_name)} — Stock Manager</b>", "", "Har plan ke saamne alag 🔑 Add Keys button hai. Ek plan ki keys doosre plan mein nahi jayengi.", ""]
    keyboard=[]
    for row in rows:
        lines.append(f"📌 <b>{safe(row['name'])}</b> • {row['days']} Days • Stock: <b>{row['stock']}</b>")
        keyboard.append([button(f"🔑 Add Keys — {safe(row['name'])} • {row['days']}d • {row['stock']} in stock", f"stockplan:{row['id']}")])
    keyboard.append([button("‹  Back to Products", "admin:stock")])
    await edit_or_send(update, "\n".join(lines), InlineKeyboardMarkup(keyboard))


async def product_maintenance_picker(update: Update) -> None:
    with db() as connection:
        rows = connection.execute(
            "SELECT id, name, maintenance_mode FROM products WHERE active=1 ORDER BY name"
        ).fetchall()
    if not rows:
        await edit_or_send(update, "Abhi koi active product nahi hai.", admin_keyboard())
        return
    keyboard = []
    for row in rows:
        label = "🚧 ON" if row["maintenance_mode"] else "🟢 OFF"
        keyboard.append([button(f"{label} • {safe(row['name'])}", f"productmaint:{row['id']}")])
    keyboard.append([button("⬅️ Admin Catalog", "admin:catalog")])
    await edit_or_send(update, "🚧 <b>Product Maintenance</b>\n\nJis product ko maintenance ON karoge, users uske plans dekh/buy nahi पाएंगे. Stock delete नहीं होगा; OFF karte hi product wapas live ho jayega.", InlineKeyboardMarkup(keyboard))


async def coupon_type_picker(update: Update) -> None:
    await edit_or_send(
        update,
        "🏷️ Discount type choose karein:",
        InlineKeyboardMarkup(
            [
                [button("📊 Percentage (%)", "coupon_type:percent")],
                [button("💵 Fixed Amount (₹)", "coupon_type:fixed")],
                [button("‹  Cancel", "admin:settings")],
            ]
        ),
    )


async def coupon_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    draft = context.user_data.get("coupon_draft", {})
    if not draft.get("code") or draft.get("type") not in {"percent", "fixed"} or "value" not in draft:
        await edit_or_send(update, "❌ Coupon wizard incomplete hai.", admin_keyboard())
        return
    value = f"{draft['value']}%" if draft["type"] == "percent" else money(draft["value"])
    max_uses = "Unlimited" if not draft.get("max_uses") else str(draft["max_uses"])
    expiry = "Never" if not draft.get("expiry_days") else f"{draft['expiry_days']} days"
    text = (
        "╭━━━ 🏷️ <b>COUPON DRAFT</b> ━━━╮\n"
        f"│ 🔖 Code: <code>{safe(draft['code'])}</code>\n"
        f"│ 💸 Discount: <b>{safe(value)}</b>\n"
        f"│ 👥 Max Uses: <b>{safe(max_uses)}</b>\n"
        f"│ ⏳ Expiry: <b>{safe(expiry)}</b>\n"
        "╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
        "Details check karke Create Coupon dabayein."
    )
    await edit_or_send(update, text, InlineKeyboardMarkup([
        [button("✅ Create Coupon", "coupon_save")],
        [button("❌ Cancel", "coupon_cancel")],
    ]))


async def save_product_draft(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save the interactive product draft atomically."""
    draft = context.user_data.get("product_draft", {})
    plans = draft.get("plans", [])
    if not draft.get("name") or not draft.get("category_id") or not plans:
        await admin_reply(update, context,
            "❌ Product incomplete hai. Product name aur kam se kam 1 plan zaroor complete karein."
        )
        return
    try:
        with db() as connection:
            connection.execute("BEGIN")
            cursor = connection.execute(
                "INSERT INTO products(category_id, name, description, channel_link, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    draft["category_id"],
                    draft["name"],
                    draft.get("description", ""),
                    draft.get("channel_link", ""),
                    iso_now(),
                ),
            )
            product_id = cursor.lastrowid
            connection.executemany(
                "INSERT INTO plans(product_id, name, description, days, customer_price, reseller_price) VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        product_id,
                        plan["name"],
                        plan.get("description", ""),
                        plan["days"],
                        plan["customer_price"],
                        plan["reseller_price"],
                    )
                    for plan in plans
                ],
            )
            connection.commit()
    except (KeyError, sqlite3.IntegrityError, sqlite3.OperationalError):
        logging.exception("Product save failed")
        await admin_reply(update, context,
            "❌ Product save nahi ho saka. Details check karke dobara try karein."
        )
        return

    name = safe(draft["name"])
    channel = (
        f"<a href=\"{safe(draft['channel_link'])}\">Open Channel</a>"
        if draft.get("channel_link") else "Not set"
    )
    count = len(plans)
    context.user_data.pop("product_draft", None)
    context.user_data.pop("plan_index", None)
    context.user_data["flow"] = None
    await admin_reply(update, context,
        f"✅ <b>Product Created</b>\n\n🛍️ {name}\n📢 Channel: {channel}\n📦 Plans: <b>{count}</b>\n\n🔑 Ab Catalog → Stock se keys add karein.",
        reply_markup=admin_keyboard(),
        parse_mode=ParseMode.HTML,
    )


async def product_plan_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    draft = context.user_data.get("product_draft", {})
    plans = draft.get("plans", [])
    if not draft.get("name") or not plans:
        await edit_or_send(update, "❌ Product draft incomplete hai.", admin_keyboard())
        return

    lines = [
        "╭━━━ 🛍️ <b>PRODUCT DRAFT</b> ━━━╮",
        f"│ 📦 <b>{safe(draft['name'])}</b>",
        "│ 📢 Channel: " + (
            f"<a href=\"{safe(draft['channel_link'])}\">Open Channel</a>"
            if draft.get("channel_link") else "Not set"
        ),
        "│",
    ]
    for i, plan in enumerate(plans, 1):
        lines.extend([
            f"│ <b>Plan {i} • {safe(plan['name'])}</b>",
            f"│ ⏳ {plan['days']} Days  •  💰 {money(plan['customer_price'])}  •  🤝 {money(plan['reseller_price'])}",
            "│",
        ])
    lines.extend([
        "╰━━━━━━━━━━━━━━━━━━━━━━━━╯",
        "",
        "➕ <b>Add More Plan</b> par tap karke jitne chahein plans add karein. Product name aur channel dobara nahi poocha jayega.",
    ])
    await edit_or_send(
        update,
        "\n".join(lines),
        InlineKeyboardMarkup([
            [button("➕ Add More Plan", "paddplan")],
            [button("↩️ Remove Last Plan", "premovelast")],
            [button("✅ Save Product", "psave")],
            [button("❌ Cancel", "pcancel")],
        ]),
    )


async def admin_risk_alerts(update: Update) -> None:
    with db() as connection:
        rows=connection.execute("SELECT * FROM risk_flags WHERE status='open' ORDER BY id DESC LIMIT 25").fetchall()
    if not rows:
        await edit_or_send(update,"🟢 <b>Risk Alerts</b>\n\nNo open risk alerts.",admin_back()); return
    lines=["⚠️ <b>Risk Alerts</b>\n"]
    kb=[]
    for r in rows:
        lines.append(f"<b>#{r['id']}</b> • User <code>{r['user_id']}</code> • {safe(r['risk_type'])}\n{safe(r['details'])}\n{display_date(r['created_at'])}\n")
        kb.append([button(f"✅ Resolve #{r['id']}",f"riskresolve:{r['id']}")])
    kb.append([button("⬅️ Admin Panel","admin:main")])
    await edit_or_send(update,"\n".join(lines),InlineKeyboardMarkup(kb))


async def schedule_broadcast_screen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["flow"]="schedule_broadcast"
    await edit_or_send(update,"🗓️ <b>Schedule Broadcast</b>\n\nFormat: <code>YYYY-MM-DD HH:MM | message</code>\nTime store timezone (Asia/Kolkata) mein hoga.",admin_back())


async def process_scheduled_broadcasts(context: ContextTypes.DEFAULT_TYPE) -> None:
    now=utc_now()
    with db() as connection:
        connection.execute("UPDATE scheduled_broadcasts SET status='scheduled', processing_at=NULL WHERE status='processing' AND processing_at IS NOT NULL AND datetime(processing_at) <= datetime(?, '-10 minutes')", (now.isoformat(),))
        rows=connection.execute("SELECT * FROM scheduled_broadcasts WHERE status='scheduled' AND run_at<=? ORDER BY id LIMIT 5",(now.isoformat(),)).fetchall()
        for row in rows:
            connection.execute("UPDATE scheduled_broadcasts SET status='processing', processing_at=? WHERE id=? AND status='scheduled'",(now.isoformat(),row['id']))
        connection.commit()
    if not rows: return
    with db() as connection:
        users=connection.execute("SELECT id FROM users WHERE active=1").fetchall()
    for row in rows:
        sent=errors=0
        for user in users:
            try:
                await context.bot.send_message(user['id'], f"📣 <b>SHIVAM STORE</b>\n\n{safe(row['message'])}", parse_mode=ParseMode.HTML)
                sent+=1
            except Exception:
                errors+=1
        with db() as connection:
            connection.execute("UPDATE scheduled_broadcasts SET status='sent', processing_at=NULL, sent_count=?, error_count=? WHERE id=?",(sent,errors,row['id']))
            connection.commit()


async def analytics(update: Update) -> None:
    with db() as connection:
        stats = connection.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM users) users,
              (SELECT COUNT(*) FROM users WHERE is_reseller = 1 AND active = 1) resellers,
              (SELECT COUNT(*) FROM orders WHERE status = 'pending') pending,
              (SELECT COUNT(*) FROM orders WHERE status = 'approved') completed,
              (SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status = 'approved') revenue,
              (SELECT COUNT(*) FROM stock_keys WHERE status = 'available') stock
            """
        ).fetchone()
        today = connection.execute(
            "SELECT COUNT(*) AS orders, COALESCE(SUM(amount), 0) AS revenue FROM orders "
            "WHERE status = 'approved' AND approved_at >= ?",
            ((utc_now() - timedelta(days=1)).isoformat(),),
        ).fetchone()
    text = (
        "📈 <b>Analytics & Reports</b>\n\n"
        f"Total users: <b>{stats['users']}</b>\n"
        f"Active resellers: <b>{stats['resellers']}</b>\n"
        f"Pending orders: <b>{stats['pending']}</b>\n"
        f"Completed orders: <b>{stats['completed']}</b>\n"
        f"All-time approved value: <b>{money(stats['revenue'])}</b>\n"
        f"Available keys: <b>{stats['stock']}</b>\n\n"
        f"Last 24 hours: <b>{today['orders']}</b> orders • <b>{money(today['revenue'])}</b>"
    )
    await edit_or_send(update, text, admin_keyboard())


# ---------------------------------------------------------------------------
# Message flows
# ---------------------------------------------------------------------------

def clear_flow(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in (
        "flow",
        "current_order_id",
        "draft",
        "product_draft",
        "plan_index",
        "stock_plan_id",
        "coupon_draft",
        "coupon_plan_id",
        "pending_utr",
        "deposit_amount",
        "payment_back_callback",
        "admin_auth",
        "admin_authenticated_at",
    ):
        context.user_data.pop(key, None)


async def submit_utr_from_chat(update: Update, context: ContextTypes.DEFAULT_TYPE, utr: str) -> None:
    """Validate a chat-entered UTR and move the order into automatic verification."""
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return
    utr = re.sub(r"\s+", "", str(utr or "")).upper()
    if not re.fullmatch(r"[A-Z0-9]{12,30}", utr):
        await message.reply_text("❌ Valid UTR/RRN 12–30 letters/numbers ka hona chahiye. Spaces ke bina bhejein.")
        return
    order_id = context.user_data.get("current_order_id")
    if not order_id:
        await message.reply_text("❌ Payment session nahi mila. Dobara Shop se order banayein.")
        context.user_data["flow"] = None
        return
    try:
        with db() as connection:
            connection.execute("BEGIN IMMEDIATE")
            duplicate = connection.execute("SELECT order_no FROM orders WHERE utr=?", (utr,)).fetchone()
            order = connection.execute("SELECT * FROM orders WHERE id=? AND user_id=?", (int(order_id), user.id)).fetchone()
            if duplicate:
                connection.rollback()
                if order:
                    add_risk_flag(user.id, "DUPLICATE_UTR", f"UTR already belongs to {duplicate['order_no']}", int(order_id))
                await message.reply_text("❌ Ye UTR pehle use ho chuka hai. Payment automatically verify nahi kiya jayega.")
                return
            if not order or order["status"] != "awaiting_utr":
                connection.rollback()
                await message.reply_text("❌ Payment order active nahi hai ya expire ho chuka hai.")
                context.user_data["flow"] = None
                return
            expiry_value = order["expiry_at"] or (datetime.fromisoformat(order["created_at"]) + timedelta(minutes=20)).isoformat()
            if utc_now() > datetime.fromisoformat(expiry_value):
                connection.execute("UPDATE orders SET status='expired', delivery_status='not_required' WHERE id=?", (int(order_id),))
                connection.commit()
                context.user_data["flow"] = None
                await message.reply_text("⏱️ Payment expire ho gaya hai. Naya order banayein.")
                return
            connection.execute(
                "UPDATE orders SET utr=?, status='pending', payment_method='upi' WHERE id=? AND user_id=? AND status='awaiting_utr' AND payment_method='gateway'",
                (utr, int(order_id), user.id),
            )
            connection.commit()
        context.user_data["flow"] = None
        pending_message = await message.reply_text(
            "⏳ <b>PENDING</b>\n\n"
            f"Order: <code>{safe(order['order_no'])}</code>\n"
            "Payment verification in progress...",
            parse_mode=ParseMode.HTML,
        )
        with db() as connection:
            connection.execute(
                "UPDATE orders SET pending_message_chat_id=?, pending_message_id=? WHERE id=?",
                (pending_message.chat_id, pending_message.message_id, int(order_id)),
            )
            connection.commit()
    except sqlite3.IntegrityError:
        await message.reply_text("❌ Ye UTR already submit ho chuka hai.")


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.effective_message:
        return
    upsert_user(update.effective_user)
    if not is_admin(update.effective_user.id) and setting("maintenance_mode","0") == "1":
        await admin_reply(update, context, "🚧 Store abhi maintenance mode mein hai. Please thodi der baad try karein.")
        return
    with db() as connection:
        banned = connection.execute("SELECT active FROM users WHERE id=?",(update.effective_user.id,)).fetchone()
    if not is_admin(update.effective_user.id) and banned and not banned["active"]:
        await admin_reply(update, context, "⛔ Aapka account temporarily disabled hai. Support se contact karein.")
        return
    flow = context.user_data.get("flow")
    text = update.effective_message.text.strip()
    if flow != "user_password_unlock" and await password_gate(update, context) is False:
        return
    if flow == "user_password_unlock":
        cooldown = str(context.user_data.get("password_cooldown_until", "") or "")
        if cooldown:
            try:
                if datetime.fromisoformat(cooldown.replace("Z", "+00:00")) > utc_now():
                    await delete_incoming(update)
                    await edit_or_send(update, "🛡️ Password attempts temporarily locked. Please wait 60 seconds.", InlineKeyboardMarkup([[button("🚫 Cancel", "home")]]))
                    return
            except ValueError:
                context.user_data.pop("password_cooldown_until", None)
        record = user_password_record(update.effective_user.id)
        await delete_incoming(update)
        if record and _verify_user_password(text, record["bot_password_salt"], record["bot_password_hash"]):
            context.user_data["flow"] = None
            with db() as connection:
                pref = connection.execute("SELECT password_remember_minutes FROM users WHERE id=?", (update.effective_user.id,)).fetchone()
            minutes = int(pref["password_remember_minutes"] or 60) if pref else 60
            context.user_data["password_unlocked_until"] = (utc_now() + timedelta(minutes=minutes)).isoformat()
            await edit_or_send(update, home_text(update.effective_user.id), main_keyboard(update.effective_user.id))
        else:
            attempts = int(context.user_data.get("password_failed_attempts", 0)) + 1
            context.user_data["password_failed_attempts"] = attempts
            if attempts >= 5:
                context.user_data["password_cooldown_until"] = (utc_now() + timedelta(seconds=60)).isoformat()
                context.user_data["password_failed_attempts"] = 0
                await edit_or_send(update, "🛡️ Too many incorrect attempts. Try again after 60 seconds.", InlineKeyboardMarkup([[button("🚫 Cancel", "home")]]))
            else:
                await edit_or_send(update, f"❌ Wrong password. Attempt {attempts}/5.", InlineKeyboardMarkup([[button("🚫 Cancel", "home")]]))
        return
    admin_flows = {
        "admin_user_search", "admin_order_search", "low_stock", "set_announcement",
        "add_category", "product_name", "product_channel", "product_plan_name",
        "product_plan_days", "product_plan_customer_price", "product_plan_reseller_price",
        "product_description", "set_upi", "set_join_fee", "delete_product",
        "set_reseller_price", "edit_plan", "link_support", "link_tutorial",
        "link_proof", "link_paid_store", "referral_share_text", "coupon_code", "coupon_value",
        "coupon_max_uses", "coupon_expiry_days", "add_admin", "admin_balance",
        "schedule_broadcast", "set_referral_reward", "translation_input", "broadcast", "add_key", "stock_keys", "reseller_price",
    }
    if is_admin(update.effective_user.id) and flow in admin_flows:
        await delete_incoming(update)

    if flow == "admin_user_search":
        await delete_incoming(update)
        context.user_data["flow"] = None
        await admin_users(update, text)
        return

    if flow == "admin_order_search":
        await delete_incoming(update)
        context.user_data["flow"] = None
        await admin_order_search(update, text)
        return

    if flow == "low_stock":
        await delete_incoming(update)
        try: value=int(text)
        except ValueError: value=-1
        if not 0 <= value <= 100:
            await admin_reply(update, context, "0 se 100 ke beech number dein.")
            return
        set_setting("low_stock_threshold",str(value)); context.user_data["flow"]=None
        await admin_reply(update, context, "✅ Low-stock threshold save ho gaya.",reply_markup=admin_keyboard())
        return

    if flow == "set_announcement":
        await delete_incoming(update)
        if len(text) > 300:
            await admin_reply(update, context, "Notice 300 characters se chhota rakhein.", reply_markup=admin_keyboard())
            return
        set_setting("store_announcement", text)
        context.user_data["flow"] = None
        await admin_reply(update, context, "✅ Store notice update ho gaya.", reply_markup=admin_keyboard())
        return

    if flow in {"user_password_set", "user_password_change"}:
        await delete_incoming(update)
        if not re.fullmatch(r"[^\s]{4,64}", text):
            await edit_or_send(update, "❌ Password 4–64 characters ka hona chahiye, spaces ke bina.", back_home(update.effective_user.id))
            return
        set_user_password(update.effective_user.id, text)
        context.user_data["flow"] = None
        await settings_security(update)
        return

    if flow in {"utr", "utr_verify", "set_upi"}:
        context.user_data.pop("flow", None)
        await edit_or_send(update, "ℹ️ Manual UPI/UTR payments are disabled. Please use the configured Payment Gateway.", back_home())
        return

    if flow == "coupon_user":
        code = text.upper()
        plan_id = context.user_data.get("coupon_plan_id")
        result = plan_details(int(plan_id), update.effective_user.id) if plan_id else None
        if not result:
            context.user_data.pop("coupon", None)
            context.user_data["flow"] = None
            await edit_or_send(update, "Plan available nahi hai.", back_home())
            return
        plan, reseller = result
        original = float(plan["reseller_price"] if reseller else plan["customer_price"])
        if calculate_coupon(code, original) is None:
            await admin_reply(update, context, "Coupon invalid, expired, ya usage limit complete ho chuki hai.")
            return
        context.user_data["coupon"] = code
        context.user_data["flow"] = None
        await admin_reply(update, context, 
            "✅ Coupon apply ho gaya. Payment method choose karein.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [button("💳 Pay via Gateway", f"buy:{context.user_data['coupon_plan_id']}")],
                    [button("💰 Buy with Wallet", f"walletbuy:{context.user_data['coupon_plan_id']}")],
                    [button("‹  Back to Plan", f"plan:{context.user_data['coupon_plan_id']}")],
                ]
            ),
        )
        return

    if flow == "deposit_keypad":
        await admin_reply(update, context, 
            "👇 Buttons se amount select karein. Chat mein amount type karna disabled hai.",
            reply_markup=deposit_keypad_markup(),
        )
        return

    if flow == "balance_amount":
        # Deposit amount is selected only through the on-screen keypad.
        await admin_reply(update, context, 
            "👇 Deposit amount buttons se select karein. Chat mein amount likhne ki zaroorat nahi hai."
        )
        return



    if flow == "add_category":
        if not 1 <= len(text) <= 80:
            await admin_reply(update, context, "Category name 1–80 characters ka hona chahiye.")
            return
        try:
            with db() as connection:
                connection.execute("INSERT INTO categories(name, description, active) VALUES (?, '', 1)", (text,))
                connection.commit()
        except sqlite3.IntegrityError:
            await admin_reply(update, context, "❌ Ye category already exist karti hai. Dusra naam dein.")
            return
        context.user_data["flow"] = None
        await admin_reply(update, context, 
            f"✅ <b>Category Created</b>\n\n📁 {safe(text)}",
            parse_mode=ParseMode.HTML, reply_markup=admin_keyboard()
        )
        return

    if flow == "product_name":
        if not 1 <= len(text) <= 80:
            await admin_reply(update, context, "Product name 1–80 characters ka hona chahiye.")
            return
        context.user_data.setdefault("product_draft", {})["name"] = text
        context.user_data["flow"] = "product_channel"
        await admin_reply(update, context, 
            "╭━━━ 📢 <b>CHANNEL</b> ━━━╮\n│ Product Channel Link\n╰━━━━━━━━━━━━━━╯\n\nTelegram channel link bhejein, jaise <code>https://t.me/yourchannel</code>.\nChannel nahi hai to <code>skip</code> likhein.",
            parse_mode=ParseMode.HTML,
        )
        return

    if flow == "product_channel":
        channel = "" if text.lower() in {"skip", "none", "no"} else text.strip()
        if channel and not re.fullmatch(r"https?://t\.me/[A-Za-z0-9_+/\-]+/?", channel):
            await admin_reply(update, context, 
                "❌ Valid Telegram channel link bhejein (https://t.me/...) ya skip likhein."
            )
            return
        context.user_data.setdefault("product_draft", {})["channel_link"] = channel
        context.user_data["flow"] = "product_plan_name"
        context.user_data["plan_index"] = 1
        await admin_reply(update, context, 
            "╭━━━ 📦 <b>PLAN 1</b> ━━━╮\n│ 🏷️ Plan Name\n╰━━━━━━━━━━━━╯\n\nPlan ka naam bhejein (Today / 7 Days / 30 Days):",
            parse_mode=ParseMode.HTML,
        )
        return

    if flow == "product_plan_name":
        if not 1 <= len(text) <= 80:
            await admin_reply(update, context, "Plan name 1–80 characters ka hona chahiye.")
            return
        context.user_data.setdefault("product_draft", {}).setdefault("_current", {})["name"] = text
        context.user_data["flow"] = "product_plan_days"
        await admin_reply(update, context, 
            "╭━━━ ⏳ <b>DAYS</b> ━━━╮\n│ Validity Days\n╰━━━━━━━━━━╯\n\nDays number bhejein (1–3650):",
            parse_mode=ParseMode.HTML,
        )
        return

    if flow == "product_plan_days":
        if not text.isdigit() or not 1 <= int(text) <= 3650:
            await admin_reply(update, context, "Days 1 se 3650 ke beech hone chahiye.")
            return
        context.user_data["product_draft"]["_current"]["days"] = int(text)
        context.user_data["flow"] = "product_plan_customer_price"
        await admin_reply(update, context, 
            "╭━━━ 💰 <b>PRICE</b> ━━━╮\n│ Customer Price (₹)\n╰━━━━━━━━━━━━╯\n\nPrice bhejein:",
            parse_mode=ParseMode.HTML,
        )
        return

    if flow == "product_plan_customer_price":
        amount = parse_amount(text, minimum=0, maximum=500_000)
        if amount is None:
            await admin_reply(update, context, "Valid price enter karein.")
            return
        context.user_data["product_draft"]["_current"]["customer_price"] = amount
        context.user_data["flow"] = "product_plan_reseller_price"
        await admin_reply(update, context, 
            "╭━━━ 🤝 <b>RESELLER PRICE</b> ━━━╮\n│ Reseller Price (₹)\n╰━━━━━━━━━━━━━━━━╯\n\nPrice bhejein, ya customer price same rakhne ke liye <code>skip</code> likhein:",
            parse_mode=ParseMode.HTML,
        )
        return

    if flow == "product_plan_reseller_price":
        draft = context.user_data["product_draft"]
        current = draft.pop("_current")
        if text.lower() in {"skip", "same", "no"}:
            amount = current["customer_price"]
        else:
            amount = parse_amount(text, minimum=0, maximum=500_000)
            if amount is None:
                draft["_current"] = current
                await admin_reply(update, context, "Valid reseller price enter karein, ya skip likhein.")
                return
        current["reseller_price"] = amount
        current["description"] = ""
        draft.setdefault("plans", []).append(current)
        context.user_data["plan_index"] = len(draft["plans"])
        context.user_data["flow"] = None
        await product_plan_review(update, context)
        return

    # Compatibility for an older draft that may already be at this state.
    if flow == "product_description":
        context.user_data.setdefault("product_draft", {})["description"] = "" if text.lower() == "skip" else text[:500]
        context.user_data["flow"] = "product_plan_name"
        context.user_data["plan_index"] = 1
        await admin_reply(update, context, "Plan 1 ka naam bhejein:")
        return

    if flow == "set_upi":
        context.user_data.pop("flow", None)
        await admin_reply(update, context, "ℹ️ Manual UPI is disabled. Configure Payment Gateway URL + API key from the Builder.", reply_markup=admin_keyboard())
        return

    if flow == "set_join_fee":
        try:
            amount = float(text.replace(",", ""))
        except ValueError:
            amount = -1
        if amount < 0:
            await admin_reply(update, context, "Valid fee enter karein.")
            return
        set_setting("reseller_join_fee", str(round(amount, 2)))
        context.user_data["flow"] = None
        await admin_reply(update, context, "✅ Reseller joining fee update ho gayi.", reply_markup=admin_keyboard())
        return

    if flow == "add_key":
        await add_keys_from_text(update, context, text)
        return

    if flow == "stock_keys":
        await add_keys_from_text(update, context, text)
        return

    if flow == "delete_product":
        if not text.isdigit():
            await admin_reply(update, context, "Product ID enter karein.")
            return
        with db() as connection:
            connection.execute("UPDATE products SET active = 0 WHERE id = ?", (int(text),))
            connection.commit()
        context.user_data["flow"] = None
        await admin_reply(update, context, "✅ Product hide kar diya gaya.", reply_markup=admin_keyboard())
        return

    if flow == "reseller_price":
        try:
            price = float(text.replace(",", ""))
        except ValueError:
            price = -1
        if price < 0:
            await admin_reply(update, context, "Valid price enter karein.")
            return
        with db() as connection:
            connection.execute("UPDATE plans SET reseller_price = ? WHERE id = ?", (price, context.user_data["plan_id"]))
            connection.commit()
        context.user_data["flow"] = None
        await admin_reply(update, context, "✅ Reseller price save ho gaya.", reply_markup=admin_keyboard())
        return

    if flow == "edit_plan":
        parts = [part.strip() for part in text.split("|")]
        if len(parts) != 4:
            await admin_reply(update, context, 
                "Format: PLAN NAME|DAYS|CUSTOMER PRICE|RESELLER PRICE"
            )
            return
        try:
            days = int(parts[1])
            customer_price = float(parts[2].replace(",", ""))
            reseller_price = float(parts[3].replace(",", ""))
            if days <= 0 or customer_price < 0 or reseller_price < 0 or not parts[0]:
                raise ValueError
        except ValueError:
            await admin_reply(update, context, "Plan details valid format mein bhejein.")
            return
        with db() as connection:
            connection.execute(
                "UPDATE plans SET name = ?, days = ?, customer_price = ?, reseller_price = ? "
                "WHERE id = ?",
                (parts[0], days, customer_price, reseller_price, context.user_data["plan_id"]),
            )
            connection.commit()
        context.user_data["flow"] = None
        await admin_reply(update, context, "✅ Plan, days aur dono prices update ho gaye.", reply_markup=admin_keyboard())
        return

    if flow == "referral_share_text":
        await delete_incoming(update)
        if not text:
            await admin_reply(update, context, "Referral share message empty nahi ho sakta.")
            return
        if len(text) > 4096:
            await admin_reply(update, context, "Referral share message 4096 characters tak rakhein.")
            return
        set_setting("referral_share_text", text)
        context.user_data["flow"] = None
        await admin_reply(update, context, "✅ Referral share message save ho gaya.", reply_markup=admin_keyboard())
        return

    if flow in {"link_support", "link_tutorial", "link_proof", "link_paid_store"}:
        key = {
            "link_support": "support_url",
            "link_tutorial": "tutorial_url",
            "link_proof": "selling_proof_url",
            "link_paid_store": "paid_store_url",
        }[flow]
        set_setting(key, text)
        context.user_data["flow"] = None
        await admin_reply(update, context, "✅ Link save ho gaya.", reply_markup=admin_keyboard())
        return

    if flow == "add_coupon":
        parts = [part.strip() for part in text.split("|")]
        if len(parts) < 3 or parts[1].lower() not in {"percent", "fixed"}:
            await admin_reply(update, context, 
                "Format: CODE|percent/fixed|VALUE|MAX_USES\nExample: SAVE10|percent|10|100"
            )
            return
        try:
            value, max_uses = float(parts[2]), int(parts[3]) if len(parts) > 3 else 0
            with db() as connection:
                connection.execute(
                    "INSERT INTO coupons(code, discount_type, discount_value, max_uses) VALUES (?, ?, ?, ?)",
                    (parts[0].upper(), parts[1].lower(), value, max_uses),
                )
                connection.commit()
        except (ValueError, sqlite3.IntegrityError):
            await admin_reply(update, context, "Coupon format galat hai ya code already exist karta hai.")
            return
        context.user_data["flow"] = None
        await admin_reply(update, context, "✅ Coupon add ho gaya.", reply_markup=admin_keyboard())
        return

    if flow == "coupon_code":
        code = re.sub(r"[^A-Za-z0-9_-]", "", text).upper()
        if not 3 <= len(code) <= 32:
            await admin_reply(update, context, "Coupon code 3–32 letters/numbers ka hona chahiye.")
            return
        context.user_data["coupon_draft"] = {"code": code}
        context.user_data["flow"] = "coupon_value"
        await coupon_type_picker(update)
        return

    if flow == "coupon_value":
        draft = context.user_data["coupon_draft"]
        amount = parse_amount(text, minimum=0.01, maximum=100 if draft["type"] == "percent" else 500_000)
        if amount is None or (draft["type"] == "percent" and amount > 100):
            await admin_reply(update, context, 
                "Percentage 0.01–100 ya fixed amount 0 se zyada enter karein."
            )
            return
        draft["value"] = amount
        context.user_data["flow"] = "coupon_max_uses"
        await admin_reply(update, context, "Maximum users enter karein (0 = unlimited):")
        return

    if flow == "coupon_max_uses":
        if not text.isdigit() or int(text) < 0 or int(text) > 1_000_000:
            await admin_reply(update, context, "0 ya positive whole number enter karein.")
            return
        context.user_data["coupon_draft"]["max_uses"] = int(text)
        context.user_data["flow"] = "coupon_expiry_days"
        await admin_reply(update, context, "Expiry kitne days baad? (0 = never expire):")
        return

    if flow == "coupon_expiry_days":
        if not text.isdigit() or int(text) < 0 or int(text) > 3650:
            await admin_reply(update, context, "0 se 3650 ke beech whole number enter karein.")
            return
        context.user_data["coupon_draft"]["expiry_days"] = int(text)
        context.user_data["flow"] = None
        await coupon_review(update, context)
        return

    if flow == "add_admin":
        context.user_data["flow"] = None
        await admin_reply(update, context, "⛔ Secondary admins disabled hain. Sirf configured owner hi admin hai.", reply_markup=admin_keyboard())
        return

    if flow == "admin_balance":
        parts = [part.strip() for part in text.split("|", 1)]
        if len(parts) != 2 or not parts[0].lstrip("-").isdigit():
            await admin_reply(update, context, "Format: USER_ID|AMOUNT")
            return
        target_id = int(parts[0])
        amount = parse_amount(parts[1], minimum=-500_000, maximum=500_000)
        if amount is None or amount == 0:
            await admin_reply(update, context, "Valid non-zero amount enter karein (±₹500,000 max).")
            return
        with db() as connection:
            connection.execute("BEGIN IMMEDIATE")
            user_row = connection.execute(
                "SELECT balance FROM users WHERE id = ?", (target_id,)
            ).fetchone()
            if not user_row:
                connection.rollback()
                await admin_reply(update, context, "User ID nahi mila.")
                return
            before = round(float(user_row["balance"]), 2)
            after = round(before + amount, 2)
            if after < 0:
                connection.rollback()
                await admin_reply(update, context, "❌ Balance negative nahi ho sakta.")
                return
            connection.execute(
                "UPDATE users SET balance = ?, updated_at = ? WHERE id = ?",
                (after, iso_now(), target_id),
            )
            adjustment_type = "admin_credit" if amount > 0 else "admin_debit"
            connection.execute(
                "INSERT INTO wallet_transactions(user_id, type, amount, balance_before, balance_after, note, created_at) "
                "VALUES (?, ?, ?, ?, ?, 'Admin balance adjustment', ?)",
                (target_id, adjustment_type, abs(amount), before, after, iso_now()),
            )
            connection.commit()
        context.user_data["flow"] = None
        await admin_reply(update, context, 
            f"✅ Balance update ho gaya.\nOld: {money(before)}\nNew: {money(after)}",
            reply_markup=admin_keyboard(),
        )
        return

    if flow == "translation_input":
        await delete_incoming(update)
        if not is_admin(update.effective_user.id): return
        parts = [p.strip() for p in text.split("|", 4)]
        if len(parts) != 5 or parts[0].lower() not in {"product", "category", "plan"} or parts[2].lower() not in SUPPORTED_LANGUAGES or not parts[3]:
            await admin_reply(update, context, "Invalid format. Use: product|ID|lang|NAME|DESCRIPTION")
            return
        kind, raw_id, lang, name, description = parts
        if not raw_id.isdigit():
            await admin_reply(update, context, "ID numeric hona chahiye.")
            return
        table = {"product":"products", "category":"categories", "plan":"plans"}[kind.lower()]
        try:
            with db() as connection:
                row = connection.execute(f"SELECT * FROM {table} WHERE id=? AND active=1", (int(raw_id),)).fetchone()
                if not row:
                    await admin_reply(update, context, f"{kind.title()} ID nahi mila.")
                    return
                existing = localized_json(row["name_i18n"], lang) if "name_i18n" in row.keys() else None
                # Preserve all existing language entries, including the default language.
                current_name_map = json.loads(row["name_i18n"] or "{}") if "name_i18n" in row.keys() else {}
                current_desc_map = json.loads(row["description_i18n"] or "{}") if "description_i18n" in row.keys() else {}
                current_name_map[lang] = name
                current_desc_map[lang] = description
                connection.execute(f"UPDATE {table} SET name_i18n=?, description_i18n=? WHERE id=?", (json.dumps(current_name_map, ensure_ascii=False), json.dumps(current_desc_map, ensure_ascii=False), int(raw_id)))
                connection.execute("INSERT INTO audit_logs(actor_user_id, action, entity_type, entity_id, details, created_at) VALUES(?,?,?,?,?,?)", (update.effective_user.id, "content_translation_update", kind.lower(), int(raw_id), f"language={lang}", iso_now()))
                connection.commit()
        except (json.JSONDecodeError, sqlite3.Error):
            logging.exception("Translation update failed")
            await admin_reply(update, context, "❌ Translation save nahi ho saki.")
            return
        context.user_data["flow"] = None
        await admin_reply(update, context, f"✅ {kind.title()} translation {SUPPORTED_LANGUAGES[lang]} mein save ho gayi.", reply_markup=admin_keyboard())
        return

    if flow == "set_referral_reward":
        await delete_incoming(update)
        if not is_admin(update.effective_user.id): return
        amount = parse_amount(text, minimum=0, maximum=500000)
        if amount is None:
            await admin_reply(update, context, "Valid referral reward ₹0–₹500000 enter karein.")
            return
        set_setting("referral_reward", f"{amount:.2f}")
        context.user_data["flow"] = None
        await admin_reply(update, context, f"✅ Referral reward ab <b>{money(amount)}</b> per successful referral hai.", reply_markup=admin_keyboard(), parse_mode=ParseMode.HTML)
        return

    if flow == "schedule_broadcast":
        await delete_incoming(update)
        if not is_admin(update.effective_user.id): return
        if "|" not in text:
            await admin_reply(update, context, "Format: YYYY-MM-DD HH:MM | message", reply_markup=admin_back()); return
        when, message = [x.strip() for x in text.split("|",1)]
        try:
            local_dt=datetime.strptime(when,"%Y-%m-%d %H:%M").replace(tzinfo=TIMEZONE)
            run_at=local_dt.astimezone(timezone.utc).isoformat()
        except ValueError:
            await admin_reply(update, context, "Date/time format galat hai."); return
        if local_dt.astimezone(timezone.utc) <= utc_now():
            await admin_reply(update, context, "Future time dein."); return
        if not message or len(message)>2000:
            await admin_reply(update, context, "Message 1–2000 characters ka hona chahiye."); return
        with db() as connection:
            connection.execute("INSERT INTO scheduled_broadcasts(message,run_at,created_at) VALUES(?,?,?)",(message,run_at,iso_now())); connection.commit()
        context.user_data["flow"]=None
        await admin_reply(update, context, "✅ Broadcast schedule ho gaya.",reply_markup=admin_keyboard())
        return

    if flow == "broadcast":
        with db() as connection:
            users = connection.execute("SELECT id FROM users WHERE active = 1").fetchall()
        sent = 0
        for row in users:
            try:
                await update.get_bot().send_message(row["id"], text)
                sent += 1
            except Exception:
                continue
        context.user_data["flow"] = None
        await admin_reply(update, context, f"✅ Broadcast {sent} users ko send ho gaya.", reply_markup=admin_keyboard())
        return

    await admin_reply(update, context, 
        "Menu se option select karein.", reply_markup=main_keyboard(update.effective_user.id)
    )




async def create_balance_order(user_id: int, amount: float) -> int:
    with db() as connection:
        cursor = connection.execute(
            """
            INSERT INTO orders(order_no, user_id, order_type, amount, original_amount,
                               topup_amount, status, created_at, expiry_at)
            VALUES (?, ?, 'balance', ?, ?, ?, 'awaiting_utr', ?, ?)
            """,
            (f"TEMP-{secrets.token_hex(8)}", user_id, amount, amount, amount, iso_now(), (utc_now() + timedelta(minutes=20)).isoformat(timespec="seconds")),
        )
        order_id = cursor.lastrowid
        order_no = f"BAL-{datetime.now(TIMEZONE).strftime('%Y%m%d')}-{int(order_id):05d}"
        connection.execute("UPDATE orders SET order_no = ? WHERE id = ?", (order_no, order_id))
        connection.commit()
        return int(order_id)


async def add_keys_from_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Transactional bulk stock import. UI-selected plan is preferred; PLAN_ID|KEY is also accepted."""
    raw_items = []
    selected_plan_id = context.user_data.get("stock_plan_id")
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        plan_id = selected_plan_id
        key_value = raw
        if "|" in raw:
            plan_text, key_value = raw.split("|", 1)
            plan_id = int(plan_text.strip()) if plan_text.strip().isdigit() else None
        if plan_id and key_value.strip():
            raw_items.append((int(plan_id), key_value.strip()))
    if not raw_items:
        await admin_reply(update, context, "Har key alag line par paste karein.")
        return
    added = duplicate = invalid = 0
    now = iso_now()
    try:
        with db() as connection:
            valid_plan_ids = {int(row["id"]) for row in connection.execute(
                "SELECT id FROM plans WHERE active=1"
            ).fetchall()}
            for plan_id, key_value in raw_items:
                if plan_id not in valid_plan_ids:
                    invalid += 1
                    continue
                try:
                    connection.execute(
                        "INSERT INTO stock_keys(plan_id,key_value,status,created_at) VALUES(?,?, 'available', ?)",
                        (plan_id, key_value, now),
                    )
                    added += 1
                except sqlite3.IntegrityError:
                    duplicate += 1
            connection.commit()
    except sqlite3.Error:
        logging.exception("Stock import failed")
        await admin_reply(update, context, "❌ Stock database mein save nahi ho saka. Koi partial commit nahi kiya gaya.")
        return
    context.user_data["flow"] = None
    context.user_data.pop("stock_plan_id", None)
    skipped = duplicate + invalid
    await admin_reply(update, context, 
        f"✅ <b>Stock import complete</b>\n\n"
        f"➕ Added: <b>{added}</b>\n"
        f"♻️ Duplicate: <b>{duplicate}</b>\n"
        f"⚠️ Invalid plan: <b>{invalid}</b>\n"
        f"⏭️ Skipped total: <b>{skipped}</b>",
        parse_mode=ParseMode.HTML, reply_markup=admin_keyboard(),
    )



def get_database_admin_ids() -> set[int]:
    with db() as connection:
        return {int(row["user_id"]) for row in connection.execute("SELECT user_id FROM admins WHERE active = 1")}


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await safe_query_answer(update)
    data = query.data or ""
    if update.effective_user:
        upsert_user(update.effective_user)

    ADMIN_CALLBACK_PREFIXES = (
        "admin:", "retrydelivery:", "flow:", "setrp:", "editplan:", "res_remove:",
        "pwcat:", "paddplan", "premovelast", "psave", "pcancel", "pplanct:",
        "stockprod:", "stockplan:", "productmaint:", "coupon_save", "coupon_cancel", "coupon_type:", "coupon_toggle:",
        "riskresolve:", "userban:", "userunban:", "maintenance:toggle",
    )
    admin_action = data.startswith(ADMIN_CALLBACK_PREFIXES)
    if not admin_action and update.effective_user:
        if user_password_lock_active(update.effective_user.id) and data not in {"settings:password_set", "settings:password_change"}:
            if not await password_gate(update, context):
                return
    if not admin_action and update.effective_user:
        if not is_admin(update.effective_user.id) and setting("maintenance_mode","0") == "1":
            await edit_or_send(update,"🚧 Store abhi maintenance mode mein hai. Please thodi der baad try karein.",main_keyboard(update.effective_user.id)); return
        with db() as connection:
            banned=connection.execute("SELECT active FROM users WHERE id=?",(update.effective_user.id,)).fetchone()
        if banned and not banned["active"]:
            await edit_or_send(update,"⛔ Aapka account temporarily disabled hai.",main_keyboard(update.effective_user.id)); return
    if not admin_action and update.effective_user and not user_is_verified(update.effective_user.id):
        await verification_screen(update)
        return

    if data == "more":
        await settings_screen(update)
    elif data == "settings":
        await settings_screen(update)
    elif data == "proof_tutorial":
        await proof_tutorial_screen(update)
    elif data == "settings:account":
        await settings_account(update)
    elif data == "settings:security":
        await settings_security(update)
    elif data == "settings:notifications":
        await settings_notifications(update)
    elif data == "settings:wallet":
        await settings_wallet(update)
    elif data == "settings:wallet_history":
        await settings_wallet_history(update)
    elif data == "settings:referral_earnings":
        await settings_referral_earnings(update)
    elif data == "settings:shopping":
        await settings_shopping(update)
    elif data == "settings:purchase_prefs":
        await settings_purchase_prefs(update)
    elif data == "settings:referral":
        await settings_referral(update)
    elif data == "settings:support":
        await settings_support(update)
    elif data == "settings:about":
        await settings_about(update)
    elif data == "settings:faq":
        await settings_info_page(update, "❓ <b>Help / FAQ</b>", "For common questions, payment status, orders and account help, contact Support.")
    elif data == "settings:terms":
        await settings_info_page(update, "📜 <b>Terms & Conditions</b>", "Use the store according to its published terms and applicable rules.")
    elif data == "settings:privacy":
        await settings_info_page(update, "🔒 <b>Privacy Policy</b>", "Account and order information is used to operate the store and provide support.")
    elif data == "settings:about_bot":
        await settings_info_page(update, "ℹ️ <b>About Bot</b>", f"{safe(setting('store_name','SHIVAM STORE'))}\nVersion: 3.0.12")
    elif data == "settings:changelog":
        await settings_info_page(update, "🆕 <b>What's New / Changelog</b>", "Premium Settings, Theme Preference, enhanced referral sharing and user security improvements.")
    elif data == "settings:theme":
        await settings_theme(update)
    elif data.startswith("settings:theme:"):
        value = data.split(":", 2)[2]
        if value not in {"default", "premium", "compact"}:
            value = "default"
        with db() as connection:
            connection.execute("UPDATE users SET theme_preference=?, updated_at=? WHERE id=?", (value, iso_now(), update.effective_user.id))
            connection.commit()
        await settings_theme(update)
    elif data == "settings:reset":
        await settings_reset(update)
    elif data.startswith("settings:notify:"):
        key=data.split(":",2)[2]
        allowed={"notifications_enabled","payment_notifications","order_notifications","referral_notifications","wallet_notifications","announcement_notifications"}
        if key in allowed:
            with db() as connection:
                connection.execute(f"UPDATE users SET {key}=CASE {key} WHEN 1 THEN 0 ELSE 1 END, updated_at=? WHERE id=?", (iso_now(), update.effective_user.id))
                connection.commit()
        await settings_notifications(update)
    elif data == "settings:notify_toggle":
        with db() as connection:
            connection.execute("UPDATE users SET notifications_enabled=CASE notifications_enabled WHEN 1 THEN 0 ELSE 1 END, updated_at=? WHERE id=?", (iso_now(), update.effective_user.id))
            connection.commit()
        await settings_notifications(update)
    elif data == "settings:failed_protection":
        await edit_or_send(update, "🛡️ <b>Failed Password Protection</b>\n\nRepeated incorrect password attempts are rejected and a cooldown is applied before another attempt.", InlineKeyboardMarkup([[button(tr(update.effective_user.id,"back_settings"),"settings:security")]]))
    elif data == "settings:password_set":
        context.user_data["flow"] = "user_password_set"
        await edit_or_send(update, "🔑 <b>Set Bot Password</b>\n\n4–64 characters ka password message mein bhejein. Password message delete kar diya jayega.", back_home(update.effective_user.id))
    elif data == "settings:password_change":
        context.user_data["flow"] = "user_password_change"
        await edit_or_send(update, "🔄 <b>Change Bot Password</b>\n\nNaya 4–64 character password bhejein.", back_home(update.effective_user.id))
    elif data == "settings:password_disable":
        disable_user_password(update.effective_user.id)
        context.user_data.pop("password_unlocked_until", None)
        await settings_security(update)
    elif data == "settings:password_lock":
        lock_user_now(update.effective_user.id)
        context.user_data.pop("password_unlocked_until", None)
        await password_gate(update, context)
    elif data == "settings:remember":
        await edit_or_send(update, "⏱️ <b>Remember Unlock</b>\n\nChoose how long this session stays unlocked.", InlineKeyboardMarkup([[button("1 Hour", "settings:remember:60")],[button("6 Hours", "settings:remember:360")],[button("24 Hours", "settings:remember:1440")],[button(tr(update.effective_user.id,'back_settings'),'settings:security')]]))
    elif data.startswith("settings:remember:"):
        minutes = int(data.rsplit(":",1)[1])
        with db() as connection:
            connection.execute("UPDATE users SET password_remember_minutes=?, password_remember_until=?, updated_at=? WHERE id=?", (minutes, (utc_now() + timedelta(minutes=minutes)).isoformat(), iso_now(), update.effective_user.id))
            connection.commit()
        context.user_data["password_unlocked_until"] = (utc_now() + timedelta(minutes=minutes)).isoformat()
        await settings_security(update)
    elif data == "noop":
        await safe_query_answer(update)
    elif data == "language":
        await language_screen(update)
    elif data.startswith("language:"):
        code = data.split(":", 1)[1]
        if code not in SUPPORTED_LANGUAGES:
            await language_screen(update)
            return
        with db() as connection:
            connection.execute("UPDATE users SET language=?, updated_at=? WHERE id=?", (code, iso_now(), update.effective_user.id))
            connection.commit()
        await edit_or_send(update, tr(update.effective_user.id, "language_saved"), main_keyboard(update.effective_user.id))
    elif data == "home":
        context.user_data.clear()
        await edit_or_send(
            update,
            home_text(update.effective_user.id),
            main_keyboard(update.effective_user.id),
        )
    elif data == "shop":
        await show_categories(update)
    elif data.startswith("cat:"):
        await show_products(update, int(data.split(":")[1]))
    elif data.startswith("prod:"):
        await show_plans(update, int(data.split(":")[1]))
    elif data.startswith("plan:"):
        await show_plan(update, int(data.split(":")[1]))
    elif data.startswith("buy:"):
        await begin_product_order(update, context, int(data.split(":")[1]))
    elif data.startswith("walletbuy:"):
        await wallet_purchase(update, context, int(data.split(":")[1]))
    elif data.startswith("coupon:"):
        context.user_data["coupon_plan_id"] = int(data.split(":")[1])
        context.user_data["flow"] = "coupon_user"
        await edit_or_send(
            update,
            "🏷️ Coupon code enter karein:",
            InlineKeyboardMarkup([[button("‹  Back to Plan", f"plan:{data.split(':')[1]}")]]),
        )
    elif data == "profile":
        await profile(update)
    elif data == "history":
        await history(update)
    elif data == "balance":
        await wallet_screen(update)
    elif data == "deposit":
        context.user_data["flow"] = "deposit_keypad"
        context.user_data["deposit_amount"] = ""
        await show_deposit_keypad(update, context)
    elif data.startswith("deposit:d:"):
        digit = data.rsplit(":", 1)[1]
        if context.user_data.get("flow") != "deposit_keypad":
            context.user_data["flow"] = "deposit_keypad"
            context.user_data["deposit_amount"] = ""
        raw = str(context.user_data.get("deposit_amount", ""))
        if len(raw) >= 6:
            await show_deposit_keypad(update, context)
            return
        candidate = (raw + digit).lstrip("0")
        context.user_data["deposit_amount"] = candidate
        await show_deposit_keypad(update, context)
    elif data == "deposit:delete":
        if context.user_data.get("flow") != "deposit_keypad":
            context.user_data["flow"] = "deposit_keypad"
        context.user_data["deposit_amount"] = str(context.user_data.get("deposit_amount", ""))[:-1]
        await show_deposit_keypad(update, context)
    elif data == "deposit:confirm":
        if context.user_data.get("flow") != "deposit_keypad":
            await show_deposit_keypad(update, context)
            return
        await confirm_deposit_amount(update, context)
    elif data == "payment:verify":
        await edit_or_send(update, "ℹ️ Payment ab gateway callback se verify hota hai. UTR manually submit karne ki zarurat nahi hai.", back_home())
    elif data == "payment:cancel":
        order_id = context.user_data.get("current_order_id")
        if order_id:
            with db() as connection:
                connection.execute(
                    "UPDATE orders SET status = 'cancelled', delivery_status = 'not_required' WHERE id = ? AND user_id = ? AND status = 'awaiting_utr'",
                    (int(order_id), update.effective_user.id),
                )
                connection.commit()
        await delete_tracked_screen(update, context)
        clear_flow(context)
        sent = await update.get_bot().send_message(update.effective_chat.id, "❌ Payment process cancel ho gaya.", reply_markup=main_keyboard(update.effective_user.id))
        remember_screen(context, sent)
    elif data == "payment:status":
        order_id = context.user_data.get("current_order_id")
        if not order_id:
            await edit_or_send(update, "Payment session expire ho gaya. Dobara Shop Now se try karein.", back_home())
            return
        with db() as connection:
            order = connection.execute("SELECT order_no,status,utr FROM orders WHERE id=? AND user_id=?", (int(order_id), update.effective_user.id)).fetchone()
        if not order:
            await edit_or_send(update, "Order nahi mila.", back_home()); return
        status_text = {"awaiting_utr":"⏳ PENDING", "pending":"⏳ PENDING", "approved":"✅ VERIFIED — SUCCESS", "rejected":"❌ Payment rejected", "expired":"⏱️ Payment expired", "cancelled":"🚫 Payment cancelled", "payment_verified_stock_unavailable":"⚠️ PAYMENT VERIFIED — STOCK UNAVAILABLE"}.get(order["status"], order["status"].title())
        await send_clean_text_screen(update, context, f"🧾 <b>{safe(order['order_no'])}</b>\n\n{status_text}", main_keyboard(update.effective_user.id))
    elif data == "payment:back":
        callback = context.user_data.get("payment_back_callback", "home")
        # Remove the QR/payment screen so the main menu does not stack underneath it.
        chat_id = context.user_data.get("screen_chat_id")
        message_id = context.user_data.get("screen_message_id")
        if chat_id and message_id:
            try:
                await update.get_bot().delete_message(chat_id=int(chat_id), message_id=int(message_id))
            except Exception:
                logging.debug("Payment screen could not be deleted", exc_info=True)
        clear_flow(context)
        if callback == "balance":
            await wallet_screen(update)
        elif callback == "reseller":
            await reseller_user_screen(update)
        elif callback.startswith("plan:"):
            await show_plan(update, int(callback.split(":", 1)[1]))
        else:
            await edit_or_send(update, home_text(update.effective_user.id), main_keyboard(update.effective_user.id))
    elif data.startswith("track:"):
        try: await track_order(update, int(data.split(":",1)[1]))
        except ValueError: await edit_or_send(update,"Invalid order.",back_home())
    elif data.startswith("riskresolve:"):
        if not await require_admin(update, context): return
        try: rid=int(data.split(":",1)[1])
        except ValueError: await edit_or_send(update,"Invalid risk ID.",admin_back()); return
        with db() as connection:
            connection.execute("UPDATE risk_flags SET status='resolved' WHERE id=?",(rid,)); connection.commit()
        await admin_risk_alerts(update)
    elif data == "referral":
        await referral_screen(update)
    elif data.startswith("refshare:"):
        await referral_screen(update)
    elif data == "reseller":
        await reseller_user_screen(update)
    elif data == "res_join":
        await begin_reseller_order(update, context)
    elif data in {"support", "tutorial", "proof", "paid_store"}:
        mapping = {
            "support": ("support_url", "🟢 Support"),
            "tutorial": ("tutorial_url", "🎓 Tutorial"),
            "proof": ("selling_proof_url", "📊 Selling Proof"),
            "paid_store": ("paid_store_url", "🏪 Paid Store"),
        }
        await link_screen(update, *mapping[data])
    elif data.startswith("admin:"):
        await edit_or_send(
            update,
            "🛡️ <b>Admin panel moved</b>\n\nAdmin controls are available only in the SHIVAM BOT BUILDER website.",
            back_home(update.effective_user.id),
        )
        return
        # Legacy admin callback code intentionally unreachable; kept below for database compatibility.
        action = data.split(":", 1)[1]
        if action == "main":
            await show_admin_panel(update)
        elif action == "logout":
            await cleanup_admin_session_messages(update, context, delete_screen=False)
            context.user_data.clear()
            if query.message:
                try:
                    await query.edit_message_text(
                        home_text(update.effective_user.id),
                        parse_mode=ParseMode.HTML,
                        reply_markup=main_keyboard(update.effective_user.id),
                    )
                    remember_screen(context, query.message)
                except Exception:
                    logging.debug("Could not restore main menu on logout", exc_info=True)
                    try:
                        await query.message.delete()
                    except Exception:
                        logging.debug("Could not delete admin panel message", exc_info=True)
                    sent = await update.get_bot().send_message(
                        update.effective_chat.id,
                        home_text(update.effective_user.id),
                        parse_mode=ParseMode.HTML,
                        reply_markup=main_keyboard(update.effective_user.id),
                    )
                    remember_screen(context, sent)

        elif action == "catalog":
            await admin_catalog(update)
        elif action == "pending":
            await pending_orders(update)
        elif action == "reseller":
            await reseller_panel(update)
        elif action == "reseller_pending":
            await pending_orders(update, reseller_only=True)
        elif action == "reseller_prices":
            await reseller_prices(update)
        elif action == "reseller_accounts":
            await reseller_accounts(update)
        elif action == "settings":
            await admin_settings(update)
        elif action == "analytics":
            await analytics(update)
        elif action == "users":
            await admin_users(update)
        elif action == "order_search":
            context.user_data["flow"] = "admin_order_search"
            await edit_or_send(update, "🔎 Order number, User ID ya UTR bhejein:", admin_back())
        elif action == "stock":
            await admin_stock(update)
        elif action == "coupons":
            await admin_coupons(update)
        elif action == "maintenance":
            await admin_maintenance(update)
        elif action == "admins":
            await edit_or_send(update, "👑 <b>Owner Only</b>\n\nSirf configured OWNER_USER_ID admin commands chala sakta hai. Secondary admins disabled hain.", admin_back())
        elif action == "broadcast":
            context.user_data["flow"] = "broadcast"
            await edit_or_send(update, "📣 Broadcast message bhejein:")
        elif action == "health":
            await admin_health(update)
        elif action == "backup":
            await admin_backup(update, context)
        elif action == "failed_delivery":
            await admin_failed_deliveries(update)
        elif action == "risk":
            await admin_risk_alerts(update)
        elif action == "translations":
            await admin_translations(update)
        elif action == "translation_input":
            context.user_data["flow"] = "translation_input"
            await admin_reply(update, context, "Format: product|PRODUCT_ID|LANG|NAME|DESCRIPTION\nExample: product|12|hi|प्रीमियम पैक|विवरण यहाँ", reply_markup=admin_back())
        elif action == "referrals":
            await admin_referrals(update)
        elif action == "referral_users":
            await admin_referral_users(update)
        elif action == "referral_set":
            context.user_data["flow"] = "set_referral_reward"
            await edit_or_send(update, f"💰 Current referral reward: <b>{money(referral_reward_amount())}</b>\n\nNaya reward amount bhejein (₹0–₹500000, 2 decimal tak):", admin_back())
        elif action == "schedule":
            await schedule_broadcast_screen(update, context)
    elif data.startswith("retrydelivery:"):
        if not await require_admin(update, context):
            return
        try:
            order_id = int(data.split(":", 1)[1])
        except ValueError:
            await edit_or_send(update, "Invalid delivery ID.", admin_back())
            return
        await retry_delivery(update, order_id)
    elif data.startswith("flow:"):
        if not await require_admin(update, context):
            return
        flow = data.split(":", 1)[1]
        prompts = {
            "add_category": ("add_category", "Category ka naam bhejein:"),
            "add_product": ("add_product", "Product wizard start ho raha hai..."),
            "add_key": ("add_key", "Bulk format: PLAN_ID|KEY (har key new line par)"),
            "delete_product": ("delete_product", "Delete/hide karne wale product ka ID bhejein:"),
            "set_join_fee": ("set_join_fee", "Reseller joining fee bhejein:"),
            "link_support": ("link_support", "Support URL bhejein:"),
            "link_tutorial": ("link_tutorial", "Tutorial URL bhejein:"),
            "link_proof": ("link_proof", "Selling proof URL bhejein:"),
            "link_paid_store": ("link_paid_store", "Paid store URL bhejein:"),
            "referral_share_text": ("referral_share_text", "📤 Referral Share Message bhejein. Ye text Share Referral mein link ke saath aayega (max 4096 characters):"),
            "add_coupon": ("add_coupon", "Coupon wizard start ho raha hai..."),
            "add_admin": ("add_admin", "Secondary admins disabled hain. Sirf owner configured hai."),
            "user_search": ("admin_user_search", "User ID, username ya name bhejein:"),
            "low_stock": ("low_stock", "Low-stock threshold (0–100) bhejein:"),
            "set_announcement": ("set_announcement", "📢 Store notice bhejein. Empty bhejne ke liye /clear_notice use karein:"),
            "schedule_broadcast": ("schedule_broadcast", "🗓️ Format: YYYY-MM-DD HH:MM | message"),
        }
        if flow == "add_product":
            await product_category_picker(update)
        elif flow == "add_key":
            await stock_product_picker(update)
        elif flow == "add_coupon":
            context.user_data["flow"] = "coupon_code"
            await edit_or_send(
                update,
                "╭━━━ 🏷️ <b>NEW COUPON</b> ━━━╮\n│ 🔖 Coupon Code\n╰━━━━━━━━━━━━━━━━╯\n\nCode bhejein (3–32 letters/numbers):",
                parse_mode=ParseMode.HTML,
            )
        elif flow == "cancel":
            clear_flow(context)
            await show_admin_panel(update)
        elif flow in prompts:
            context.user_data["flow"] = prompts[flow][0]
            await edit_or_send(update, prompts[flow][1])
    elif data.startswith("pwcat:"):
        if not await require_admin(update, context):
            return
        try:
            category_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await edit_or_send(update, "Invalid category ID.", admin_keyboard())
            return
        with db() as connection:
            category = connection.execute(
                "SELECT id, name FROM categories WHERE id = ? AND active = 1",
                (category_id,),
            ).fetchone()
        if not category:
            await edit_or_send(update, "Category nahi mili.", admin_keyboard())
            return
        context.user_data["product_draft"] = {
            "category_id": category_id,
            "category_name": category["name"],
            "plans": [],
        }
        context.user_data["flow"] = "product_name"
        await edit_or_send(update, f"Product name bhejein ({safe(category['name'])}):")
    elif data == "paddplan":
        if not await require_admin(update, context):
            return
        draft = context.user_data.get("product_draft")
        if not draft or not draft.get("plans"):
            await edit_or_send(update, "❌ First plan pehle complete karein.", admin_keyboard())
            return
        context.user_data["flow"] = "product_plan_name"
        context.user_data["plan_index"] = len(draft["plans"]) + 1
        await edit_or_send(
            update,
            f"╭━━━ 📦 <b>PLAN {len(draft['plans']) + 1}</b> ━━━╮\n│ 🏷️ Plan Name\n╰━━━━━━━━━━━━╯\n\nPlan ka naam bhejein:",
        )
    elif data == "premovelast":
        if not await require_admin(update, context):
            return
        draft = context.user_data.get("product_draft")
        if not draft or not draft.get("plans"):
            await edit_or_send(update, "❌ Remove karne ke liye koi plan nahi hai.", admin_keyboard())
            return
        removed = draft["plans"].pop()
        context.user_data["plan_index"] = len(draft["plans"])
        if not draft["plans"]:
            context.user_data["flow"] = "product_plan_name"
            context.user_data["plan_index"] = 1
            await edit_or_send(update, "↩️ Last plan remove ho gaya. Ab Plan 1 ka naam bhejein:")
            return
        context.user_data["flow"] = None
        await product_plan_review(update, context)
    elif data == "psave":
        if not await require_admin(update, context):
            return
        await save_product_draft(update, context)
    elif data == "pcancel":
        if not await require_admin(update, context):
            return
        context.user_data.pop("product_draft", None)
        context.user_data.pop("plan_index", None)
        context.user_data["flow"] = None
        await edit_or_send(update, "❌ Product draft cancel ho gaya.", admin_keyboard())
    elif data.startswith("pplanct:"):
        if not await require_admin(update, context):
            return
        try:
            count = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await edit_or_send(update, "Invalid plan count.", admin_keyboard())
            return
        if count < 1 or count > 50 or "product_draft" not in context.user_data:
            await edit_or_send(update, "Product wizard expire ho gaya. Dobara start karein.", admin_keyboard())
            return
        context.user_data["product_draft"]["plan_count"] = count
        context.user_data["plan_index"] = 1
        context.user_data["flow"] = "product_plan_name"
        await edit_or_send(update, "Plan 1 ka naam bhejein:")
    elif data == "admin:product_maintenance":
        if not await require_admin(update, context):
            return
        await product_maintenance_picker(update)
    elif data.startswith("productmaint:"):
        if not await require_admin(update, context):
            return
        try:
            product_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await edit_or_send(update, "Invalid product ID.", admin_back())
            return
        with db() as connection:
            row = connection.execute("SELECT name, maintenance_mode FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
            if not row:
                await edit_or_send(update, "Product nahi mila.", admin_back())
                return
            new_value = 0 if row["maintenance_mode"] else 1
            connection.execute("UPDATE products SET maintenance_mode=? WHERE id=?", (new_value, product_id))
            connection.execute("INSERT INTO audit_logs(actor_user_id, action, entity_type, entity_id, details, created_at) VALUES(?,?,?,?,?,?)", (update.effective_user.id, "product_maintenance_toggle", "product", product_id, f"maintenance_mode={new_value}", iso_now()))
            connection.commit()
        await product_maintenance_picker(update)
    elif data.startswith("stockprod:"):
        if not await require_admin(update, context):
            return
        try:
            product_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await edit_or_send(update, "Invalid product ID.", admin_keyboard())
            return
        with db() as connection:
            valid = connection.execute("SELECT id FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
        if not valid:
            await edit_or_send(update, "Product nahi mila ya inactive hai.", admin_keyboard())
            return
        await stock_plan_picker(update, product_id)
    elif data.startswith("stockplan:"):
        if not await require_admin(update, context):
            return
        try:
            stock_plan_id = int(data.split(":", 1)[1])
        except (ValueError, IndexError):
            await edit_or_send(update, "Invalid plan ID.", admin_keyboard())
            return
        with db() as connection:
            valid = connection.execute("SELECT 1 FROM plans WHERE id=? AND active=1", (stock_plan_id,)).fetchone()
        if not valid:
            await edit_or_send(update, "Plan nahi mili ya inactive hai.", admin_keyboard())
            return
        context.user_data["stock_plan_id"] = stock_plan_id
        context.user_data["flow"] = "stock_keys"
        await edit_or_send(
            update,
            "🔑 Ab sirf keys paste karein — har key alag line par.\n"
            "Example:\n<code>ABC-123</code>\n<code>XYZ-456</code>",
        )
    elif data == "coupon_save":
        if not await require_admin(update, context):
            return
        draft = context.user_data.get("coupon_draft", {})
        expires_at = (
            (utc_now() + timedelta(days=int(draft.get("expiry_days", 0)))).isoformat()
            if int(draft.get("expiry_days", 0)) > 0 else None
        )
        try:
            with db() as connection:
                connection.execute(
                    "INSERT INTO coupons(code, discount_type, discount_value, max_uses, expires_at) VALUES (?, ?, ?, ?, ?)",
                    (draft["code"], draft["type"], draft["value"], draft["max_uses"], expires_at),
                )
                connection.commit()
        except (KeyError, sqlite3.IntegrityError):
            await edit_or_send(update, "❌ Coupon code already exist karta hai ya details invalid hain.", admin_keyboard())
            return
        context.user_data.pop("coupon_draft", None)
        context.user_data["flow"] = None
        await edit_or_send(update, "✅ <b>Coupon Created</b>\n\nCoupon Coupons Manager mein available hai.", admin_keyboard())
    elif data == "coupon_cancel":
        if not await require_admin(update, context):
            return
        context.user_data.pop("coupon_draft", None)
        context.user_data["flow"] = None
        await edit_or_send(update, "❌ Coupon draft cancel ho gaya.", admin_keyboard())
    elif data.startswith("coupon_type:"):
        if not await require_admin(update, context):
            return
        discount_type = data.split(":", 1)[1]
        if discount_type not in {"percent", "fixed"} or "coupon_draft" not in context.user_data:
            await edit_or_send(update, "Coupon wizard expire ho gaya.", admin_keyboard())
            return
        context.user_data["coupon_draft"]["type"] = discount_type
        context.user_data["flow"] = "coupon_value"
        label = "0.01–100" if discount_type == "percent" else "₹ amount"
        await edit_or_send(update, f"Discount value enter karein ({label}):")
    elif data.startswith("setrp:"):
        if not await require_admin(update, context):
            return
        context.user_data["flow"] = "reseller_price"
        context.user_data["plan_id"] = int(data.split(":")[1])
        await edit_or_send(update, "Naya reseller price bhejein:")
    elif data.startswith("editplan:"):
        if not await require_admin(update, context):
            return
        context.user_data["flow"] = "edit_plan"
        context.user_data["plan_id"] = int(data.split(":")[1])
        await edit_or_send(
            update,
            "Format bhejein:\nPLAN NAME|DAYS|CUSTOMER PRICE|RESELLER PRICE",
        )
    elif data.startswith("userban:") or data.startswith("userunban:"):
        if not await require_admin(update, context): return
        target_id=int(data.split(":")[1])
        if target_id == int(OWNER_USER_ID or -1):
            await edit_or_send(update,"⛔ Owner ko ban nahi kiya ja sakta.",admin_back()); return
        active=1 if data.startswith("userunban:") else 0
        with db() as connection:
            connection.execute("UPDATE users SET active=?, updated_at=? WHERE id=?",(active,iso_now(),target_id)); connection.commit()
        await admin_users(update)
    elif data.startswith("coupon_toggle:"):
        if not await require_admin(update, context): return
        cid=int(data.split(":")[1])
        with db() as connection:
            connection.execute("UPDATE coupons SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?",(cid,)); connection.commit()
        await admin_coupons(update)
    elif data == "maintenance:toggle":
        if not await require_admin(update, context): return
        current=setting("maintenance_mode","0")=="1"
        set_setting("maintenance_mode","0" if current else "1")
        await admin_maintenance(update)
    elif data.startswith("res_remove:"):
        if not await require_admin(update, context):
            return
        target_id = int(data.split(":")[1])
        with db() as connection:
            connection.execute(
                "UPDATE users SET is_reseller = 0, updated_at = ? WHERE id = ?",
                (iso_now(), target_id),
            )
            connection.commit()
        await edit_or_send(update, "✅ Reseller deactivate ho gaya.", reseller_back())


async def reseller_user_screen(update: Update) -> None:
    with db() as connection:
        user = connection.execute(
            "SELECT is_reseller FROM users WHERE id = ?", (update.effective_user.id,)
        ).fetchone()
    if user and user["is_reseller"]:
        await edit_or_send(
            update,
            "🤝 <b>Active Reseller</b>\n\n"
            "Aapko Shop Now par sirf reseller prices dikhengi.",
            InlineKeyboardMarkup([[button("🛒 Shop Now", "shop")], [button("⬅️ Main Menu", "home")]]),
        )
        return
    fee = float(setting("reseller_join_fee", "0"))
    with db() as connection:
        pending = connection.execute(
            "SELECT 1 FROM orders WHERE user_id = ? AND order_type = 'reseller' "
            "AND status IN ('awaiting_utr', 'pending')",
            (update.effective_user.id,),
        ).fetchone()
    if pending:
        await edit_or_send(update, "Aapka reseller payment automatic verification ke liye pending hai.", back_home())
        return
    await edit_or_send(
        update,
        "🤝 <b>Reseller Program</b>\n\n"
        f"One-time joining fee: <b>{money(fee)}</b>\n"
        "Payment automatic verify hone ke baad aapko har product par special reseller price milegi.",
        InlineKeyboardMarkup([[button(f"💳 Become Reseller — {money(fee)}", "res_join")], [button("⬅️ Main Menu", "home")]]),
    )


async def begin_reseller_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_payment_configured(update, context):
        return
    fee = float(setting("reseller_join_fee", "0"))
    order_id = await create_special_order(update.effective_user.id, "reseller", fee)
    context.user_data["current_order_id"] = order_id
    context.user_data["flow"] = "payment_wait"
    with db() as connection:
        order = connection.execute("SELECT order_no FROM orders WHERE id = ?", (order_id,)).fetchone()
    await send_payment_screen(update, context, order["order_no"], fee, "Reseller Membership", "reseller")


async def create_special_order(user_id: int, order_type: str, amount: float) -> int:
    with db() as connection:
        cursor = connection.execute(
            "INSERT INTO orders(order_no, user_id, order_type, amount, original_amount, "
            "topup_amount, status, created_at, expiry_at) VALUES (?, ?, ?, ?, ?, ?, 'awaiting_utr', ?, ?)",
            (f"TEMP-{secrets.token_hex(8)}", user_id, order_type, amount, amount, 0, iso_now(), (utc_now() + timedelta(minutes=20)).isoformat(timespec="seconds")),
        )
        order_id = int(cursor.lastrowid)
        prefix = "RES" if order_type == "reseller" else "ORD"
        order_no = f"{prefix}-{datetime.now(TIMEZONE).strftime('%Y%m%d')}-{order_id:05d}"
        connection.execute("UPDATE orders SET order_no = ? WHERE id = ?", (order_no, order_id))
        connection.commit()
        return order_id


async def expiry_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    expire_stale_orders()


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error("Unhandled Telegram update error", exc_info=context.error)
    message = getattr(update, "effective_message", None)
    if message:
        try:
            await message.reply_text(
                "⚠️ Temporary error aa gaya. Dobara try karein ya /start dabayein."
            )
        except Exception:
            logging.debug("Could not send error response", exc_info=True)


# ---------------------------------------------------------------------------
# Command aliases
# ---------------------------------------------------------------------------

async def command_guard(update: Update, context: ContextTypes.DEFAULT_TYPE, callback: Any) -> None:
    if await require_admin(update, context):
        await callback(update, context)


async def clear_notice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_admin(update, context):
        return
    set_setting("store_announcement", "")
    await admin_reply(update, context, "✅ Store notice clear ho gaya.", reply_markup=admin_keyboard())


async def admin_health(update: Update) -> None:
    if not update.effective_user or not is_admin(update.effective_user.id):
        await deny_admin(update)
        return
    try:
        with db() as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            users = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            orders = connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
            available = connection.execute("SELECT COUNT(*) FROM stock_keys WHERE status='available'").fetchone()[0]
        status = "🟢 HEALTHY" if integrity == "ok" else "🔴 CHECK FAILED"
        imap_ok = bool(IMAP_ENABLED and IMAP_USERNAME and IMAP_APP_PASSWORD and IMAP_ALLOWED_SENDERS)
        last_run = setting("auto_payment_last_run", "—")
        last_error = setting("auto_payment_last_error", "—")
        text=(f"🩺 <b>System Health</b>\n\nStatus: <b>{status}</b>\nDB integrity: <code>{safe(integrity)}</code>\nUsers: <b>{users}</b>\nOrders: <b>{orders}</b>\nAvailable stock: <b>{available}</b>\nIMAP verifier config: <b>{'READY' if imap_ok else 'NOT READY'}</b>\nIMAP last run: <code>{safe(last_run)}</code>\nIMAP last error: <code>{safe(last_error)}</code>")
    except Exception as exc:
        text=f"🔴 <b>System check failed</b>\n<code>{safe(exc)}</code>"
    await edit_or_send(update, text, admin_back())


async def admin_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user=update.effective_user
    if not user or not is_admin(user.id):
        await deny_admin(update)
        return
    if not DB_PATH.exists():
        await edit_or_send(update, "❌ Database file nahi mila.", admin_back())
        return
    import tempfile
    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(prefix="shivam_store_backup_", suffix=".sqlite3")
        os.close(fd)
        with db() as source:
            with sqlite3.connect(temp_path) as target:
                source.backup(target)
                result = target.execute("PRAGMA integrity_check").fetchone()[0]
                if result != "ok":
                    raise RuntimeError(f"Backup integrity check failed: {result}")
                target.execute("PRAGMA wal_checkpoint(PASSIVE)")
        os.chmod(temp_path, 0o600)
        with open(temp_path, "rb") as backup_file:
            await update.get_bot().send_document(
                chat_id=user.id,
                document=backup_file,
                filename="shivam_store_backup.sqlite3",
                caption=f"💾 SHIVAM STORE safe database snapshot\nCreated: {display_date(iso_now())}",
            )
        await edit_or_send(update, "✅ Safe database snapshot backup bhej diya gaya.", admin_keyboard())
    except Exception:
        logging.exception("Database backup delivery failed")
        await edit_or_send(update, "❌ Backup send nahi ho saka. Database/network check karein.", admin_back())
    finally:
        if temp_path:
            try: os.unlink(temp_path)
            except OSError: pass


async def setupi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await admin_reply(update, context, "Manual UPI is disabled. Configure Payment Gateway from the Builder.")
async def addcategory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_admin(update, context):
        return
    context.user_data["flow"] = "add_category"
    await admin_reply(update, context, "Category ka naam bhejein:")


async def addproduct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_admin(update, context):
        return
    await product_category_picker(update)


async def delproduct(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_admin(update, context):
        return
    context.user_data["flow"] = "delete_product"
    await admin_reply(update, context, "Hide/delete karne wale product ka ID bhejein:")


async def addkey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_admin(update, context):
        return
    await stock_plan_picker(update)


async def addbalance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_admin(update, context):
        return
    context.user_data["flow"] = "admin_balance"
    await admin_reply(update, context, "Format: USER_ID|AMOUNT")


async def imaptest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_admin(update, context):
        return
    ok, detail = await asyncio.to_thread(imap_connection_check)
    icon = "✅" if ok else "❌"
    await admin_reply(update, context, f"{icon} <b>Gmail/IMAP Test</b>\n\n{safe(detail)}", parse_mode=ParseMode.HTML, reply_markup=admin_keyboard())


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_admin(update, context):
        return
    await analytics(update)


async def pendingorders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_admin(update, context):
        return
    await pending_orders(update)


async def addcoupon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_admin(update, context):
        return
    context.user_data["flow"] = "coupon_code"
    await admin_reply(update, context, "╭━━━ 🏷️ NEW COUPON ━━━╮\n│ 🔖 Coupon Code\n╰━━━━━━━━━━━━━━╯\n\nCode bhejein (3–32 letters/numbers):", parse_mode=ParseMode.HTML)


async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_admin(update, context): return
    await admin_reply(update, context, "⛔ Secondary admins disabled hain. Sirf owner admin hai.", reply_markup=admin_keyboard())


async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str, label: str) -> None:
    if not await require_admin(update, context):
        return
    context.user_data["flow"] = key
    await admin_reply(update, context, f"{label} URL bhejein:")


async def set_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await link_command(update, context, "link_support", "Support")


async def set_tutorial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await link_command(update, context, "link_tutorial", "Tutorial")


async def set_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await link_command(update, context, "link_proof", "Selling proof")


async def set_paid_store(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await link_command(update, context, "link_paid_store", "Paid store")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_admin(update, context):
        return
    context.user_data["flow"] = "broadcast"
    await admin_reply(update, context, "Broadcast message bhejein:")


def heartbeat_thread() -> None:
    """Write process + Telegram connectivity heartbeats outside the job queue."""
    p = os.getenv("BOT_HEARTBEAT_PATH", "").strip()
    if not p:
        return
    token = BOT_TOKEN.strip()
    connectivity_path = str(Path(p).with_name("telegram_heartbeat"))
    while True:
        try:
            # The process heartbeat proves the Python process is alive.
            Path(p).write_text(iso_now(), encoding="utf-8")
            # A second heartbeat proves the Telegram API is reachable with this token.
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{token}/getMe",
                method="GET",
                headers={"Accept": "application/json", "User-Agent": "SHIVAM-STORE-BOT/3.2"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                payload = json.loads(resp.read(64 * 1024).decode("utf-8", errors="replace"))
                if not payload.get("ok"):
                    raise RuntimeError("Telegram getMe returned ok=false")
            Path(connectivity_path).write_text(iso_now(), encoding="utf-8")
        except Exception:
            logging.debug("Heartbeat/connectivity check failed", exc_info=True)
        time.sleep(30)


async def heartbeat_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    # Kept as a secondary heartbeat when JobQueue is available.
    p=os.getenv("BOT_HEARTBEAT_PATH", "").strip()
    if not p:
        return
    try:
        Path(p).write_text(iso_now(), encoding="utf-8")
    except Exception:
        logging.debug("Heartbeat write failed", exc_info=True)


async def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit(
            "BOT_TOKEN missing. .env file mein BOT_TOKEN=... set karein. "
            "ADMIN_USER_ID bhi zaroor set karein."
        )
    if not ADMIN_USER_IDS:
        raise SystemExit("ADMIN_USER_ID missing. .env file mein apna numeric Telegram user ID set karein.")
    gateway_enabled = os.getenv("PAYMENT_GATEWAY_ENABLED", "0").strip() == "1"
    if gateway_enabled:
        gateway_url = os.getenv("PAYMENT_GATEWAY_URL", "").strip()
        gateway_key = os.getenv("PAYMENT_GATEWAY_API_KEY", "").strip()
        if not gateway_url or not gateway_url.lower().startswith("https://"):
            raise SystemExit("PAYMENT_GATEWAY_URL missing or must use HTTPS when gateway payments are enabled.")
        if not gateway_key:
            raise SystemExit("PAYMENT_GATEWAY_API_KEY missing when gateway payments are enabled.")
    init_db()
    expire_stale_orders()
    threading.Thread(target=heartbeat_thread, name="heartbeat", daemon=True).start()
    application = Application.builder().token(BOT_TOKEN).build()
    # Customer-facing Telegram surface only. All store/admin management is website-only.
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CallbackQueryHandler(callback_router))
    application.add_handler(MessageHandler(filters.CONTACT, contact_router))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    application.add_error_handler(error_handler)
    if application.job_queue:
        application.job_queue.run_repeating(expiry_job, interval=300, first=300)
        application.job_queue.run_repeating(process_scheduled_broadcasts, interval=30, first=30)
        application.job_queue.run_repeating(gateway_callback_fulfillment_job, interval=10, first=5)
        application.job_queue.run_repeating(heartbeat_job, interval=30, first=1)
    logging.info("%s is starting with database %s", BOT_VERSION, DB_PATH)
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)
    stop_event = __import__("asyncio").Event()
    try:
        await stop_event.wait()
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        level=logging.INFO,
    )
    import asyncio

    asyncio.run(main())