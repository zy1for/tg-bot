import asyncio
import html
import json
import logging
import os
import re
from datetime import datetime, timedelta, time
from typing import Dict, List, Set, Tuple
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =========================================================
# НАСТРОЙКИ
# =========================================================
TOKEN = os.getenv("TOKEN")
DIGISELLER_COOKIE = os.getenv("COOKIE")

STAFF_GROUP_ID = int(os.getenv("STAFF_GROUP_ID", "0"))

DISPLAY_NAMES = {
    781922474: "Диля",
    8177004956: "Костя",
    8225013907: "Кайсар",
    5646910006: "Миша",
    7443195793: "Тима",
    7135999120: "Расул",
    1920853728: "Эльвира",
    5493517866: "Бекболат",
    1312771702: "Максат",
    844359525: "Сико",
    742038308: "Далхат",
    1294614140: "Диас",
    1163420256: "Ибрагим",
}

WORKER_AREAS = {
    781922474: "Plati",        # Диля
    8177004956: "GGsel",       # Костя
    7443195793: "Plati",       # Тима
    1294614140: "GGsel",       # Диас
    844359525: "GGsel",        # Сико
    5646910006: "Plati",       # Миша
    8225013907: "GGsel",       # Кайсар
    1920853728: "FanPay AI",   # Эльвира
    1163420256: "GGsel",        # Ибрагим

    742038308: "Steam",        # Далхат
    5493517866: "Steam",       # Бекболат
    1312771702: "Steam",       # Максат
    7135999120: "Steam",       # Расул
}

MSK_TZ = ZoneInfo("Europe/Moscow")

DIGISELLER_NEGATIVE_URL = "https://my.digiseller.com/inside/responses.asp?gb=2&shop=-1"
DIGISELLER_BASE_URL = "https://my.digiseller.com/inside/"
DIGISELLER_DIALOGS_URL = "https://my.digiseller.com/inside/messages.asp"

CHECK_INTERVAL_SECONDS = 60
DIALOGS_CHECK_INTERVAL_SECONDS = 10
ABSENT_CHECK_INTERVAL_SECONDS = 60

USERS_FILE = "users.json"
SENT_REVIEWS_FILE = "sent_reviews.json"
ANNOUNCEMENTS_FILE = "announcements.json"
SHIFT_STATUS_FILE = "shift_status.json"
PROFILES_FILE = "profiles.json"
DIALOGS_STATE_FILE = "dialogs_state.json"
FINES_FILE = "fines.json"
SCORES_FILE = "scores.json"
SCHEDULE_FILE = "schedule.json"
PENDING_NEWS_FILE = "pending_news.json"
REQUESTS_FILE = "requests.json"

# =========================================================
# АДМИНЫ
# =========================================================
ADMIN_IDS = [781922474, 135479524, 5384930958]

# =========================================================
# ВОРКЕРЫ ПО ПЛАТФОРМАМ
# =========================================================
AI_WORKERS = [
    8177004956,   # Костя
    781922474,    # Диля
    7443195793,   # Тима
    1294614140,   # Диас
    844359525,    # Сико
    5646910006,   # Миша
    8225013907,   # Кайсар
]

STEAM_WORKERS = [
    742038308,    # Далхат
    5493517866,   # Бекболат
    1312771702,   # Максат
    7135999120,   # Расул
]

FANPAY_WORKERS = [
    1920853728,   # Эльвира
]

# =========================================================
# СМЕНЫ
# =========================================================
LATE_FINE_AMOUNT = 500
ABSENT_FINE_AMOUNT = 1000

DAY_SHIFT_START = time(11, 0)
DAY_SHIFT_EXACT_UNTIL = time(11, 0, 59)
DAY_SHIFT_LATE_AFTER = time(11, 15)
DAY_SHIFT_END = time(17, 29, 59)

EVENING_SHIFT_START = time(17, 30)
EVENING_SHIFT_EXACT_UNTIL = time(17, 30, 59)
EVENING_SHIFT_LATE_AFTER = time(17, 45)
EVENING_SHIFT_END = time(23, 59, 59)

