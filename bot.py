import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Set

import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =========================================================
# НАСТРОЙКИ
# =========================================================
TOKEN = os.getenv("TOKEN")
DIGISELLER_COOKIE = os.getenv("COOKIE")

DIGISELLER_NEGATIVE_URL = "https://my.digiseller.com/inside/responses.asp?gb=2&shop=-1"
DIGISELLER_BASE_URL = "https://my.digiseller.com/inside/"
CHECK_INTERVAL_SECONDS = 60

USERS_FILE = "users.json"
SENT_REVIEWS_FILE = "sent_reviews.json"
ANNOUNCEMENTS_FILE = "announcements.json"
SHIFT_STATUS_FILE = "shift_status.json"
PROFILES_FILE = "profiles.json"

# =========================================================
# АДМИНЫ
# =========================================================
ADMIN_IDS = [781922474, 135479524, 5384930958]

# =========================================================
# РАБОТНИКИ ПО ПЛАТФОРМАМ
# =========================================================
AI_WORKERS = [8225013907, 8177004956, 781922474]
STEAM_WORKERS = [7135999120, 742038308]

ALL_KNOWN_WORKERS = sorted(set(AI_WORKERS + STEAM_WORKERS))

# =========================================================
# ИНСТРУКЦИИ
# =========================================================
DATA = {
    "chatgpt": {
        "title": "ChatGPT",
        "items": {
            "payment_link_problem": {
                "button": "Ссылка ведет в чат",
                "text": (
                    "❕По вашей ссылке не открывается страница оплаты, а перекидывает в чат ChatGPT 💭\n"
                    "📌 Ниже — инструкция, как отправить правильную ссылку, чтобы мы оформили ваш заказ ✅\n\n"
                    "‼️ Если у Вас не получается сгенерировать ссылку на оплату, воспользуйтесь инструкцией. "
                    "В ней описан способ формирования ссылки через \"Окно разработчика (F12)\" в случае ошибки ‼️\n\n"
                    "https://teletype.in/@fursovstore/Y3WYK7-OYFQ"
                )
            },
            "disable_autorenew": {
                "button": "Отключить автопродление",
                "text": (
                    "Просим Вас отключить авто-продление подписки\n"
                    "В конце месяца ChatGPT автоматически пытается продлить подписку.\n"
                    "При неуспешных попытках оплаты наш мерчант списывает $0.14 за каждую попытку "
                    "(да, даже если карта пустая).\n"
                    "Ниже — простая инструкция, как это сделать 👇\n\n"
                    "Как отключить автопродление подписки ChatGPT ❓\n\n"
                    "Сделайте следующее:\n"
                    "1️⃣ Нажмите на иконку профиля\n"
                    "2️⃣ Перейдите в Настройки\n"
                    "3️⃣ Откройте раздел Учётная запись\n"
                    "4️⃣ Пролистайте вниз до блока Оплата\n"
                    "5️⃣ Нажмите Управление\n"
                    "6️⃣ Откроется страница управления подпиской\n"
                    "7️⃣ Нажмите «Отменить подписку» и подтвердите\n\n"
                    "❗️ Про отмену:\n"
                    "Подписка НЕ отменяется сразу — она будет действовать до конца уже оплаченного периода, "
                    "просто автопродление отключится.\n\n"
                    "Очень надеемся на ваше понимание ❤️"
                )
            },
            "twelve_months_problem": {
                "button": "12 месяцев массово слетает",
                "text": (
                    "Здравствуйте!\n\n"
                    "На данный момент у ChatGPT временно отключена возможность продления подписок сразу на 12 месяцев — "
                    "это общая ситуация у всех, не только по вашему заказу.\n\n"
                    "Чтобы вы не теряли доступ, мы уже подготовили решение:\n"
                    "✅ Сейчас оформим вам подписку на 1 месяц\n"
                    "🔁 Далее просто пишите нам в этот чат, и мы будем продлевать её ежемесячно "
                    "в рамках уже оплаченного вами срока\n\n"
                    "Ничего дополнительно оплачивать не потребуется.\n\n"
                    "То есть по факту для вас ничего не меняется — подписка просто будет идти помесячно вместо годовой.\n\n"
                    "Если в дальнейшем ситуация изменится:\n"
                    "— предложим альтернативный вариант\n"
                    "или\n"
                    "— сделаем перерасчёт за оставшийся период\n\n"
                    "Выполните следующие действия:\n"
                    "➖ Зайдите в свой аккаунт ChatGPT (если ещё не вошли — просто авторизуйтесь).\n"
                    "➖ Перейдите по ссылке https://chatgpt.com/api/auth/session\n"
                    "➖ Скопируйте весь текст, который откроется на странице.\n"
                    "Отправьте содержимое ссылки в чат."
                )
            }
        }
    },
    "claude": {
        "title": "Claude",
        "items": {
            "appeal_block": {
                "button": "Апелляция при блокировке",
                "text": (
                    "❗️Инструкция по подаче апелляции, если Claude заблокировал аккаунт\n\n"
                    "Если при входе вы видите ошибку:\n\n"
                    "Your account has been disabled after an automatic review of your recent activities.”\n\n"
                    "нужно подать апелляцию вручную.\n\n"
                    "1. Откройте официальную статью Anthropic:\n"
                    "https://support.claude.com/en/articles/8241253-safeguards-warnings-and-appeals\n\n"
                    "2. Откройте форму апелляции:\n"
                    "https://docs.google.com/forms/d/e/1FAIpQLSdcTocgFJXSJzFJzVc47nxKmjeVhXDfgRaifH3DUZhYarA8vA/viewform\n\n"
                    "3. Заполните поля:\n\n"
                    "Email — ваша почта для связи\n"
                    "Name — ваше имя\n"
                    "Email associated with your account — почта, на которую зарегистрирован аккаунт Claude\n"
                    "Message — вставьте текст ниже\n\n"
                    "4. Текст для поля Message:\n\n"
                    "Hello,\n\n"
                    "My Claude account was disabled and I received the following message:\n\n"
                    "“Your account has been disabled after an automatic review of your recent activities.”\n\n"
                    "I believe this may be a mistake and I would like to request a manual review of my account.\n\n"
                    "I am a regular user with a paid subscription, and to the best of my knowledge I did not intentionally violate your Terms of Service or Usage Policy.\n\n"
                    "Please review my account and let me know whether it can be restored. If not, I would appreciate any clarification about the reason for the disablement.\n\n"
                    "Thank you.\n\n"
                    "5. После отправки формы ожидайте ответ от поддержки.\n"
                    "Лучше не отправлять много одинаковых заявок подряд, чтобы не устроить support’у мини-DDoS из апелляций.\n\n"
                    "В случае отказа в разблокировке - сообщите нам"
                )
            },
            "org_id_request": {
                "button": "Запрос Organization ID",
                "text": (
                    "Здравствуйте! 👋\n\n"
                    "Для активации подписки Claude нам нужен ваш Organization ID.\n\n"
                    "⚠️ Перед отправкой обязательно проверьте: у вас должен быть FREE Plan (без активной подписки).\n"
                    "Если старая подписка еще действует или висит неоплаченный счет — сначала отмените её и дождитесь окончания периода. "
                    "Иначе активация может пройти, но подписка не отобразится, возврата в данном случае нет.\n\n"
                    "Как найти Organization ID:\n"
                    "1. Зайдите на сайт Claude\n"
                    "2. Войдите в аккаунт\n"
                    "3. Нажмите на иконку профиля справа сверху\n"
                    "4. Откройте Settings\n"
                    "5. Пролистайте до раздела Account\n"
                    "6. Скопируйте Organization ID\n"
                    "7. Отправьте нам этот код в ответном сообщении\n\n"
                    "Как только пришлёте ID — двигаемся дальше 🚀"
                )
            },
            "blocked_template": {
                "button": "Шаблон: аккаунт заблокирован",
                "text": (
                    "Здравствуйте!\n\n"
                    "На данный момент по подпискам Claude наблюдается волна блокировок со стороны сервиса. "
                    "К сожалению, это происходит независимо от нас и может затрагивать часть аккаунтов.\n\n"
                    "В рамках гарантии мы готовы предоставить вам новую подписку взамен.\n\n"
                    "Для этого, пожалуйста, выберите удобный вариант:\n"
                    " • 📧 Предоставить почту Gmail — мы зарегистрируем новый аккаунт и оформим подписку\n"
                    " • 🔑 Предоставить уже существующий аккаунт — мы оформим подписку на него\n\n"
                    "После получения данных мы сразу передадим ваш заказ в работу.\n\n"
                    "Приносим извинения за доставленные неудобства и благодарим за понимание!"
                )
            },
            "activation_x5_x20": {
                "button": "Активация Claude x5-x20",
                "text": (
                    "Инструкция по активации Claude х5 - х20\n\n"
                    "1. Скачать расширение: https://editcookie.com\n"
                    "2. Войти в аккаунт Claude\n"
                    "3. Обновить страницу\n"
                    "4. Открыть расширение (иконка cookie)\n"
                    "5. Найти sessionKey и скопировать значение\n"
                    "6. Перейти: https://receipt.nitro.xin/redeem/claude\n"
                    "7. Вставить CDK и sessionKey\n"
                    "8. Нажать \"Активировать\"\n\n"
                    "Подписка появится через 2–5 минут\n"
                    "Если не появилась — перезайти в аккаунт"
                )
            },
            "service_errors": {
                "button": "Сбой Claude",
                "text": (
                    "На данный момент на серверах сервиса Claude наблюдаются временные технические сбои. "
                    "В связи с этим не удается осуществить вход в аккаунт.\n\n"
                    "Ваш заказ принят в работу, однако его обработка может занять немного больше времени, чем обычно"
                )
            }
        }
    },
    "grok": {
        "title": "Grok",
        "items": {
            "technical_issues": {
                "button": "Технические сбои",
                "text": (
                    "Здравствуйте!\n\n"
                    "В настоящий момент в сервисе Grok наблюдаются временные технические сбои, "
                    "из-за чего возникают сложности с оплатой подписок.\n\n"
                    "В связи с этим выполнение заказа может занять до 24–48 часов — до полного устранения проблемы со стороны сервиса.\n\n"
                    "Вы можете выбрать один из вариантов:\n"
                    "• ожидание активации подписки;\n"
                    "• полный возврат средств.\n\n"
                    "Если вы выбираете возврат, пожалуйста, сообщите нам об этом — мы сразу отправим заявку, "
                    "и средства поступят вам в течение 24–48 часов.\n\n"
                    "Благодарим за понимание и терпение 🤝"
                )
            }
        }
    },
    "spotify": {
        "title": "Spotify",
        "items": {
            "facebook_email_password": {
                "button": "Вход через Facebook",
                "text": (
                    "Если ваш аккаунт был создан через Facebook, но вы хотите использовать вход по электронной почте и паролю, выполните следующие шаги:\n\n"
                    "Войдите в аккаунт через Facebook\n"
                    "Перейдите на сайт Spotify: https://www.spotify.com/account\n"
                    "Авторизуйтесь с помощью Facebook.\n\n"
                    "Проверьте электронную почту\n"
                    "На странице \"Обзор аккаунта\" (Account Overview) убедитесь, что в аккаунте указана актуальная почта.\n"
                    "При необходимости измените её в разделе редактирования профиля.\n\n"
                    "Установите пароль\n"
                    "Перейдите на страницу сброса пароля: https://www.spotify.com/password-reset/\n"
                    "Введите указанную в аккаунте почту, получите письмо и задайте новый пароль.\n\n"
                    "Используйте почту и пароль для входа\n"
                    "После этого вы сможете входить в Spotify напрямую — по почте и паролю, без использования Facebook."
                )
            }
        }
    },
    "kling": {
        "title": "Kling",
        "items": {
            "payment_link": {
                "button": "Как вытащить ссылку",
                "text": (
                    "Здравствуйте. Как вытащить ссылку на оплату в Kling AI\n"
                    "Нажать кнопку Plans from 6.99\n"
                    "В открывшемся окне выбрать подходящую подписку и нажать по ней\n"
                    "Как откроется окно оплаты скинуть в чат"
                )
            }
        }
    },
    "midjourney": {
        "title": "Midjourney",
        "items": {
            "avoid_block": {
                "button": "Как избежать блокировки",
                "text": (
                    "🎨 Как избежать блокировки Midjourney после оплаты\n\n"
                    "В связи с участившимися блокировками аккаунтов - настоятельно рекомендуем выполнить следующие действия:\n\n"
                    "🛑 Отключите автопродление подписки (если оплачивали по ссылке):\n\n"
                    "🔧 Как отменить (Прикреплен скриншот):\n"
                    "1. Нажмите на аватарку → Manage Subscription\n"
                    "2. Выберите вкладку View Invoices\n"
                    "3. Нажмите кнопку «Отменить подписку»\n"
                    "4. Подтвердите отмену ещё раз\n\n"
                    "📌 Подписка продолжит работать до конца оплаченного срока - ничего не сгорит!\n\n"
                    "📌 Рекомендации по использованию:\n"
                    "✅ Используйте только сайт Midjourney (https://www.midjourney.com) - не работайте напрямую через Discord-бота\n"
                    "❌ Не используйте скрипты, боты, сторонние API - даже если кажется удобно\n"
                    "🚫 Промты на темы NSFW, насилия, токсичности, политических провокаций — могут привести к мгновенной блокировке\n"
                    "💬 Не отправляйте слишком много запросов подряд - система может воспринять это как автоматизацию\n"
                    "🔒 Не делитесь своим аккаунтом с друзьями и коллегами - особенно с неизвестными или через VPN с подозрительными локациями\n\n"
                    "⚠️ Midjourney строго следит за соблюдением правил - блокировки часто происходят без предупреждений и без возврата средств."
                )
            }
        }
    }
}

