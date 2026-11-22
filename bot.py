"""
بوت تليجرام بيعمل صفحات هبوط (Landing Pages) لأي نشاط تجاري.

الفكرة: العميل يكلم البوت، يختار مجاله، يدخل اسم النشاط ورقم الواتساب
والمنتجات، والبوت يطلعله ملف HTML جاهز يترفع على أي استضافة.

شغال من غير أي خدمة مدفوعة. لو حطيت AI_API_KEY في ملف .env هيتفعّل
جزء الوصف الذكي للمنتجات (شوف ai_hook.py).
"""

import logging
import os
import re
import time
from html import escape
from pathlib import Path
from string import Template
from urllib.parse import quote

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from ai_hook import describe_product

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ------------------------- ثوابت -------------------------

FIELDS = {
    "furniture": ("🛋️", "أثاث وفرش"),
    "food": ("🍔", "أكل وحلويات"),
    "clothing": ("👕", "ملابس وأزياء"),
    "services": ("🛠️", "خدمات"),
    "other": ("✨", "مجال تاني"),
}

# مراحل المحادثة
(
    CHOOSING_FIELD,
    BUSINESS_NAME,
    WA_NUMBER,
    PRODUCT_NAME,
    PRODUCT_PRICE,
    ADD_MORE,
) = range(6)

PAGES_DIR = Path("pages")
PAGES_DIR.mkdir(exist_ok=True)

TEMPLATE = Template(
    (Path(__file__).parent / "template.html").read_text(encoding="utf-8")
)


# ------------------------- أدوات مساعدة -------------------------

def normalize_whatsapp(raw: str) -> str:
    """يحوّل الرقم لصيغة دولية تشتغل في روابط wa.me"""
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("00"):
        digits = digits[2:]
    # رقم مصري مكتوب 01xxxxxxxxx
    if digits.startswith("0") and len(digits) == 11:
        digits = "20" + digits[1:]
    return digits


def build_products_html(products: list, field_key: str, wa_number: str) -> str:
    cards = []
    for p in products:
        name = escape(p["name"])
        price = escape(p["price"])
        desc = describe_product(field_key, p["name"], p["price"]) or \
            "جودة ممتازة وسعر يناسبك 👌"
        order_msg = quote(f"السلام عليكم 👋 عايز أطلب: {p['name']} ({p['price']})")
        cards.append(
            f"""
      <div class="card">
        <h3>{name}</h3>
        <p class="desc">{escape(desc)}</p>
        <p class="price">{price}</p>
        <a class="order-btn" href="https://wa.me/{wa_number}?text={order_msg}" target="_blank">
          اطلب على واتساب 💬
        </a>
      </div>"""
        )
    return "\n".join(cards)


def generate_page(user_id: int, data: dict) -> Path:
    """يبني صفحة HTML من القالب ويحفظها في pages/"""
    field_emoji, field_label = FIELDS[data["field"]]
    wa_number = data["wa_number"]
    general_msg = quote(f"السلام عليكم 👋 عايز أستفسر عن منتجات {data['business_name']}")

    html_page = TEMPLATE.substitute(
        business_name=escape(data["business_name"]),
        field_emoji=field_emoji,
        field_label=escape(field_label),
        products_html=build_products_html(data["products"], data["field"], wa_number),
        wa_link_general=f"https://wa.me/{wa_number}?text={general_msg}",
        year=time.strftime("%Y"),
    )

    path = PAGES_DIR / f"page_{user_id}_{int(time.time())}.html"
    path.write_text(html_page, encoding="utf-8")
    return path