# =========================================================
# ИНСТРУКЦИИ
# =========================================================
DATA = {
    "chatgpt": {
        "title": "🤖 ChatGPT",
        "items": {
            "payment_link_problem": {
                "button": "💳 Ссылка ведет в чат",
                "text": (
                    "❕По вашей ссылке не открывается страница оплаты, а перекидывает в чат ChatGPT 💭\n"
                    "📌 Ниже — инструкция, как отправить правильную ссылку, чтобы мы оформили ваш заказ ✅\n\n"
                    "‼️ Если у Вас не получается сгенерировать ссылку на оплату, воспользуйтесь инструкцией. "
                    "В ней описан способ формирования ссылки через \"Окно разработчика (F12)\" в случае ошибки ‼️\n\n"
                    "https://teletype.in/@fursovstore/Y3WYK7-OYFQ"
                )
            },
            "disable_autorenew": {
                "button": "🔁 Отключить автопродление",
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
                "button": "📅 12 месяцев массово слетает",
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
            },
            "euro_payment_link": {
                "button": "💶 Ссылка на оплату в евро",
                "text": (
                    "Сейчас у вас на аккаунте стоит оплата в Евро - нужно сменить на доллары либо тенге, "
                    "и заново сформировать ссылку на оплату. Мы оплачиваем только в долларовой/тенге валюте."
                )
            },
            "get_activation_token": {
                "button": "🔑 Получить токен для активации",
                "text": (
                    "➖ Зайдите в свой аккаунт ChatGPT (если ещё не вошли — просто авторизуйтесь).\n"
                    "➖ Перейдите по ссылке https://chatgpt.com/api/auth/session\n"
                    "➖ Скопируйте весь текст, который откроется на странице.\n"
                    "Отправьте содержимое ссылки в чат"
                )
            },
            "payment_card_link": {
                "button": "💳 Получить ссылку на оплату по карте",
                "text": (
                    "Пожалуйста, выполните следующие шаги:\n"
                    "1. Зайдите в свой аккаунт на официальном сайте.\n"
                    "2. Перейдите в раздел «Подписки».\n"
                    "3. Выберите нужный план.\n"
                    "4. В окне ввода данных карты скопируйте URL (ссылку из адресной строки браузера).\n"
                    "5. Отправьте её сюда в чат — я продолжу оформление."
                )
            },
            "appstore": {
                "button": "📱 Инструкция App Store",
                "text": (
                    "Откройте App Store на Айфон\n"
                    "2. Нажмите на иконку профиля\n"
                    "3. Пролистайте вниз и выйдите из своего аккаунта\n"
                    "4. Введите данные:\n\n"
                    "Логин:\n"
                    "Пароль:\n\n"
                    "5. Введите в поиске App Store: ChatGPT\n"
                    "6. Скачайте приложение\n"
                    "7. Выйдите из нашего аккаунта"
                )
            }
        }
    },
    "claude": {
        "title": "🧠 Claude",
        "items": {
            "appeal_block": {
                "button": "🛑 Апелляция при блокировке",
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
                "button": "🆔 Запрос Organization ID",
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
                "button": "♻️ Шаблон: аккаунт заблокирован",
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
                "button": "⚡ Активация Claude x5-x20",
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
                "button": "🧯 Сбой Claude",
                "text": (
                    "На данный момент на серверах сервиса Claude наблюдаются временные технические сбои. "
                    "В связи с этим не удается осуществить вход в аккаунт.\n\n"
                    "Ваш заказ принят в работу, однако его обработка может занять немного больше времени, чем обычно"
                )
            }
        }
    },
    "spotify": {
        "title": "🎵 Spotify",
        "items": {
            "facebook_email_password": {
                "button": "📘 Вход через Facebook",
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
            },
            "apple_email_password": {
                "button": "🍎 Вход через Apple ID",
                "text": (
                    "Как привязать электронную почту и пароль к аккаунту Spotify, зарегистрированному через Apple ID:\n\n"
                    "Если вы изначально создали аккаунт Spotify с помощью Apple ID, но теперь хотите входить через электронную почту и пароль, выполните следующие шаги:\n\n"
                    "1. Войдите в аккаунт Spotify через Apple\n"
                    "Перейдите на сайт: https://www.spotify.com/account\n\n"
                    "Выберите вход через Apple ID и авторизуйтесь.\n\n"
                    "2. Убедитесь, что в аккаунте указана действующая почта\n"
                    "На странице «Обзор аккаунта» (Account overview) проверьте, какая электронная почта указана.\n\n"
                    "Важно: если при регистрации вы выбрали опцию «Скрыть мой email» (Hide My Email), "
                    "у вас будет случайный адрес от Apple (например, xyz123@privaterelay.appleid.com).\n\n"
                    "Рекомендуется заменить его на ваш реальный адрес — для этого нажмите «Изменить» (Edit) рядом с полем email.\n\n"
                    "3. Установите пароль\n"
                    "Так как вы использовали Apple ID, пароль Spotify может не быть установлен. Чтобы его создать:\n\n"
                    "Перейдите на страницу сброса пароля:\n"
                    "https://www.spotify.com/password-reset/\n\n"
                    "Введите ту почту, которая указана в вашем аккаунте Spotify "
                    "(в том числе, если это адрес вида @privaterelay.appleid.com).\n\n"
                    "Пройдите по ссылке из письма и задайте новый пароль.\n\n"
                    "4. Вход через email и пароль\n"
                    "После установки пароля вы сможете входить в Spotify напрямую, используя вашу электронную почту и пароль — "
                    "без необходимости использовать Apple ID."
                )
            },
            "google_email_password": {
                "button": "🌐 Вход через Google",
                "text": (
                    "Как привязать почту и пароль к аккаунту Spotify (если используется вход через Google):\n\n"
                    "Если вы ранее регистрировались в Spotify через Google, но теперь хотите использовать вход "
                    "по электронной почте и паролю, выполните следующие шаги:\n\n"
                    "1. Перейдите в настройки аккаунта\n"
                    "Откройте сайт Spotify: https://www.spotify.com/account\n\n"
                    "Войдите в свой аккаунт через Google, как обычно.\n\n"
                    "2. Убедитесь, что в аккаунте указана электронная почта\n"
                    "На странице «Обзор аккаунта» (Account overview) проверьте, указана ли ваша электронная почта.\n\n"
                    "При необходимости вы можете изменить её в настройках.\n\n"
                    "3. Установите пароль для входа\n"
                    "Если вы регистрировались через Google, у вас может не быть установленного пароля. Чтобы его создать:\n\n"
                    "Перейдите на страницу сброса пароля:\n"
                    "https://www.spotify.com/password-reset/\n\n"
                    "Введите адрес электронной почты, указанный в вашем аккаунте.\n\n"
                    "Перейдите по ссылке в письме и задайте новый пароль.\n\n"
                    "4. Используйте email и пароль для входа\n"
                    "После установки пароля вы сможете входить в Spotify, используя вашу почту и заданный пароль — "
                    "без необходимости использовать Google-аккаунт."
                )
            },
            "payment_regions": {
                "button": "🌍 Регионы подписок",
                "text": (
                    "🔴 Регион оплаты подписки:\n"
                    "➖ Подписки Family (Все сроки) - Нигерия (Есть DJ AI и Подкасты)\n"
                    "➖ Подписка Индивидуал (Все сроки) - Нигерия (Есть DJ AI и Подкасты)\n"
                    "➖ Подписки Дуо (Все сроки) - Нигерия (Есть DJ AI и Подкасты)\n"
                    "➖ Подписки Platinum/Standard/Lite - Индия (подкасты есть на всех, DJ AI — только в Platinum)"
                )
            },
            "incorrect_data": {
                "button": "❌ Данные некорректны",
                "text": (
                    "Неверный логин или пароль. Ссылка на сброс пароля:\n\n"
                    "https://accounts.spotify.com/ru/password-reset"
                )
            },
            "appstore": {
                "button": "📱 Инструкция App Store",
                "text": (
                    "Откройте App Store на Айфон\n"
                    "2. Нажмите на иконку профиля\n"
                    "3. Пролистайте вниз и выйдите из своего аккаунта\n"
                    "4. Введите данные:\n\n"
                    "Логин:\n"
                    "Пароль:\n\n"
                    "5. Введите в поиске App Store: Spotify\n"
                    "6. Скачайте приложение\n"
                    "7. Выйдите из нашего аккаунта"
                )
            },
            "duo_different_regions": {
                "button": "👥 Spotify Duo разные регионы",
                "text": (
                    "Как добавить второй аккаунт в Spotify Duo, если регионы разные\n\n"
                    "ШАГ 1: Подготовь VPN с подключением к Нигерии\n"
                    " • Используй любой VPN с нигерийским сервером:\n"
                    " • Windscribe, Surfshark, ExpressVPN и т.п.\n"
                    " • Важно: подключать VPN нужно на устройстве, где ты будешь менять регион второго аккаунта и принимать приглашение.\n\n"
                    "⸻\n\n"
                    "ШАГ 2: Измени регион второго аккаунта на Нигерию\n"
                    " 1. Подключи VPN к Нигерии.\n"
                    " 2. Зайди во второй аккаунт Spotify: spotify.com/account. (https://www.spotify.com/account)\n"
                    " 3. Нажми Edit Profile / Редактировать профиль.\n"
                    " 4. В поле Country / Страна выбери Nigeria.\n"
                    " • Если поле недоступно — выйди из аккаунта и заново зайди под VPN, тогда оно появится.\n"
                    " 5. Сохрани изменения.\n\n"
                    "⸻\n\n"
                    "ШАГ 3: Прими приглашение от Duo\n"
                    " 1. На основном аккаунте (где Duo) зайди на: spotify.com/account/duo. (https://www.spotify.com/account/duo)\n"
                    " 2. Нажми “Send invite” / Отправить приглашение.\n"
                    " 3. Введи email второго аккаунта и отправь.\n"
                    " 4. На втором аккаунте:\n"
                    " • Открой письмо с приглашением.\n"
                    " • Перейди по ссылке.\n"
                    " • VPN на этом устройстве должен быть тоже включён и настроен на Нигерию.\n"
                    " • Введи тот же адрес, что указан в Duo (например: 12 Adebayo Street, Lagos).\n"
                    " • Подтверди.\n\n"
                    "⸻\n\n"
                    "ВАЖНО:\n"
                    " • Spotify проверяет, чтобы оба аккаунта были в одной стране и на одном адресе.\n"
                    " • Если VPN не используется — регион и адрес не совпадут, и добавление не сработает.\n"
                    " • Если пишет, что невозможно присоединиться — проверь:\n"
                    " • Регион второго аккаунта (в настройках),\n"
                    " • Наличие VPN в момент принятия,\n"
                    " • Адрес — должен быть в точности такой же."
                )
            }
        }
    },
    "kling": {
        "title": "🎬 Kling",
        "items": {
            "payment_link": {
                "button": "🔗 Как вытащить ссылку",
                "text": (
                    "Здравствуйте. Как вытащить ссылку на оплату в Kling AI\n"
                    "Нажать кнопку Plans from 6.99\n"
                    "В открывшемся окне выбрать подходящую подписку и нажать по ней\n"
                    "Как откроется окно оплаты скинуть в чат"
                )
            },
            "cancel_plan": {
                "button": "❌ Отменить автооплату",
                "text": (
                    "Пожалуйста отмените план нажав по Manage plan затем cancel plan указав любой из причин. "
                    "Это действие не отменит саму подписку а следующую оплату. Надеемся на ваше понимание"
                )
            },
            "registration_account": {
                "button": "📩 Регистрация аккаунта",
                "text": (
                    "На наши почты Outlook не поступают коды верификации, сможете предложить любую из своих почт (адрес) для регистрации?"
                )
            }
        }
    },
    "doplata": {
        "title": "💰 Доплата",
        "items": {
            "plati_doplata": {
                "button": "🟦 Доплата Plati",
                "text": "Доплата plati: https://plati.market/itm/5457373"
            },
            "ggsel_doplata": {
                "button": "🟨 Доплата GGsel",
                "text": "Доплата ggsel: https://ggsel.net/catalog/product/doplata-za-tovar-ili-uslugu-102090136"
            }
        }
    },
    "ready_templates": {
        "title": "✅ Шаблоны готовности",
        "items": {
            "ggsel_ready": {
                "button": "🟨 GGsel",
                "text": (
                    "Гoтoвo! Бyдeм блaгoдapны ВaшeМy oтзывy, oни пoмoгaют cтaть нaм лyчшe.\n"
                    "➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
                    "⚠️ Вaжнo: ecли в пpoцecce выпoлнeния вoзниклa зaдepжкa, oнa нe вceгдa cвязaнa c нaшeй paбoтoй \n"
                    "В пикoвыe чacы зaкaзы oбpaбaтывaютcя дoльшe из-зa выcoкoй зaгpyзки, a тaкжe вoзмoжныx тexничecкиx или плaтёжныx пpoблeм внyтpи cepвиca.\n"
                    "➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
                    "Нaши тoвapы:\n"
                    "🟥 ChatGPT 5 Plus — https://ggsel.net/catalog/product/4437281\n"
                    "🟩 Spotify Premium — https://ggsel.net/catalog/product/4881347\n"
                    "🟫 Perplexity Pro (12 мec/449Р) — https://ggsel.net/catalog/product/5345557\n"
                    "🟨 Midjourney V7 — https://ggsel.net/catalog/product/101602330\n"
                    "🟪 Cursor AI PRO — https://ggsel.net/catalog/product/101606985\n"
                    "🟪 Claude AI PRO — https://ggsel.net/catalog/product/5479179\n"
                    "🟥 YouTube Premium — https://ggsel.net/catalog/product/102100531\n"
                    "🟩 Xbox Game Pass (1–12м) — https://ggsel.net/catalog/product/4437286\n"
                    "⭕️ Вce тoвapы - https://ggsel.net/sellers/164256\n"
                    "➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖"
                )
            },
            "plati_ready": {
                "button": "🟦 Plati",
                "text": (
                    "🎉 Готово! Будем благодарны Вашему отзыву, они помогают стать нам лучше.\n"
                    "➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
                    "🎁 Промокод на следующую покупку услуги cо скидкой для Вас и Ваших друзей: 139ECB630E7B4FE9\n"
                    "➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
                    "Наши товары:\n"
                    "🟥 ChatGPT 5.2 Plus — https://plati.ru/itm/4306654\n"
                    "🟩 Spotify Premium — https://plati.ru/itm/4009731\n"
                    "🟫 Perplexity Pro (12 меc/1.5$) — https://plati.ru/itm/5345532\n"
                    "🟨 Midjourney V7 — https://plati.ru/itm/4252725\n"
                    "🟪 Cursor AI PRO — https://plati.ru/itm/5070972\n"
                    "🟪 Claude AI PRO — https://plati.ru/itm/4873214\n"
                    "🟥 YouTube Premium — https://plati.ru/itm/5040347\n"
                    "🟦 Смена региона Steam — https://plati.ru/itm/3525355\n"
                    "⬛️ Пополнение Steam — https://plati.ru/itm/3343799\n"
                    "🟩 Xbox Game Pass (1–12м) — https://plati.ru/itm/3853868\n"
                    "⭕️ Все товары - https://fursov.me\n"
                    "➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
                    "📢 Акции и новости → https://t.me/+cFsmUDuAkPQ5ZGYy\n"
                    "➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
                    "🌍 Ищете VPN для ChatGPT?\n"
                    "Юзай Bebra VPN — стабильно работает с ChatGPT, Instagram, YouTube и не только.\n"
                    "💥 По нашей ссылке 2 месяца по цене 1!\n"
                    "👉 https://clck.ru/3R27mL"
                )
            },
            "fanpay_ready": {
                "button": "🟧 FanPay",
                "text": (
                    "Готово! Будем благодарны Вашему отзыву, они помогают стать нам лучше\n\n"
                    "Не забудьте подтвердить сделку, пожалуйста!"
                )
            }
        }
    },
    "midjourney": {
        "title": "🎨 Midjourney",
        "items": {
            "avoid_block": {
                "button": "🛡 Как избежать блокировки",
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


def load_shift_status() -> Dict[str, dict]:
    return load_json_file(SHIFT_STATUS_FILE, {})


def save_shift_status(data: Dict[str, dict]) -> None:
    save_json_file(SHIFT_STATUS_FILE, data)


def load_profiles() -> Dict[str, dict]:
    return load_json_file(PROFILES_FILE, {})


def save_profiles(data: Dict[str, dict]) -> None:
    save_json_file(PROFILES_FILE, data)


def load_dialogs_state() -> Dict[str, dict]:
    return load_json_file(
        DIALOGS_STATE_FILE,
        {
            "watch_enabled": True,
            "last_active_count": None,
            "last_new_count": None,
            "last_signature": ""
        }
    )


def save_dialogs_state(data: Dict[str, dict]) -> None:
    save_json_file(DIALOGS_STATE_FILE, data)


def load_fines() -> List[dict]:
    return load_json_file(FINES_FILE, [])


def save_fines(data: List[dict]) -> None:
    save_json_file(FINES_FILE, data)


def load_scores() -> List[dict]:
    return load_json_file(SCORES_FILE, [])


def save_scores(data: List[dict]) -> None:
    save_json_file(SCORES_FILE, data)


def load_schedule() -> Dict[str, dict]:
    return load_json_file(SCHEDULE_FILE, {})


def save_schedule(data: Dict[str, dict]) -> None:
    save_json_file(SCHEDULE_FILE, data)


def load_pending_news() -> Dict[str, dict]:
    return load_json_file(PENDING_NEWS_FILE, {})


def save_pending_news(data: Dict[str, dict]) -> None:
    save_json_file(PENDING_NEWS_FILE, data)


def load_requests() -> List[dict]:
    return load_json_file(REQUESTS_FILE, [])


def save_requests(data: List[dict]) -> None:
    save_json_file(REQUESTS_FILE, data)


USERS: Set[int] = load_users()
SENT_REVIEWS: Set[str] = load_sent_reviews()
ANNOUNCEMENTS: Dict[str, dict] = load_announcements()
SHIFT_STATUS: Dict[str, dict] = load_shift_status()
USER_PROFILES: Dict[str, dict] = load_profiles()
DIALOGS_STATE: Dict[str, dict] = load_dialogs_state()
FINES: List[dict] = load_fines()
SCORES: List[dict] = load_scores()
SCHEDULE: Dict[str, dict] = load_schedule()
PENDING_NEWS: Dict[str, dict] = load_pending_news()
REQUESTS: List[dict] = load_requests()

# =========================================================
# HELPERS
# =========================================================
def msk_now() -> datetime:
    return datetime.now(MSK_TZ)

def get_worker_area(user_id: int) -> str:
    return WORKER_AREAS.get(user_id, get_platform_name(user_id))

def is_private_chat(message: Message) -> bool:
    return message.chat.type == "private"


def today_msk_str() -> str:
    return msk_now().strftime("%Y-%m-%d")


def tomorrow_msk_str() -> str:
    return (msk_now() + timedelta(days=1)).strftime("%Y-%m-%d")


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def update_profile_from_user(user) -> None:
    user_id = str(user.id)
    USER_PROFILES[user_id] = {
        "username": user.username or "",
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "updated_at": msk_now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_profiles(USER_PROFILES)


def get_platform_name(user_id: int) -> str:
    if user_id in FANPAY_WORKERS:
        return "FanPay"
    if user_id in AI_WORKERS:
        return "AI"
    if user_id in STEAM_WORKERS:
        return "Steam"
    return "Не назначена"


def get_role_name(user_id: int) -> str:
    return "👑 Админ" if is_admin(user_id) else "👨‍💻 Сотрудник"


def current_shift_type(now: datetime | None = None) -> str | None:
    now = now or msk_now()
    now_t = now.time()
    if DAY_SHIFT_START <= now_t <= DAY_SHIFT_END:
        return "day"
    if EVENING_SHIFT_START <= now_t <= EVENING_SHIFT_END:
        return "evening"
    return None


def current_shift_name(now: datetime | None = None) -> str:
    shift_type = current_shift_type(now)
    if shift_type == "day":
        return "🌞 Дневная"
    if shift_type == "evening":
        return "🌙 Вечерняя"
    return "⏸ Вне смены"


def is_late_for_shift(now: datetime, shift_type: str) -> bool:
    if shift_type == "day":
        return now.time() > DAY_SHIFT_LATE_AFTER
    if shift_type == "evening":
        return now.time() > EVENING_SHIFT_LATE_AFTER
    return False


def is_exact_start_bonus(now: datetime, shift_type: str) -> bool:
    if shift_type == "day":
        return DAY_SHIFT_START <= now.time() <= DAY_SHIFT_EXACT_UNTIL
    if shift_type == "evening":
        return EVENING_SHIFT_START <= now.time() <= EVENING_SHIFT_EXACT_UNTIL
    return False


def ensure_shift_user(user_id: int):
    uid = str(user_id)
    if uid not in SHIFT_STATUS:
        SHIFT_STATUS[uid] = {
            "is_on_shift": False,
            "last_shift_on": "",
            "last_shift_off": "",
            "last_shift_type": "",
            "last_shift_date": "",
            "last_late": False,
            "current_shift_key": "",
            "auto_absent_fined_keys": [],
            "streak": 0
        }
        save_shift_status(SHIFT_STATUS)


def add_fine(user_id: int, amount: int, reason: str, source: str):
    FINES.append({
        "user_id": int(user_id),
        "amount": int(amount),
        "reason": reason,
        "source": source,
        "created_at": msk_now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_fines(FINES)


def add_score(user_id: int, points: int, reason: str):
    SCORES.append({
        "user_id": int(user_id),
        "points": int(points),
        "reason": reason,
        "created_at": msk_now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_scores(SCORES)


def get_user_fines(user_id: int) -> List[dict]:
    return [x for x in FINES if int(x["user_id"]) == int(user_id)]


def get_user_scores(user_id: int) -> List[dict]:
    return [x for x in SCORES if int(x["user_id"]) == int(user_id)]


def get_user_weekly_fines_sum(user_id: int) -> int:
    border = msk_now() - timedelta(days=7)
    total = 0
    for fine in get_user_fines(user_id):
        try:
            dt = datetime.strptime(fine["created_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=MSK_TZ)
            if dt >= border:
                total += int(fine["amount"])
        except Exception:
            continue
    return total


def get_user_total_fines_sum(user_id: int) -> int:
    return sum(int(x["amount"]) for x in get_user_fines(user_id))


def get_user_weekly_score(user_id: int) -> int:
    border = msk_now() - timedelta(days=7)
    total = 0
    for score in get_user_scores(user_id):
        try:
            dt = datetime.strptime(score["created_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=MSK_TZ)
            if dt >= border:
                total += int(score["points"])
        except Exception:
            continue
    return total


def get_user_total_score(user_id: int) -> int:
    return sum(int(x["points"]) for x in get_user_scores(user_id))


def score_table_for_shift(date_str: str, shift_type: str) -> List[int]:
    shift_key = f"{date_str}:{shift_type}"
    joined = []
    for uid_str, state in SHIFT_STATUS.items():
        if state.get("current_shift_key") == shift_key and state.get("last_shift_date") == date_str:
            joined.append(int(uid_str))
    return joined


def get_profile_text(user_id: int) -> str:
    ensure_shift_user(user_id)
    profile = USER_PROFILES.get(str(user_id), {})
    state = SHIFT_STATUS.get(str(user_id), {})

    username = profile.get("username") or "нет"
    first_name = profile.get("first_name") or ""
    last_name = profile.get("last_name") or ""
    full_name = f"{first_name} {last_name}".strip() or "не указано"

    is_on_shift = state.get("is_on_shift", False)
    last_shift_on = state.get("last_shift_on") or "не было"
    last_shift_off = state.get("last_shift_off") or "не было"
    last_shift_type = state.get("last_shift_type") or "неизвестно"
    streak = int(state.get("streak", 0))

    weekly_sum = get_user_weekly_fines_sum(user_id)
    total_sum = get_user_total_fines_sum(user_id)
    weekly_score = get_user_weekly_score(user_id)
    total_score = get_user_total_score(user_id)

    return (
        "👤 Ваш профиль\n\n"
        f"🆔 ID: {user_id}\n"
        f"👤 Username: @{username}\n"
        f"📛 Имя: {full_name}\n"
        f"🎭 Роль: {get_role_name(user_id)}\n"
        f"🧩 Платформа: {get_platform_name(user_id)}\n"
        f"📍 Статус: {'🟢 На смене' if is_on_shift else '🔴 Не на смене'}\n"
        f"🕒 Текущая смена по МСК: {current_shift_name()}\n"
        f"🗂 Последняя смена: {last_shift_type}\n"
        f"🟢 Последний выход: {last_shift_on}\n"
        f"🔴 Последний уход: {last_shift_off}\n"
        f"🔥 Streak без опозданий: {streak}\n"
        f"⭐ Рейтинг за 7 дней: {weekly_score}\n"
        f"🏆 Рейтинг общий: {total_score}\n"
        f"💸 Штрафы за 7 дней: {weekly_sum} руб\n"
        f"💰 Штрафы всего: {total_sum} руб"
    )


def get_short_user_label(user_id: int) -> str:
    profile = USER_PROFILES.get(str(user_id), {})

    if user_id in DISPLAY_NAMES:
        return DISPLAY_NAMES[user_id]

    username = (profile.get("username") or "").strip()
    first_name = (profile.get("first_name") or "").strip()
    last_name = (profile.get("last_name") or "").strip()

    if username:
        return f"@{username}"

    full_name = f"{first_name} {last_name}".strip()
    if full_name:
        return full_name

    if first_name:
        return first_name

    return str(user_id)


def get_platform_users(platform: str) -> List[int]:
    platform = platform.lower()
    if platform == "ai":
        return AI_WORKERS
    if platform == "steam":
        return STEAM_WORKERS
    if platform == "all":
        return sorted(set(AI_WORKERS + STEAM_WORKERS))
    return []


def get_schedule_for_day(day_str: str) -> dict:
    return SCHEDULE.get(day_str, {"day": [], "evening": []})


def build_day_schedule_text(day_str: str) -> str:
    sched = get_schedule_for_day(day_str)
    day_users = sched.get("day", [])
    evening_users = sched.get("evening", [])

    lines = [f"🗓 График на {day_str}\n"]
    lines.append("🌞 Дневная смена:")
    if day_users:
        lines.extend([f"• {get_short_user_label(uid)}" for uid in day_users])
    else:
        lines.append("• никого")

    lines.append("")
    lines.append("🌙 Вечерняя смена:")
    if evening_users:
        lines.extend([f"• {get_short_user_label(uid)}" for uid in evening_users])
    else:
        lines.append("• никого")

    return "\n".join(lines)


def build_week_schedule_text() -> str:
    base = msk_now().date()
    chunks = []
    for i in range(7):
        d = base + timedelta(days=i)
        chunks.append(build_day_schedule_text(d.strftime("%Y-%m-%d")))
    return "\n\n".join(chunks)


def who_should_work_now() -> List[int]:
    now = msk_now()
    shift_type = current_shift_type(now)
    if shift_type is None:
        return []
    sched = get_schedule_for_day(today_msk_str())
    return sched.get(shift_type, [])


def build_who_should_work_text() -> str:
    now = msk_now()
    shift_type = current_shift_type(now)
    if shift_type is None:
        return "⏸ Сейчас нет активной смены по МСК."

    users = who_should_work_now()
    shift_name = "🌞 Дневная" if shift_type == "day" else "🌙 Вечерняя"

    if not users:
        return f"{shift_name} смена сейчас активна, но в графике никого нет."

    lines = [f"{shift_name} смена сейчас активна.\n", "👥 Сейчас должны быть на смене:"]
    lines.extend([f"• {get_short_user_label(uid)}" for uid in users])
    return "\n".join(lines)


def build_load_forecast_text() -> str:
    tomorrow = get_schedule_for_day(tomorrow_msk_str())
    day_count = len(tomorrow.get("day", []))
    evening_count = len(tomorrow.get("evening", []))

    def describe(cnt: int) -> str:
        if cnt == 0:
            return "❌ никого"
        if cnt == 1:
            return "⚠️ мало"
        if cnt == 2:
            return "🟡 средне"
        return "🟢 нормально"

    return (
        "📈 Прогноз загрузки на завтра\n\n"
        f"🌞 Дневная смена: {day_count} чел. — {describe(day_count)}\n"
        f"🌙 Вечерняя смена: {evening_count} чел. — {describe(evening_count)}"
    )


def build_weekly_fines_report() -> str:
    border = msk_now() - timedelta(days=7)

    sums: Dict[int, int] = {}
    counts: Dict[int, int] = {}

    for fine in FINES:
        try:
            dt = datetime.strptime(fine["created_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=MSK_TZ)
        except Exception:
            continue

        if dt < border:
            continue

        uid = int(fine["user_id"])
        sums[uid] = sums.get(uid, 0) + int(fine["amount"])
        counts[uid] = counts.get(uid, 0) + 1

    if not sums:
        return "📊 За последние 7 дней штрафов нет."

    total_fines_count = sum(counts.values())
    total_fines_sum = sum(sums.values())

    lines = ["📊 Штрафы за последние 7 дней:\n"]
    for uid, total in sorted(sums.items(), key=lambda x: x[1], reverse=True):
        lines.append(
            f"• {get_short_user_label(uid)} | штрафов: {counts[uid]} | сумма: {total} руб"
        )

    lines.append("")
    lines.append(f"📌 Всего штрафов: {total_fines_count}")
    lines.append(f"💰 Общая сумма: {total_fines_sum} руб")
    return "\n".join(lines)


def build_my_week_text(user_id: int) -> str:
    border = msk_now() - timedelta(days=7)
    weekly_fines = get_user_weekly_fines_sum(user_id)
    weekly_score = get_user_weekly_score(user_id)
    streak = int(SHIFT_STATUS.get(str(user_id), {}).get("streak", 0))

    late_events = 0
    for fine in get_user_fines(user_id):
        try:
            dt = datetime.strptime(fine["created_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=MSK_TZ)
            if dt >= border and "Опоздание" in fine["reason"]:
                late_events += 1
        except Exception:
            continue

    perfect_starts = 0
    for score in get_user_scores(user_id):
        try:
            dt = datetime.strptime(score["created_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=MSK_TZ)
            if dt >= border and score["reason"] == "Точный выход в стартовую минуту":
                perfect_starts += 1
        except Exception:
            continue

    first_on_shift = 0
    for score in get_user_scores(user_id):
        try:
            dt = datetime.strptime(score["created_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=MSK_TZ)
            if dt >= border and score["reason"] == "Первый на смене":
                first_on_shift += 1
        except Exception:
            continue

    return (
        "📊 Ваш отчёт за 7 дней\n\n"
        f"⭐ Рейтинг за неделю: {weekly_score}\n"
        f"🔥 Текущий streak: {streak}\n"
        f"⏰ Опозданий за неделю: {late_events}\n"
        f"🎯 Точных выходов в стартовую минуту: {perfect_starts}\n"
        f"🏁 Первых выходов на смене: {first_on_shift}\n"
        f"💸 Штрафов за неделю: {weekly_fines} руб"
    )


def build_news_status_text() -> str:
    if not ANNOUNCEMENTS:
        return "📢 Новостей пока нет."

    lines = ["📢 Статус новостей:\n"]
    sorted_items = sorted(
        ANNOUNCEMENTS.items(),
        key=lambda x: x[1].get("created_at", ""),
        reverse=True
    )[:10]

    for ann_id, ann in sorted_items:
        platform = ann.get("platform", "all")
        acked = len(ann.get("acked_by", []))
        target = len(get_platform_users(platform))
        lines.append(
            f"• ID {ann_id}\n"
            f"  🌍 Платформа: {platform.upper()}\n"
            f"  ⏱ Дедлайн: {ann.get('deadline_minutes', 0)} мин\n"
            f"  ✅ Ознакомились: {acked}/{target}\n"
            f"  📝 {ann.get('text', '')[:80]}"
        )
    return "\n\n".join(lines)


def build_not_read_text() -> str:
    if not ANNOUNCEMENTS:
        return "📭 Нет активных новостей."

    ann_id, ann = sorted(
        ANNOUNCEMENTS.items(),
        key=lambda x: x[1].get("created_at", ""),
        reverse=True
    )[0]

    platform = ann.get("platform", "all")
    target_users = get_platform_users(platform)
    acked = set(int(x) for x in ann.get("acked_by", []))
    not_read = [uid for uid in target_users if uid not in acked]

    if not not_read:
        return "✅ Все сотрудники ознакомились."

    lines = ["❌ Не ознакомились:\n"]
    for uid in not_read:
        lines.append(f"• {get_short_user_label(uid)} | {get_platform_name(uid)}")

    return "\n".join(lines)

async def notify_staff_group_shift(bot: Bot, user_id: int, action: str) -> None:
    if not STAFF_GROUP_ID:
        return

    worker_name = get_short_user_label(user_id)
    area = get_worker_area(user_id)

    if action == "on":
        text = f"🟢 Сотрудник {worker_name} — Вышел на смену {area}"
    else:
        text = f"🔴 Сотрудник {worker_name} — Завершил(-а) смену {area}"

    try:
        await bot.send_message(STAFF_GROUP_ID, text)
    except Exception as e:
        logging.warning(f"Ошибка отправки в группу: {e}")

# =========================================================
# КЛАВИАТУРЫ
# =========================================================
def services_keyboard():
    builder = InlineKeyboardBuilder()
    for service_key, service_data in DATA.items():
        builder.button(text=service_data["title"], callback_data=f"service:{service_key}")
    builder.button(text="🏠 Главное меню", callback_data="open_menu")
    builder.adjust(2)
    return builder.as_markup()


def instructions_keyboard(service_key: str):
    builder = InlineKeyboardBuilder()
    for item_key, item_data in DATA[service_key]["items"].items():
        builder.button(text=item_data["button"], callback_data=f"item:{service_key}:{item_key}")
    builder.button(text="⬅️ Назад", callback_data="open_instructions")
    builder.button(text="🏠 Главное меню", callback_data="open_menu")
    builder.adjust(1)
    return builder.as_markup()


def back_to_list_keyboard(service_key: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ К списку инструкций", callback_data=f"service:{service_key}")
    builder.button(text="🏠 Главное меню", callback_data="open_menu")
    builder.adjust(1)
    return builder.as_markup()


def acknowledge_keyboard(announcement_id: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ознакомлен", callback_data=f"ack:{announcement_id}")
    builder.adjust(1)
    return builder.as_markup()


def admin_main_inline_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Пользователи", callback_data="admin_users")
    builder.button(text="📊 Штрафы за неделю", callback_data="admin_weekly_fines")
    builder.button(text="🗓 Кто на смене сейчас", callback_data="admin_who_should_work")
    builder.button(text="📈 Прогноз загрузки", callback_data="admin_load_forecast")
    builder.button(text="📨 Проверить диалоги", callback_data="admin_dialogs_check")
    builder.button(text="📢 Рассылка", callback_data="admin_news_start")
    builder.button(text="❌ Кто не ознакомился", callback_data="admin_not_read")
    builder.adjust(2)
    return builder.as_markup()


def profile_inline_keyboard(is_on_shift: bool):
    builder = InlineKeyboardBuilder()
    if not is_on_shift:
        builder.button(text="🟢 Вышел на смену", callback_data="shift_on_btn")
    else:
        builder.button(text="🔴 Ушёл со смены", callback_data="shift_off_btn")
    builder.button(text="📊 Мой отчёт", callback_data="my_week_btn")
    builder.button(text="💸 Мои штрафы", callback_data="my_fines_btn")
    builder.button(text="🏠 Главное меню", callback_data="open_menu")
    builder.adjust(2)
    return builder.as_markup()


def news_platform_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🤖 AI", callback_data="news_platform:ai")
    builder.button(text="🎮 Steam", callback_data="news_platform:steam")
    builder.button(text="🌍 Всем", callback_data="news_platform:all")
    builder.button(text="❌ Отмена", callback_data="news_cancel")
    builder.adjust(2)
    return builder.as_markup()


def news_deadline_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="⏱ 15 мин", callback_data="news_deadline:15")
    builder.button(text="⏱ 30 мин", callback_data="news_deadline:30")
    builder.button(text="⏱ 60 мин", callback_data="news_deadline:60")
    builder.button(text="⏱ 120 мин", callback_data="news_deadline:120")
    builder.button(text="❌ Отмена", callback_data="news_cancel")
    builder.adjust(2)
    return builder.as_markup()


def need_admin_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="❗ Срочно", callback_data="req_admin:urgent")
    builder.button(text="❓ Вопрос", callback_data="req_admin:question")
    builder.button(text="⚙️ Проблема", callback_data="req_admin:problem")
    builder.button(text="❌ Отмена", callback_data="req_admin_cancel")
    builder.adjust(2)
    return builder.as_markup()


def main_menu_keyboard(is_admin_user: bool = False):
    rows = [
        [KeyboardButton(text="📚 Инструкции"), KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="📊 Моя неделя"), KeyboardButton(text="💸 Мои штрафы")],
        [KeyboardButton(text="🟢 Вышел на смену"), KeyboardButton(text="🔴 Ушёл со смены")],
        [KeyboardButton(text="🗓 Сегодня"), KeyboardButton(text="📅 Завтра")],
        [KeyboardButton(text="🚨 Нужен админ")],
    ]
    if is_admin_user:
        rows.append([KeyboardButton(text="👑 Админ панель")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

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
    html_text = fetch_url(DIGISELLER_NEGATIVE_URL)
    soup = BeautifulSoup(html_text, "html.parser")

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
    html_text = fetch_url(review_url)
    soup = BeautifulSoup(html_text, "html.parser")
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
        f"🧾 Номер счета: {review['invoice']}\n"
        f"📦 Товар: {review['product']}\n"
        f"👤 Покупатель: {review['buyer']}\n"
        "💬 Отзыв:\n"
        "-------------------------------------\n"
        f"{review['review_text']}"
    )


def parse_dialogs_page() -> Tuple[int, int, List[dict]]:
    html_text = fetch_url(DIGISELLER_DIALOGS_URL)
    soup = BeautifulSoup(html_text, "html.parser")

    rows: List[dict] = []
    signatures: List[str] = []

    for tr in soup.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 4:
            continue

        buyer = cells[0].get_text(" ", strip=True)
        product = cells[1].get_text(" ", strip=True)
        count_info = cells[2].get_text(" ", strip=True)
        time_info = cells[3].get_text(" ", strip=True)

        if not buyer or "@" not in buyer:
            continue
        if buyer.lower() == "support@digiseller.com":
            continue
        if not product or product.lower() in {"sign in", "не найдено", "все товары"}:
            continue

        match = re.search(r"(\d+)\s*/\s*(\d+)", count_info)
        if not match:
            continue

        total_count = int(match.group(1))
        new_count = int(match.group(2))

        row = {
            "buyer": buyer,
            "product": product,
            "total_count": total_count,
            "new_count": new_count,
            "time": time_info
        }
        rows.append(row)
        signatures.append(f"{buyer}|{product}|{total_count}|{new_count}|{time_info}")

    if not rows:
        for a_tag in soup.find_all("a", href=True):
            buyer = a_tag.get_text(" ", strip=True)
            if "@" not in buyer:
                continue
            if buyer.lower() == "support@digiseller.com":
                continue

            parent_tr = a_tag.find_parent("tr")
            if not parent_tr:
                continue

            cells = parent_tr.find_all("td")
            if len(cells) < 4:
                continue

            buyer = cells[0].get_text(" ", strip=True)
            product = cells[1].get_text(" ", strip=True)
            count_info = cells[2].get_text(" ", strip=True)
            time_info = cells[3].get_text(" ", strip=True)

            match = re.search(r"(\d+)\s*/\s*(\d+)", count_info)
            if not match:
                continue

            total_count = int(match.group(1))
            new_count = int(match.group(2))

            row = {
                "buyer": buyer,
                "product": product,
                "total_count": total_count,
                "new_count": new_count,
                "time": time_info
            }
            rows.append(row)
            signatures.append(f"{buyer}|{product}|{total_count}|{new_count}|{time_info}")

    unique_rows = []
    seen = set()
    for row in rows:
        key = (row["buyer"], row["product"], row["total_count"], row["new_count"], row["time"])
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(row)

    rows = unique_rows
    active_count = len(rows)
    new_count_sum = sum(row["new_count"] for row in rows)
    signature = "||".join(signatures)

    DIALOGS_STATE["last_signature_temp"] = signature
    return active_count, new_count_sum, rows


def build_dialogs_message(active_count: int, new_count_sum: int, rows: List[dict]) -> str:
    lines = [
        f"📨 Активные диалоги Digiseller: {active_count}",
        f"🆕 Новых сообщений: {new_count_sum}",
        ""
    ]

    if not rows:
        lines.append("Сейчас активных диалогов не найдено.")
        return "\n".join(lines)

    for idx, row in enumerate(rows[:20], start=1):
        lines.append(
            f"{idx}. {row['buyer']}\n"
            f"   📦 Товар: {row['product']}\n"
            f"   💬 Сообщений всего/новых: {row['total_count']} / {row['new_count']}\n"
            f"   🕒 Время: {row['time']}\n"
        )

    if len(rows) > 20:
        lines.append(f"... и ещё {len(rows) - 20}")

    return "\n".join(lines)

# =========================================================
# СМЕНЫ
# =========================================================
async def process_shift_on(user_id: int, bot: Bot) -> str:
    ensure_shift_user(user_id)

    now = msk_now()
    user_shift = SHIFT_STATUS[str(user_id)]

    now_time = now.time()

    # Определяем смену + окно раннего входа
    if time(10, 50) <= now_time < time(17, 30):
        shift_name = "Дневная"
        shift_type = "day"
        shift_start = now.replace(hour=11, minute=0, second=0, microsecond=0)
        allowed_early = now.replace(hour=10, minute=50, second=0, microsecond=0)
        late_border = now.replace(hour=11, minute=15, second=0, microsecond=0)

    elif time(17, 20) <= now_time <= time(23, 59, 59):
        shift_name = "Вечерняя"
        shift_type = "evening"
        shift_start = now.replace(hour=17, minute=30, second=0, microsecond=0)
        allowed_early = now.replace(hour=17, minute=20, second=0, microsecond=0)
        late_border = now.replace(hour=17, minute=45, second=0, microsecond=0)

    elif time(0, 0) <= now_time < time(10, 50):
        return (
            "⏸ Сейчас ещё рано для выхода на смену.\n"
            "🌞 На дневную можно отмечаться с 10:50 МСК\n"
            "🌙 На вечернюю можно отмечаться с 17:20 МСК"
        )
    else:
        return "⏸ Сейчас нет активного окна для выхода на смену."

    if user_shift.get("is_on_shift", False):
        return "🟢 Вы уже отмечены как сотрудник на смене."

    # Опоздание
    late = now > late_border

    # Точный бонус только если не раньше старта и не позже 1 минуты после старта
    exact_bonus = shift_start <= now <= (shift_start + timedelta(minutes=1))

    # Первый на смене
    today_key = now.strftime("%Y-%m-%d") + "_" + shift_name
    is_first_on_shift = not any(
        s.get("current_shift_key") == today_key and s.get("is_on_shift", False)
        for s in SHIFT_STATUS.values()
    )

    # Обновляем статус
    user_shift["is_on_shift"] = True
    user_shift["last_shift_on"] = now.strftime("%Y-%m-%d %H:%M:%S")
    user_shift["last_shift_type"] = shift_name
    user_shift["last_shift_date"] = today_msk_str()
    user_shift["last_late"] = late
    user_shift["current_shift_key"] = today_key

    if late:
        user_shift["streak"] = 0
    else:
        user_shift["streak"] = int(user_shift.get("streak", 0)) + 1

    save_shift_status(SHIFT_STATUS)

    messages = [
        f"🟢 Вы вышли на {shift_name} смену.",
        f"🕒 Время отметки: {now.strftime('%H:%M:%S')} МСК"
    ]

    if now < shift_start:
        messages.append("⏳ Вы отметились заранее — это нормально.")

    if late:
        add_fine(user_id, LATE_FINE_AMOUNT, f"Опоздание на {shift_name} смену", "auto_late")
        messages.append(f"⚠️ Вы опоздали. Штраф: {LATE_FINE_AMOUNT} руб")
    else:
        messages.append("✅ Молодец, успел на смену!")

    if exact_bonus and not late:
        add_score(user_id, 1, "Точный выход в стартовую минуту")
        messages.append("⭐ Бонус +1: точный выход в стартовую минуту")

    if is_first_on_shift and not late:
        add_score(user_id, 1, "Первый на смене")
        messages.append("🚀 Бонус +1: вы первый на этой смене")

    if late:
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"⚠️ Авто-штраф за опоздание\n"
                    f"{get_short_user_label(user_id)} | {get_worker_area(user_id)}\n"
                    f"💸 {LATE_FINE_AMOUNT} руб | {shift_name} смена"
                )
            except Exception:
                pass

    await notify_staff_group_shift(bot, user_id, "on")
    return "\n".join(messages)


async def process_shift_off(user_id: int, bot: Bot | None = None) -> str:
    ensure_shift_user(user_id)
    now = msk_now()
    user_shift = SHIFT_STATUS[str(user_id)]

    if not user_shift.get("is_on_shift", False):
        return "🔴 Вы и так не на смене."

    user_shift["is_on_shift"] = False
    user_shift["last_shift_off"] = now.strftime("%Y-%m-%d %H:%M:%S")
    user_shift["current_shift_key"] = ""
    save_shift_status(SHIFT_STATUS)

    if bot:
        await notify_staff_group_shift(bot, user_id, "off")

    return f"🔴 Вы ушли со смены\n🕒 {now.strftime('%H:%M:%S')} МСК"


async def auto_check_absent_workers(bot: Bot):
    await asyncio.sleep(10)

    while True:
        try:
            now = msk_now()
            shift_type = current_shift_type(now)
            if shift_type is None:
                await asyncio.sleep(ABSENT_CHECK_INTERVAL_SECONDS)
                continue

            if shift_type == "day" and now.time() <= DAY_SHIFT_LATE_AFTER:
                await asyncio.sleep(ABSENT_CHECK_INTERVAL_SECONDS)
                continue

            if shift_type == "evening" and now.time() <= EVENING_SHIFT_LATE_AFTER:
                await asyncio.sleep(ABSENT_CHECK_INTERVAL_SECONDS)
                continue

            today_str = today_msk_str()
            sched = get_schedule_for_day(today_str)
            should_work = sched.get(shift_type, [])
            shift_key = f"{today_str}:{shift_type}"

            for user_id in should_work:
                ensure_shift_user(user_id)
                state = SHIFT_STATUS[str(user_id)]

                if state.get("current_shift_key") == shift_key and state.get("is_on_shift", False):
                    continue

                fined_keys = state.get("auto_absent_fined_keys", [])
                if shift_key in fined_keys:
                    continue

                add_fine(user_id, ABSENT_FINE_AMOUNT, "Не вышел на смену", "auto_absent")
                state["streak"] = 0
                fined_keys.append(shift_key)
                state["auto_absent_fined_keys"] = fined_keys
                save_shift_status(SHIFT_STATUS)

                try:
                    await bot.send_message(
                        user_id,
                        f"❌ Вы не отметили выход на смену вовремя.\n"
                        f"💸 Авто-штраф: {ABSENT_FINE_AMOUNT} руб"
                    )
                except Exception:
                    pass

                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(
                            admin_id,
                            f"❌ Авто-штраф за невыход на смену\n"
                            f"{get_short_user_label(user_id)} | {get_platform_name(user_id)}\n"
                            f"💸 {ABSENT_FINE_AMOUNT} руб"
                        )
                    except Exception:
                        pass

        except Exception as e:
            logging.exception(f"Ошибка авто-проверки невыхода на смену: {e}")

        await asyncio.sleep(ABSENT_CHECK_INTERVAL_SECONDS)

async def chat_id_handler(message: Message):
    await message.answer(f"Chat ID: {message.chat.id}")


# =========================================================
# REQUESTS
# =========================================================
def add_request(user_id: int, req_type: str):
    REQUESTS.append({
        "user_id": int(user_id),
        "type": req_type,
        "status": "open",
        "created_at": msk_now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_requests(REQUESTS)

# =========================================================
# РАССЫЛКИ
# =========================================================
def create_announcement(platform: str, deadline_minutes: int, text: str) -> str:
    announcement_id = str(int(asyncio.get_event_loop().time() * 1000))
    ANNOUNCEMENTS[announcement_id] = {
        "platform": platform,
        "deadline_minutes": deadline_minutes,
        "text": text,
        "created_at": msk_now().strftime("%Y-%m-%d %H:%M:%S"),
        "acked_by": []
    }
    save_announcements(ANNOUNCEMENTS)
    return announcement_id

# =========================================================
# MONITORS
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


async def monitor_dialogs(bot: Bot):
    await asyncio.sleep(8)

    while True:
        try:
            if not DIALOGS_STATE.get("watch_enabled", True):
                await asyncio.sleep(DIALOGS_CHECK_INTERVAL_SECONDS)
                continue

            if not DIGISELLER_COOKIE:
                await asyncio.sleep(DIALOGS_CHECK_INTERVAL_SECONDS)
                continue

            active_count, new_count_sum, rows = await asyncio.to_thread(parse_dialogs_page)
            current_signature = DIALOGS_STATE.get("last_signature_temp", "")

            last_active_count = DIALOGS_STATE.get("last_active_count")
            last_new_count = DIALOGS_STATE.get("last_new_count")
            last_signature = DIALOGS_STATE.get("last_signature", "")

            changed = (
                last_active_count != active_count
                or last_new_count != new_count_sum
                or last_signature != current_signature
            )

            if changed:
                notify_text = "🔔 Обновление по активным сообщениям\n\n" + build_dialogs_message(
                    active_count, new_count_sum, rows
                )

                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(admin_id, notify_text, disable_web_page_preview=True)
                    except Exception as e:
                        logging.warning(f"Не удалось отправить админу {admin_id} обновление по диалогам: {e}")

                DIALOGS_STATE["last_active_count"] = active_count
                DIALOGS_STATE["last_new_count"] = new_count_sum
                DIALOGS_STATE["last_signature"] = current_signature
                save_dialogs_state(DIALOGS_STATE)

        except Exception as e:
            logging.exception(f"Ошибка мониторинга диалогов: {e}")

        await asyncio.sleep(DIALOGS_CHECK_INTERVAL_SECONDS)


async def monitor_announcements(bot: Bot):
    await asyncio.sleep(15)

    while True:
        try:
            now = msk_now()

            for ann_id, ann in list(ANNOUNCEMENTS.items()):
                created_str = ann.get("created_at")
                deadline_minutes = int(ann.get("deadline_minutes", 0))
                if not created_str or deadline_minutes <= 0:
                    continue

                try:
                    created_dt = datetime.strptime(created_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=MSK_TZ)
                except Exception:
                    continue

                deadline_dt = created_dt + timedelta(minutes=deadline_minutes)
                if now < deadline_dt:
                    continue

                if ann.get("expired_notified"):
                    continue

                platform = ann.get("platform", "all")
                target_users = get_platform_users(platform)
                acked = set(int(x) for x in ann.get("acked_by", []))
                not_read = [uid for uid in target_users if uid not in acked]

                if not_read:
                    for admin_id in ADMIN_IDS:
                        try:
                            lines = [f"❌ Не ознакомились вовремя | {platform.upper()}"]
                            lines.extend([f"• {get_short_user_label(uid)}" for uid in not_read])
                            await bot.send_message(admin_id, "\n".join(lines))
                        except Exception:
                            pass

                ann["expired_notified"] = True
                ANNOUNCEMENTS[ann_id] = ann
                save_announcements(ANNOUNCEMENTS)

        except Exception as e:
            logging.exception(f"Ошибка мониторинга новостей: {e}")

        await asyncio.sleep(60)

# =========================================================
# COMMAND HANDLERS
# =========================================================
async def start_handler(message: Message):
    if message.chat.type != "private":
        return

    user_id = message.chat.id
    username = message.from_user.username

    update_profile_from_user(message.from_user)
    ensure_shift_user(user_id)

    is_new = user_id not in USERS
    if is_new:
        USERS.add(user_id)
        save_users(USERS)

    await message.answer(
        f"✅ Бот активирован.\n"
        f"🆔 Ваш user ID: {user_id}\n\n"
        f"Теперь вам будут приходить отзывы, новости и служебные уведомления.\n"
        f"Ниже доступно главное меню 👇",
        reply_markup=main_menu_keyboard(is_admin(user_id))
    )

    admin_text = (
        "👤 Сотрудник нажал /start\n\n"
        f"🆔 ID: {user_id}\n"
        f"👤 Username: @{username if username else 'нет'}\n"
        f"📛 Имя: {full_name or 'не указано'}\n"
        f"🧩 Платформа: {get_platform_name(user_id)}\n"
        f"📌 Статус: {'Новый пользователь' if is_new else 'Повторный /start'}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(admin_id, admin_text)
        except Exception as e:
            logging.warning(f"Не удалось отправить уведомление админу {admin_id}: {e}")


async def menu_handler(message: Message):
    if message.chat.type != "private":
        return

    ensure_shift_user(message.chat.id)
    await message.answer(
        "🏠 Главное меню",
        reply_markup=main_menu_keyboard(is_admin(message.chat.id))
    )
    
async def remove_fine_handler(message: Message):
    if not is_admin(message.chat.id):
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Использование:\n/remove_fine ID номер")
        return

    uid = int(parts[1])
    index = int(parts[2]) - 1

    user_fines = [f for f in FINES if int(f["user_id"]) == uid]

    if index < 0 or index >= len(user_fines):
        await message.answer("❌ Неверный номер")
        return

    fine = user_fines[index]
    FINES.remove(fine)
    save_fines(FINES)

    await message.answer(f"✅ Штраф снят у {get_short_user_label(uid)}")


async def instructions_handler(message: Message):
    if message.chat.type != "private":
        return

    await message.answer(
        "📚 Выберите раздел инструкций:",
        reply_markup=services_keyboard()
    )


async def id_handler(message: Message):
    await message.answer(f"🆔 Ваш user ID: {message.chat.id}")


async def profile_handler(message: Message):
    if message.chat.type != "private":
        return

    ensure_shift_user(message.chat.id)
    update_profile_from_user(message.from_user)
    is_on = SHIFT_STATUS[str(message.chat.id)]["is_on_shift"]

    await message.answer(
        get_profile_text(message.chat.id),
        reply_markup=profile_inline_keyboard(is_on)
    )


async def my_fines_handler(message: Message):
    if message.chat.type != "private":
        return

    user_id = message.chat.id
    user_fines = get_user_fines(user_id)

    if not user_fines:
        await message.answer("💸 У вас пока нет штрафов.")
        return

    lines = ["💸 Ваши штрафы:\n"]
    for fine in user_fines[-15:]:
        lines.append(
            f"• {fine['created_at']} | {fine['amount']} руб | {fine['reason']}"
        )

    await message.answer("\n".join(lines))


async def my_week_handler(message: Message):
    if message.chat.type != "private":
        return

    await message.answer(build_my_week_text(message.chat.id))


async def admin_handler(message: Message):
    if not is_admin(message.chat.id):
        await message.answer("⛔ У вас нет доступа к админ-панели.")
        return
    await message.answer("👑 Админ-панель", reply_markup=admin_main_inline_keyboard())


async def users_count_handler(message: Message):
    if not is_admin(message.chat.id):
        return
    await message.answer(f"👥 Активированных пользователей: {len(USERS)}")


async def list_users_handler(message: Message):
    if not is_admin(message.chat.id):
        return

    if not USERS:
        await message.answer("👥 Пользователей пока нет.")
        return

    lines = ["👥 Пользователи бота:\n"]
    for user_id in sorted(USERS):
        lines.append(f"• {get_short_user_label(user_id)} | {get_platform_name(user_id)} | ID {user_id}")

    text = "\n".join(lines)
    if len(text) > 4000:
        for i in range(0, len(text), 3500):
            await message.answer(text[i:i + 3500])
    else:
        await message.answer(text)


async def workers_ai_handler(message: Message):
    if not is_admin(message.chat.id):
        return
    lines = ["🤖 AI-воркеры:\n"]
    for user_id in AI_WORKERS:
        lines.append(f"• {get_short_user_label(user_id)} | ID {user_id}")
    await message.answer("\n".join(lines))


async def workers_steam_handler(message: Message):
    if not is_admin(message.chat.id):
        return
    lines = ["🎮 Steam-воркеры:\n"]
    for user_id in STEAM_WORKERS:
        lines.append(f"• {get_short_user_label(user_id)} | ID {user_id}")
    await message.answer("\n".join(lines))


async def shift_on_handler(message: Message):
    if message.chat.type != "private":
        return

    update_profile_from_user(message.from_user)
    ensure_shift_user(message.chat.id)

    text = await process_shift_on(message.chat.id, message.bot)
    await message.answer(text)


async def shift_off_handler(message: Message):
    if message.chat.type != "private":
        return

    update_profile_from_user(message.from_user)
    ensure_shift_user(message.chat.id)

    text = await process_shift_off(message.chat.id, message.bot)
    await message.answer(text)


async def fine_handler(message: Message):
    if not is_admin(message.chat.id):
        return

    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.answer("Использование:\n/fine user_id сумма причина")
        return

    try:
        target_user_id = int(parts[1])
        amount = int(parts[2])
    except ValueError:
        await message.answer("❌ user_id и сумма должны быть числами.")
        return

    reason = parts[3]
    add_fine(target_user_id, amount, reason, "manual")

    try:
        await message.bot.send_message(
            target_user_id,
            f"⚠️ Вам назначен штраф\n\n💸 Сумма: {amount} руб\n📝 Причина: {reason}"
        )
    except Exception:
        pass

    await message.answer(f"✅ Штраф отправлен {target_user_id}.")


async def weekly_fines_handler(message: Message):
    if not is_admin(message.chat.id):
        return
    await message.answer(build_weekly_fines_report())


async def user_view_handler(message: Message):
    if not is_admin(message.chat.id):
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование:\n/user id")
        return

    try:
        uid = int(parts[1])
    except ValueError:
        await message.answer("❌ Неверный ID.")
        return

    ensure_shift_user(uid)
    await message.answer(get_profile_text(uid))


async def who_should_work_handler(message: Message):
    if not is_admin(message.chat.id):
        return
    await message.answer(build_who_should_work_text())


async def load_forecast_handler(message: Message):
    if not is_admin(message.chat.id):
        return
    await message.answer(build_load_forecast_text())


async def today_handler(message: Message):
    if message.chat.type != "private":
        return

    await message.answer(build_day_schedule_text(today_msk_str()))


async def tomorrow_handler(message: Message):
    if message.chat.type != "private":
        return

    await message.answer(build_day_schedule_text(tomorrow_msk_str()))


async def week_handler(message: Message):
    if message.chat.type != "private":
        return

    await message.answer(build_week_schedule_text())


async def set_schedule_handler(message: Message):
    if not is_admin(message.chat.id):
        return

    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.answer(
            "Использование:\n"
            "/set_schedule 2026-04-18 day 111,222\n"
            "/set_schedule 2026-04-18 evening 333,444"
        )
        return

    day_str = parts[1]
    shift_type = parts[2].lower()
    ids_text = parts[3].strip()

    if shift_type not in {"day", "evening"}:
        await message.answer("❌ shift_type должен быть day или evening.")
        return

    ids = []
    for chunk in ids_text.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            ids.append(int(chunk))
        except ValueError:
            await message.answer(f"❌ Не удалось прочитать ID: {chunk}")
            return

    if day_str not in SCHEDULE:
        SCHEDULE[day_str] = {"day": [], "evening": []}

    SCHEDULE[day_str][shift_type] = ids
    save_schedule(SCHEDULE)

    await message.answer(
        f"✅ График обновлён.\n"
        f"📅 {day_str}\n"
        f"🕒 {shift_type}\n"
        f"👥 {', '.join(str(x) for x in ids) if ids else 'пусто'}"
    )


async def dialogs_handler(message: Message):
    if not is_admin(message.chat.id):
        return

    try:
        active_count, new_count_sum, rows = await asyncio.to_thread(parse_dialogs_page)
        await message.answer(build_dialogs_message(active_count, new_count_sum, rows), disable_web_page_preview=True)
    except Exception as e:
        await message.answer(f"❌ Не удалось получить диалоги: {e}")


async def debug_dialogs_handler(message: Message):
    if not is_admin(message.chat.id):
        return

    try:
        raw_html = await asyncio.to_thread(fetch_url, DIGISELLER_DIALOGS_URL)
        snippet = html.escape(raw_html[:3500])
        await message.answer(f"<pre>{snippet}</pre>", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Ошибка debug: {e}")


async def watch_dialogs_on_handler(message: Message):
    if not is_admin(message.chat.id):
        return
    DIALOGS_STATE["watch_enabled"] = True
    save_dialogs_state(DIALOGS_STATE)
    await message.answer("✅ Авто-мониторинг диалогов включён.")


async def watch_dialogs_off_handler(message: Message):
    if not is_admin(message.chat.id):
        return
    DIALOGS_STATE["watch_enabled"] = False
    save_dialogs_state(DIALOGS_STATE)
    await message.answer("🛑 Авто-мониторинг диалогов выключен.")


async def news_status_handler(message: Message):
    if not is_admin(message.chat.id):
        return
    await message.answer(build_news_status_text())


async def admin_news_text_catcher(message: Message):
    if not is_admin(message.chat.id):
        return

    draft = PENDING_NEWS.get(str(message.chat.id))
    if not draft:
        return

    text = (message.text or "").strip()
    if not text:
        return

    platform = draft.get("platform")
    deadline_minutes = draft.get("deadline_minutes")

    if not platform or not deadline_minutes:
        await message.answer("❌ Недостаточно данных для рассылки.")
        return

    announcement_id = create_announcement(platform, deadline_minutes, text)
    target_users = get_platform_users(platform)

    sent_count = 0
    for user_id in target_users:
        try:
            await message.bot.send_message(
                user_id,
                f"📢 Новая информация от администратора\n"
                f"🌍 Платформа: {platform.upper()}\n\n"
                f"{text}\n\n"
                f"⏱ Время на ознакомление: {deadline_minutes} мин",
                reply_markup=acknowledge_keyboard(announcement_id)
            )
            sent_count += 1
        except Exception:
            continue

    PENDING_NEWS.pop(str(message.chat.id), None)
    save_pending_news(PENDING_NEWS)

    await message.answer(
        f"✅ Рассылка отправлена.\n"
        f"🌍 Платформа: {platform.upper()}\n"
        f"👥 Получателей: {sent_count}\n"
        f"⏱ Время: {deadline_minutes} мин"
    )

async def cancel_fine_amount_handler(message: Message):
    if not is_admin(message.chat.id):
        return

    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.answer(
            "Использование:\n"
            "/cancel_fine_amount ID сумма причина\n\n"
            "Пример:\n"
            "/cancel_fine_amount 781922474 500 ошибка бота"
        )
        return

    try:
        uid = int(parts[1])
        amount = int(parts[2])
    except ValueError:
        await message.answer("❌ ID и сумма должны быть числами.")
        return

    reason = parts[3]

    # Ищем самый свежий штраф на такую сумму
    matching_fines = [
        f for f in FINES
        if int(f["user_id"]) == uid and int(f["amount"]) == amount
    ]

    if not matching_fines:
        await message.answer(
            f"❌ У сотрудника {get_short_user_label(uid)} нет штрафа на сумму {amount} руб."
        )
        return

    matching_fines.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    fine_to_remove = matching_fines[0]

    FINES.remove(fine_to_remove)
    save_fines(FINES)

    await message.answer(
        f"✅ Штраф аннулирован\n"
        f"👤 Сотрудник: {get_short_user_label(uid)}\n"
        f"💸 Сумма: {amount} руб\n"
        f"📝 Причина отмены: {reason}"
    )

    try:
        await message.bot.send_message(
            uid,
            f"✅ Один из ваших штрафов был аннулирован администратором.\n"
            f"💸 Сумма: {amount} руб\n"
            f"📝 Причина: {reason}"
        )
    except Exception:
        pass

async def user_fines_handler(message: Message):
    if not is_admin(message.chat.id):
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование:\n/user_fines ID")
        return

    uid = int(parts[1])

    user_fines = [f for f in FINES if int(f["user_id"]) == uid]

    if not user_fines:
        await message.answer("📭 У сотрудника нет штрафов.")
        return

    lines = [f"📋 Штрафы {get_short_user_label(uid)}:\n"]

    for i, fine in enumerate(user_fines, start=1):
        lines.append(
            f"{i}. {fine['amount']} руб | {fine['reason']} | {fine['created_at']}"
        )

    await message.answer("\n".join(lines))

# =========================================================
# TEXT BUTTONS
# =========================================================
async def btn_instructions(message: Message):
    if message.chat.type != "private":
        return

    await instructions_handler(message)


async def btn_profile(message: Message):
    if message.chat.type != "private":
        return

    await profile_handler(message)


async def btn_my_week(message: Message):
    if message.chat.type != "private":
        return

    await my_week_handler(message)


async def btn_my_fines(message: Message):
    if message.chat.type != "private":
        return

    await my_fines_handler(message)


async def btn_shift_on(message: Message):
    if message.chat.type != "private":
        return

    await shift_on_handler(message)


async def btn_shift_off(message: Message):
    if message.chat.type != "private":
        return

    await shift_off_handler(message)


async def btn_today(message: Message):
    if message.chat.type != "private":
        return

    await today_handler(message)


async def btn_tomorrow(message: Message):
    if message.chat.type != "private":
        return

    await tomorrow_handler(message)


async def btn_need_admin(message: Message):
    if message.chat.type != "private":
        return

    await message.answer(
        "🚨 Выберите тип обращения к админу:",
        reply_markup=need_admin_keyboard()
    )


async def btn_admin_panel(message: Message):
    if message.chat.type != "private":
        return

    await admin_handler(message)

# =========================================================
# CALLBACKS
# =========================================================
async def service_handler(callback: CallbackQuery):
    service_key = callback.data.split(":")[1]
    if service_key not in DATA:
        await callback.answer("Раздел не найден", show_alert=True)
        return

    await callback.message.answer(
        f"📚 Вы выбрали: {DATA[service_key]['title']}\n\nВыберите инструкцию:",
        reply_markup=instructions_keyboard(service_key)
    )
    await callback.answer()


async def item_handler(callback: CallbackQuery):
    _, service_key, item_key = callback.data.split(":")
    if service_key not in DATA or item_key not in DATA[service_key]["items"]:
        await callback.answer("Инструкция не найдена", show_alert=True)
        return

    text = DATA[service_key]["items"][item_key]["text"]
    await callback.message.answer(
        text,
        reply_markup=back_to_list_keyboard(service_key),
        disable_web_page_preview=True
    )
    await callback.answer()


async def my_profile_handler(callback: CallbackQuery):
    ensure_shift_user(callback.from_user.id)
    update_profile_from_user(callback.from_user)
    is_on = SHIFT_STATUS[str(callback.from_user.id)]["is_on_shift"]
    await callback.message.answer(get_profile_text(callback.from_user.id), reply_markup=profile_inline_keyboard(is_on))
    await callback.answer()


async def my_fines_button_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_fines = get_user_fines(user_id)
    if not user_fines:
        await callback.message.answer("💸 У вас пока нет штрафов.")
        await callback.answer()
        return

    lines = ["💸 Ваши штрафы:\n"]
    for fine in user_fines[-15:]:
        lines.append(f"• {fine['created_at']} | {fine['amount']} руб | {fine['reason']}")

    await callback.message.answer("\n".join(lines))
    await callback.answer()


async def my_week_button_handler(callback: CallbackQuery):
    await callback.message.answer(build_my_week_text(callback.from_user.id))
    await callback.answer()


async def open_instructions_handler(callback: CallbackQuery):
    await callback.message.answer("📚 Выберите раздел инструкций:", reply_markup=services_keyboard())
    await callback.answer()


async def open_menu_handler(callback: CallbackQuery):
    await callback.message.answer("🏠 Главное меню", reply_markup=main_menu_keyboard(is_admin(callback.from_user.id)))
    await callback.answer()


async def shift_on_btn_handler(callback: CallbackQuery):
    update_profile_from_user(callback.from_user)
    ensure_shift_user(callback.from_user.id)
    text = await process_shift_on(callback.from_user.id, callback.bot)
    await callback.message.answer(text)
    await callback.answer()


async def shift_off_btn_handler(callback: CallbackQuery):
    text = await process_shift_off(callback.from_user.id, callback.bot)
    await callback.message.answer(text)
    await callback.answer()


async def admin_users_cb(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer(f"👥 Активированных пользователей: {len(USERS)}")
    await callback.answer()


async def admin_weekly_fines_cb(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer(build_weekly_fines_report())
    await callback.answer()


async def admin_who_should_work_cb(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer(build_who_should_work_text())
    await callback.answer()


async def admin_load_forecast_cb(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer(build_load_forecast_text())
    await callback.answer()


async def admin_dialogs_check_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    try:
        active_count, new_count_sum, rows = await asyncio.to_thread(parse_dialogs_page)
        await callback.message.answer(build_dialogs_message(active_count, new_count_sum, rows))
        await callback.answer("Обновлено")
    except Exception as e:
        await callback.answer("Ошибка", show_alert=True)
        await callback.message.answer(f"❌ Не удалось получить диалоги: {e}")


async def admin_news_start_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    PENDING_NEWS[str(callback.from_user.id)] = {}
    save_pending_news(PENDING_NEWS)

    await callback.message.answer("📢 Выберите платформу для рассылки:", reply_markup=news_platform_keyboard())
    await callback.answer()


async def news_platform_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    platform = callback.data.split(":")[1]
    draft = PENDING_NEWS.get(str(callback.from_user.id), {})
    draft["platform"] = platform
    PENDING_NEWS[str(callback.from_user.id)] = draft
    save_pending_news(PENDING_NEWS)

    await callback.message.answer(
        f"✅ Платформа выбрана: {platform.upper()}\n\n⏱ Теперь выберите время на ознакомление:",
        reply_markup=news_deadline_keyboard()
    )
    await callback.answer()


async def news_deadline_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    minutes = int(callback.data.split(":")[1])
    draft = PENDING_NEWS.get(str(callback.from_user.id), {})
    draft["deadline_minutes"] = minutes
    PENDING_NEWS[str(callback.from_user.id)] = draft
    save_pending_news(PENDING_NEWS)

    await callback.message.answer(
        f"✅ Время на ознакомление: {minutes} мин.\n\n📝 Теперь отправьте одним сообщением текст рассылки."
    )
    await callback.answer()


async def news_cancel_handler(callback: CallbackQuery):
    PENDING_NEWS.pop(str(callback.from_user.id), None)
    save_pending_news(PENDING_NEWS)
    await callback.message.answer("❌ Создание рассылки отменено.")
    await callback.answer()


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

    await callback.answer("Принято ✅")
    await callback.message.answer("✅ Ознакомление подтверждено.")

    short_text = f"✅ {get_short_user_label(user_id)} ознакомился | {get_platform_name(user_id)}"
    for admin_id in ADMIN_IDS:
        try:
            await callback.bot.send_message(admin_id, short_text)
        except Exception:
            pass


async def admin_not_read_cb(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer(build_not_read_text())
    await callback.answer()


async def need_admin_handler(callback: CallbackQuery):
    await callback.message.answer("🚨 Выберите тип обращения к админу:", reply_markup=need_admin_keyboard())
    await callback.answer()


async def req_admin_type_handler(callback: CallbackQuery):
    req_type = callback.data.split(":")[1]
    user_id = callback.from_user.id
    update_profile_from_user(callback.from_user)
    ensure_shift_user(user_id)

    add_request(user_id, req_type)

    req_name = {
        "urgent": "❗ Срочно",
        "question": "❓ Вопрос",
        "problem": "⚙️ Проблема"
    }.get(req_type, req_type)

    for admin_id in ADMIN_IDS:
        try:
            await callback.bot.send_message(
                admin_id,
                f"🚨 Запрос сотрудника\n"
                f"👤 {get_short_user_label(user_id)}\n"
                f"🧩 Платформа: {get_platform_name(user_id)}\n"
                f"🕒 Смена: {current_shift_name()}\n"
                f"📌 Тип: {req_name}\n"
                f"🆔 ID: {user_id}"
            )
        except Exception:
            pass

    await callback.message.answer("✅ Запрос админу отправлен.")
    await callback.answer()


async def req_admin_cancel_handler(callback: CallbackQuery):
    await callback.message.answer("❌ Запрос админу отменён.")
    await callback.answer()

# =========================================================
# MAIN
# =========================================================
async def main():
    if not TOKEN:
        raise ValueError("TOKEN не задан")

    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    # commands
    dp.message.register(start_handler, CommandStart())
    dp.message.register(menu_handler, Command("menu"))
    dp.message.register(instructions_handler, Command("instructions"))
    dp.message.register(profile_handler, Command("profile"))
    dp.message.register(id_handler, Command("id"))
    dp.message.register(my_fines_handler, Command("my_fines"))
    dp.message.register(my_week_handler, Command("my_week"))
    dp.message.register(admin_handler, Command("admin"))
    dp.message.register(users_count_handler, Command("users"))
    dp.message.register(list_users_handler, Command("list_users"))
    dp.message.register(workers_ai_handler, Command("workers_ai"))
    dp.message.register(workers_steam_handler, Command("workers_steam"))
    dp.message.register(shift_on_handler, Command("shift_on"))
    dp.message.register(shift_off_handler, Command("shift_off"))
    dp.message.register(fine_handler, Command("fine"))
    dp.message.register(weekly_fines_handler, Command("weekly_fines"))
    dp.message.register(user_view_handler, Command("user"))
    dp.message.register(who_should_work_handler, Command("who_should_work"))
    dp.message.register(load_forecast_handler, Command("load_forecast"))
    dp.message.register(today_handler, Command("today"))
    dp.message.register(tomorrow_handler, Command("tomorrow"))
    dp.message.register(week_handler, Command("week"))
    dp.message.register(set_schedule_handler, Command("set_schedule"))
    dp.message.register(dialogs_handler, Command("dialogs"))
    dp.message.register(debug_dialogs_handler, Command("debug_dialogs"))
    dp.message.register(watch_dialogs_on_handler, Command("watch_dialogs_on"))
    dp.message.register(watch_dialogs_off_handler, Command("watch_dialogs_off"))
    dp.message.register(news_status_handler, Command("news_status"))
    dp.message.register(remove_fine_handler, Command("remove_fine"))
    dp.message.register(chat_id_handler, Command("chat_id"))
    dp.message.register(cancel_fine_amount_handler, Command("cancel_fine_amount"))
    dp.message.register(user_fines_handler, Command("user_fines"))

    # text buttons
    dp.message.register(btn_instructions, F.text == "📚 Инструкции")
    dp.message.register(btn_profile, F.text == "👤 Профиль")
    dp.message.register(btn_my_week, F.text == "📊 Моя неделя")
    dp.message.register(btn_my_fines, F.text == "💸 Мои штрафы")
    dp.message.register(btn_shift_on, F.text == "🟢 Вышел на смену")
    dp.message.register(btn_shift_off, F.text == "🔴 Ушёл со смены")
    dp.message.register(btn_today, F.text == "🗓 Сегодня")
    dp.message.register(btn_tomorrow, F.text == "📅 Завтра")
    dp.message.register(btn_need_admin, F.text == "🚨 Нужен админ")
    dp.message.register(btn_admin_panel, F.text == "👑 Админ панель")

    # admin news text fallback
    dp.message.register(admin_news_text_catcher, F.text)

    # callbacks
    dp.callback_query.register(service_handler, F.data.startswith("service:"))
    dp.callback_query.register(item_handler, F.data.startswith("item:"))
    dp.callback_query.register(my_profile_handler, F.data == "my_profile")
    dp.callback_query.register(my_fines_button_handler, F.data == "my_fines_btn")
    dp.callback_query.register(my_week_button_handler, F.data == "my_week_btn")
    dp.callback_query.register(open_instructions_handler, F.data == "open_instructions")
    dp.callback_query.register(open_menu_handler, F.data == "open_menu")
    dp.callback_query.register(shift_on_btn_handler, F.data == "shift_on_btn")
    dp.callback_query.register(shift_off_btn_handler, F.data == "shift_off_btn")
    dp.callback_query.register(acknowledge_handler, F.data.startswith("ack:"))

    dp.callback_query.register(admin_users_cb, F.data == "admin_users")
    dp.callback_query.register(admin_weekly_fines_cb, F.data == "admin_weekly_fines")
    dp.callback_query.register(admin_who_should_work_cb, F.data == "admin_who_should_work")
    dp.callback_query.register(admin_load_forecast_cb, F.data == "admin_load_forecast")
    dp.callback_query.register(admin_dialogs_check_handler, F.data == "admin_dialogs_check")
    dp.callback_query.register(admin_news_start_handler, F.data == "admin_news_start")
    dp.callback_query.register(admin_not_read_cb, F.data == "admin_not_read")

    dp.callback_query.register(need_admin_handler, F.data == "need_admin")
    dp.callback_query.register(req_admin_type_handler, F.data.startswith("req_admin:"))
    dp.callback_query.register(req_admin_cancel_handler, F.data == "req_admin_cancel")

    dp.callback_query.register(news_platform_handler, F.data.startswith("news_platform:"))
    dp.callback_query.register(news_deadline_handler, F.data.startswith("news_deadline:"))
    dp.callback_query.register(news_cancel_handler, F.data == "news_cancel")

    # tasks
    asyncio.create_task(monitor_negative_reviews(bot))
    asyncio.create_task(monitor_dialogs(bot))
    asyncio.create_task(auto_check_absent_workers(bot))
    asyncio.create_task(monitor_announcements(bot))

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())