# =========================================================
# ХРАНЕНИЕ
# =========================================================
def load_json_file(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json_file(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_users() -> Set[int]:
    raw = load_json_file(USERS_FILE, [])
    result = set()
    for item in raw:
        try:
            result.add(int(item))
        except Exception:
            continue
    return result


def save_users(users: Set[int]) -> None:
    save_json_file(USERS_FILE, sorted(users))


def load_sent_reviews() -> Set[str]:
    raw = load_json_file(SENT_REVIEWS_FILE, [])
    return set(str(x) for x in raw)


def save_sent_reviews(review_ids: Set[str]) -> None:
    save_json_file(SENT_REVIEWS_FILE, sorted(review_ids))


def load_announcements() -> Dict[str, dict]:
    return load_json_file(ANNOUNCEMENTS_FILE, {})


def save_announcements(data: Dict[str, dict]) -> None:
    save_json_file(ANNOUNCEMENTS_FILE, data)


def load_shift_status() -> Dict[str, bool]:
    return load_json_file(SHIFT_STATUS_FILE, {})


def save_shift_status(data: Dict[str, bool]) -> None:
    save_json_file(SHIFT_STATUS_FILE, data)


def load_profiles() -> Dict[str, dict]:
    return load_json_file(PROFILES_FILE, {})


def save_profiles(data: Dict[str, dict]) -> None:
    save_json_file(PROFILES_FILE, data)


USERS: Set[int] = load_users()
SENT_REVIEWS: Set[str] = load_sent_reviews()
ANNOUNCEMENTS: Dict[str, dict] = load_announcements()
SHIFT_STATUS: Dict[str, bool] = load_shift_status()
USER_PROFILES: Dict[str, dict] = load_profiles()

# =========================================================
# КЛАВИАТУРЫ
# =========================================================
def services_keyboard():
    builder = InlineKeyboardBuilder()
    for service_key, service_data in DATA.items():
        builder.button(text=service_data["title"], callback_data=f"service:{service_key}")
    builder.adjust(2)
    return builder.as_markup()


def instructions_keyboard(service_key: str):
    builder = InlineKeyboardBuilder()
    for item_key, item_data in DATA[service_key]["items"].items():
        builder.button(text=item_data["button"], callback_data=f"item:{service_key}:{item_key}")
    builder.button(text="⬅️ Назад", callback_data="back_main")
    builder.adjust(1)
    return builder.as_markup()


def back_to_list_keyboard(service_key: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ К списку инструкций", callback_data=f"service:{service_key}")
    builder.button(text="🏠 В главное меню", callback_data="back_main")
    builder.adjust(1)
    return builder.as_markup()


def acknowledge_keyboard(announcement_id: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ознакомлен", callback_data=f"ack:{announcement_id}")
    builder.adjust(1)
    return builder.as_markup()


# =========================================================
# HELPER
# =========================================================
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def update_profile_from_user(user) -> None:
    user_id = str(user.id)
    USER_PROFILES[user_id] = {
        "username": user.username or "",
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_profiles(USER_PROFILES)


def get_profile_text(user_id: int) -> str:
    profile = USER_PROFILES.get(str(user_id), {})
    username = profile.get("username") or "нет"
    first_name = profile.get("first_name") or ""
    last_name = profile.get("last_name") or ""
    full_name = f"{first_name} {last_name}".strip() or "не указано"
    shift = "на смене" if SHIFT_STATUS.get(str(user_id), False) else "не на смене"
    return f"ID: {user_id} | @{username} | {full_name} | {shift}"


def get_platform_users(platform: str) -> List[int]:
    platform = platform.lower()
    if platform == "ai":
        return AI_WORKERS
    if platform == "steam":
        return STEAM_WORKERS
    if platform == "all":
        return sorted(set(AI_WORKERS + STEAM_WORKERS))
    return []


def get_deadline_text_for_user(user_id: int) -> str:
    if SHIFT_STATUS.get(str(user_id), False):
        return "⏰ Срок ознакомления: в течение 1 часа, так как вы отмечены как сотрудник на смене."
    return "⏰ Срок ознакомления: до начала вашей следующей смены."


def admin_commands_text() -> str:
    return (
        "👑 Список команд администратора\n\n"
        "/admin — список админ-команд\n"
        "/users — количество активированных пользователей\n"
        "/list_users — список пользователей бота с ID\n"
        "/workers_ai — список AI-воркеров\n"
        "/workers_steam — список Steam-воркеров\n"
        "/news <ai|steam|all> <текст> — рассылка новости по платформе\n"
        "/fine <user_id> <сумма> <причина> — отправить штраф сотруднику\n\n"
        "Команды работников:\n"
        "/shift_on — отметить себя на смене\n"
        "/shift_off — снять себя со смены\n"
        "/start — активация бота\n"
        "/id — показать свой ID"
    )


# =========================================================
# DIGISELLER
# =========================================================
def digiseller_headers() -> Dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0",
        "Cookie": DIGISELLER_COOKIE or "",
        "Referer": "https://my.digiseller.com/",
    }


def fetch_url(url: str) -> str:
    response = requests.get(url, headers=digiseller_headers(), timeout=30)
    response.raise_for_status()
    response.encoding = response.encoding or "utf-8"
    return response.text


def get_negative_review_links() -> List[Dict[str, str]]:
    html = fetch_url(DIGISELLER_NEGATIVE_URL)
    soup = BeautifulSoup(html, "html.parser")

    found = []
    seen = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "response.asp?id_r=" not in href:
            continue

        match = re.search(r"id_r=(\d+)", href)
        if not match:
            continue

        review_id = match.group(1)
        if review_id in seen:
            continue
        seen.add(review_id)

        full_link = href
        if not href.startswith("http"):
            full_link = DIGISELLER_BASE_URL + href.lstrip("/")

        found.append({"id": review_id, "link": full_link})

    return found


def extract_field(text: str, field_name: str) -> str:
    pattern = rf"{re.escape(field_name)}\s*:\s*(.+)"
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()
    return "Не найдено"


def normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"\r", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_review_page(review_url: str) -> Dict[str, str]:
    html = fetch_url(review_url)
    soup = BeautifulSoup(html, "html.parser")
    raw_text = normalize_text(soup.get_text("\n"))

    invoice = extract_field(raw_text, "Номер счета")
    product = extract_field(raw_text, "Товар")
    buyer = extract_field(raw_text, "Покупатель")

    review_text = "Не найдено"
    review_patterns = [
        r"Отзыв\s*:\s*-+\s*(.+)",
        r"Отзыв\s*:\s*(.+)"
    ]

    for pattern in review_patterns:
        match = re.search(pattern, raw_text, flags=re.DOTALL)
        if match:
            review_text = match.group(1).strip()
            break

    review_text = re.sub(r"\n{3,}", "\n\n", review_text).strip()

    return {
        "invoice": invoice,
        "product": product,
        "buyer": buyer,
        "review_text": review_text,
        "url": review_url
    }


def build_review_message(review: Dict[str, str]) -> str:
    return (
        "❌ Покупатель оставил отрицательный отзыв\n"
        f"{review['url']}\n\n"
        f"Номер счета: {review['invoice']}\n"
        f"Товар: {review['product']}\n"
        f"Покупатель: {review['buyer']}\n"
        "Отзыв:\n"
        "-------------------------------------\n"
        f"{review['review_text']}"
    )


# =========================================================
# РАССЫЛКА
# =========================================================
async def broadcast_to_all_users(bot: Bot, text: str) -> None:
    for user_id in USERS:
        try:
            await bot.send_message(chat_id=user_id, text=text, disable_web_page_preview=True)
        except Exception as e:
            logging.warning(f"Не удалось отправить пользователю {user_id}: {e}")


async def monitor_negative_reviews(bot: Bot):
    await asyncio.sleep(5)

    while True:
        try:
            if not DIGISELLER_COOKIE:
                logging.warning("COOKIE не задана")
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)
                continue

            reviews = await asyncio.to_thread(get_negative_review_links)

            for review_meta in reviews:
                review_id = review_meta["id"]

                if review_id in SENT_REVIEWS:
                    continue

                review_data = await asyncio.to_thread(parse_review_page, review_meta["link"])
                message_text = build_review_message(review_data)

                await broadcast_to_all_users(bot, message_text)

                SENT_REVIEWS.add(review_id)
                save_sent_reviews(SENT_REVIEWS)

        except Exception as e:
            logging.exception(f"Ошибка мониторинга отзывов: {e}")

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


# =========================================================
# ХЕНДЛЕРЫ
# =========================================================
async def start_handler(message: Message):
    user_id = message.chat.id
    username = message.from_user.username
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()

    update_profile_from_user(message.from_user)

    is_new = user_id not in USERS
    if is_new:
        USERS.add(user_id)
        save_users(USERS)

    await message.answer(
        f"✅ Вы активировали бота.\n"
        f"Ваш user ID: {user_id}\n\n"
        f"Теперь вам будут приходить новые отрицательные отзывы Digiseller.\n"
        f"Также можете открыть список инструкций ниже:",
        reply_markup=services_keyboard()
    )

    admin_text = (
        "👤 Сотрудник нажал /start\n\n"
        f"ID: {user_id}\n"
        f"Username: @{username if username else 'нет'}\n"
        f"Имя: {full_name or 'не указано'}\n"
        f"Статус: {'Новый пользователь' if is_new else 'Повторный /start'}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(admin_id, admin_text)
        except Exception as e:
            logging.warning(f"Не удалось отправить уведомление админу {admin_id}: {e}")


async def id_handler(message: Message):
    await message.answer(f"Ваш user ID: {message.chat.id}")


async def admin_handler(message: Message):
    if not is_admin(message.chat.id):
        await message.answer("У вас нет доступа к этой команде.")
        return
    await message.answer(admin_commands_text())


async def users_count_handler(message: Message):
    if not is_admin(message.chat.id):
        await message.answer("У вас нет доступа к этой команде.")
        return
    await message.answer(f"Активированных пользователей: {len(USERS)}")


async def list_users_handler(message: Message):
    if not is_admin(message.chat.id):
        await message.answer("У вас нет доступа к этой команде.")
        return

    if not USERS:
        await message.answer("Пользователей пока нет.")
        return

    lines = ["📋 Пользователи бота:\n"]
    for user_id in sorted(USERS):
        lines.append(get_profile_text(user_id))

    text = "\n".join(lines)
    if len(text) > 4000:
        for chunk_start in range(0, len(text), 3500):
            await message.answer(text[chunk_start:chunk_start + 3500])
    else:
        await message.answer(text)


async def workers_ai_handler(message: Message):
    if not is_admin(message.chat.id):
        await message.answer("У вас нет доступа к этой команде.")
        return

    lines = ["🤖 AI-воркеры:\n"]
    for user_id in AI_WORKERS:
        lines.append(get_profile_text(user_id))
    await message.answer("\n".join(lines))


async def workers_steam_handler(message: Message):
    if not is_admin(message.chat.id):
        await message.answer("У вас нет доступа к этой команде.")
        return

    lines = ["🎮 Steam-воркеры:\n"]
    for user_id in STEAM_WORKERS:
        lines.append(get_profile_text(user_id))
    await message.answer("\n".join(lines))


async def shift_on_handler(message: Message):
    user_id = message.chat.id
    SHIFT_STATUS[str(user_id)] = True
    save_shift_status(SHIFT_STATUS)
    update_profile_from_user(message.from_user)
    await message.answer("🟢 Вы отмечены как сотрудник на смене.")


async def shift_off_handler(message: Message):
    user_id = message.chat.id
    SHIFT_STATUS[str(user_id)] = False
    save_shift_status(SHIFT_STATUS)
    update_profile_from_user(message.from_user)
    await message.answer("🔴 Вы отмечены как сотрудник вне смены.")


async def news_handler(message: Message):
    if not is_admin(message.chat.id):
        await message.answer("У вас нет доступа к этой команде.")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "Использование:\n"
            "/news ai текст\n"
            "/news steam текст\n"
            "/news all текст"
        )
        return

    platform = parts[1].lower()
    news_text = parts[2]

    target_users = get_platform_users(platform)
    if not target_users:
        await message.answer("Платформа не найдена. Используй: ai, steam, all")
        return

    announcement_id = str(int(asyncio.get_event_loop().time() * 1000))
    ANNOUNCEMENTS[announcement_id] = {
        "text": news_text,
        "platform": platform,
        "acked_by": []
    }
    save_announcements(ANNOUNCEMENTS)

    sent_count = 0
    for user_id in target_users:
        try:
            deadline_text = get_deadline_text_for_user(user_id)
            await message.bot.send_message(
                user_id,
                f"📢 Новая информация от администратора\n"
                f"Платформа: {platform.upper()}\n\n"
                f"{news_text}\n\n"
                f"{deadline_text}",
                reply_markup=acknowledge_keyboard(announcement_id)
            )
            sent_count += 1
        except Exception as e:
            logging.warning(f"Не удалось отправить новость пользователю {user_id}: {e}")

    await message.answer(
        f"✅ Новость отправлена.\n"
        f"Платформа: {platform}\n"
        f"Получателей: {sent_count}"
    )


async def fine_handler(message: Message):
    if not is_admin(message.chat.id):
        await message.answer("У вас нет доступа к этой команде.")
        return

    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.answer("Использование:\n/fine user_id сумма причина")
        return

    try:
        target_user_id = int(parts[1])
    except ValueError:
        await message.answer("Неверный user_id.")
        return

    amount = parts[2]
    reason = parts[3]

    fine_text = (
        "⚠️ Вам назначен штраф\n\n"
        f"Сумма штрафа: {amount}\n"
        f"Причина: {reason}"
    )

    try:
        await message.bot.send_message(target_user_id, fine_text)
        await message.answer(f"✅ Штраф отправлен пользователю {target_user_id}.")
    except Exception as e:
        await message.answer(f"Не удалось отправить штраф: {e}")


async def acknowledge_handler(callback: CallbackQuery):
    _, announcement_id = callback.data.split(":", 1)

    if announcement_id not in ANNOUNCEMENTS:
        await callback.answer("Сообщение не найдено", show_alert=True)
        return

    user_id = callback.from_user.id
    update_profile_from_user(callback.from_user)

    acked_by = ANNOUNCEMENTS[announcement_id].get("acked_by", [])

    if user_id in acked_by:
        await callback.answer("Вы уже подтвердили", show_alert=True)
        return

    acked_by.append(user_id)
    ANNOUNCEMENTS[announcement_id]["acked_by"] = acked_by
    save_announcements(ANNOUNCEMENTS)

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.answer("Принято")
    await callback.message.answer("✅ Вы подтвердили ознакомление.")

    notify_text = (
        "✅ Сотрудник ознакомился с информацией\n\n"
        f"{get_profile_text(user_id)}\n"
        f"Текст: {ANNOUNCEMENTS[announcement_id]['text'][:300]}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await callback.bot.send_message(admin_id, notify_text)
        except Exception as e:
            logging.warning(f"Не удалось отправить подтверждение админу {admin_id}: {e}")


async def service_handler(callback: CallbackQuery):
    service_key = callback.data.split(":")[1]

    if service_key not in DATA:
        await callback.answer("Раздел не найден", show_alert=True)
        return

    await callback.message.edit_text(
        f"Вы выбрали: {DATA[service_key]['title']}\n\nВыберите инструкцию:",
        reply_markup=instructions_keyboard(service_key)
    )
    await callback.answer()


async def item_handler(callback: CallbackQuery):
    _, service_key, item_key = callback.data.split(":")

    if service_key not in DATA or item_key not in DATA[service_key]["items"]:
        await callback.answer("Инструкция не найдена", show_alert=True)
        return

    text = DATA[service_key]["items"][item_key]["text"]

    await callback.message.edit_text(
        text,
        reply_markup=back_to_list_keyboard(service_key),
        disable_web_page_preview=True
    )
    await callback.answer()


async def back_main_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выберите сервис:",
        reply_markup=services_keyboard()
    )
    await callback.answer()


# =========================================================
# ЗАПУСК
# =========================================================
async def main():
    if not TOKEN:
        raise ValueError("TOKEN не задан")

    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    dp.message.register(start_handler, CommandStart())
    dp.message.register(id_handler, Command("id"))
    dp.message.register(admin_handler, Command("admin"))
    dp.message.register(users_count_handler, Command("users"))
    dp.message.register(list_users_handler, Command("list_users"))
    dp.message.register(workers_ai_handler, Command("workers_ai"))
    dp.message.register(workers_steam_handler, Command("workers_steam"))
    dp.message.register(shift_on_handler, Command("shift_on"))
    dp.message.register(shift_off_handler, Command("shift_off"))
    dp.message.register(news_handler, Command("news"))
    dp.message.register(fine_handler, Command("fine"))

    dp.callback_query.register(acknowledge_handler, F.data.startswith("ack:"))
    dp.callback_query.register(service_handler, F.data.startswith("service:"))
    dp.callback_query.register(item_handler, F.data.startswith("item:"))
    dp.callback_query.register(back_main_handler, F.data == "back_main")

    asyncio.create_task(monitor_negative_reviews(bot))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())