# ------------------------- مراحل البوت -------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton(f"{e} {label}", callback_data=key)]
        for key, (e, label) in FIELDS.items()
    ]
    await update.message.reply_text(
        "أهلاً بيك! 👋\n\n"
        "أنا بوت بعملك صفحة إنترنت جاهزة لنشاطك التجاري في دقيقة.\n"
        "الصفحة فيها منتجاتك وزرار طلب على واتساب.\n\n"
        "الأول: نشاطك في أي مجال؟",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSING_FIELD


async def choose_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["field"] = query.data
    context.user_data["products"] = []
    await query.edit_message_text("تمام 👌 إيه اسم النشاط بتاعك؟")
    return BUSINESS_NAME


async def get_business_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["business_name"] = update.message.text.strip()
    await update.message.reply_text(
        "جميل 👌 ابعتلي رقم الواتساب اللي العملاء هيطلبوا عليه "
        "(بأي صيغة، مثلاً: 01012345678)"
    )
    return WA_NUMBER


async def get_wa_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    number = normalize_whatsapp(update.message.text)
    if len(number) < 10:
        await update.message.reply_text("الرقم ده مش واضح 🤔 ابعته تاني زي: 01012345678")
        return WA_NUMBER
    context.user_data["wa_number"] = number
    await update.message.reply_text(
        "تمام ✅ دلوقتي ابعت اسم أول منتج أو خدمة عندك (مثلاً: ترابيزة سفرة ٦ كراسي)"
    )
    return PRODUCT_NAME


async def get_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["current_product"] = update.message.text.strip()
    await update.message.reply_text("سعره كام؟ (مثلاً: 4500 جنيه)")
    return PRODUCT_PRICE


async def get_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["products"].append(
        {
            "name": context.user_data["current_product"],
            "price": update.message.text.strip(),
        }
    )
    keyboard = [
        [
            InlineKeyboardButton("➕ ضيف منتج تاني", callback_data="more"),
            InlineKeyboardButton("✅ خلاص، اعمل الصفحة", callback_data="done"),
        ]
    ]
    await update.message.reply_text(
        f"اتسجل ✅ عندك دلوقتي {len(context.user_data['products'])} منتج.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ADD_MORE


async def add_more(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "more":
        await query.edit_message_text("ابعت اسم المنتج اللي بعده:")
        return PRODUCT_NAME

    # العميل خلّص: اعمل الصفحة
    await query.edit_message_text("ثانية واحدة بعملك الصفحة… ⚙️")
    try:
        path = generate_page(update.effective_user.id, context.user_data)
    except Exception:
        logger.exception("page generation failed")
        await query.message.reply_text(
            "حصلت مشكلة وأنا بعمل الصفحة 😅 جرّب تاني بـ /start"
        )
        return ConversationHandler.END

    await query.message.reply_document(
        document=path.open("rb"),
        filename=f"{context.user_data['business_name']}.html",
        caption=(
            "صفحتك جاهزة 🎉\n\n"
            "افتح الملف في المتصفح وشوفه. تقدر ترفعه على أي استضافة مجانية "
            "زي GitHub Pages أو Netlify Drop ويبقى لينك شغال لأي حد.\n\n"
            "عايز تعمل صفحة تانية؟ /start"
        ),
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("تم الإلغاء 👌 لو حبيت تبدأ من الأول: /start")
    return ConversationHandler.END




# ------------------------- سيرفر keep-alive للاستضافة -------------------------

def _start_keepalive_server() -> None:
    """سيرفر HTTP بسيط عشان الاستضافة المجانية تعتبر الخدمة شغالة
    وعشان أداة المراقبة (UptimeRobot) تظق عليه فما ينامش."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    port = int(os.getenv("PORT", "8080"))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write("البوت شغال ✅".encode("utf-8"))

        def log_message(self, *args):
            pass

    server = HTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    logger.info("keep-alive server on port %s", port)

# ------------------------- التشغيل -------------------------

def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit(
            "مفيش TELEGRAM_BOT_TOKEN! اعمل ملف .env وحط فيه التوكن "
            "(شوف .env.example و README)"
        )

    _start_keepalive_server()

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_FIELD: [CallbackQueryHandler(choose_field)],
            BUSINESS_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_business_name)
            ],
            WA_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_wa_number)
            ],
            PRODUCT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_product_name)
            ],
            PRODUCT_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_product_price)
            ],
            ADD_MORE: [CallbackQueryHandler(add_more)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    logger.info("البوت شغال…")
    app.run_polling()


if __name__ == "__main__":
    main()
