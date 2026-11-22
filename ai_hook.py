"""
(اختياري) وصف ذكي للمنتجات بالذكاء الاصطناعي.

البوت شغال 100% من غير الملف ده ولا أي مفتاح.
لو حبيت تفعّل الوصف الذكي:
  1. سجّل في أي خدمة ذكاء اصطناعي (OpenAI أو غيرها) وخد API key.
  2. حط المفتاح في ملف .env كده:
       AI_API_KEY=المفتاح_هنا
  3. فعّل الكود اللي تحت في describe_product.

لو مفيش مفتاح، الدالة بترجع None والبوت بيستخدم وصف بسيط تلقائي.
"""

import os

AI_API_KEY = os.getenv("AI_API_KEY")


def describe_product(field: str, name: str, price: str):
    """يرجّع جملة وصف قصيرة للمنتج، أو None لو الذكاء الاصطناعي مش مفعّل."""
    if not AI_API_KEY:
        return None

    # ---------------------------------------------------------
    # مثال جاهز (OpenAI) — شيل علامات التعليق وثبّت مكتبة openai:
    #
    #   pip install openai
    #
    # from openai import OpenAI
    # client = OpenAI(api_key=AI_API_KEY)
    # try:
    #     r = client.chat.completions.create(
    #         model="gpt-4o-mini",
    #         messages=[{
    #             "role": "user",
    #             "content": (
    #                 f"اكتب وصف تسويقي قصير جداً (جملة واحدة) بالعامية "
    #                 f"المصرية لمنتج اسمه: {name}"
    #             ),
    #         }],
    #         max_tokens=60,
    #     )
    #     return r.choices[0].message.content.strip()
    # except Exception:
    #     return None  # أي مشكلة في الخدمة؟ البوت يفضل شغال عادي
    # ---------------------------------------------------------

    return None
