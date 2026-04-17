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
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =========================================================
# НАСТРОЙКИ
# =========================================================
TOKEN = os.getenv("TOKEN")
DIGISELLER_COOKIE = os.getenv("COOKIE")

DIGISELLER_NEGATIVE_URL = "https://my.digiseller.com/inside/responses.asp?gb=2&shop=-1"
DIGISELLER_BASE_URL = "https://my.digiseller.com/inside/"
DIGISELLER_DIALOGS_URL = "https://my.digiseller.com/inside/messages.asp"

CHECK_INTERVAL_SECONDS = 60
DIALOGS_CHECK_INTERVAL_SECONDS = 10

USERS_FILE = "users.json"
SENT_REVIEWS_FILE = "sent_reviews.json"
ANNOUNCEMENTS_FILE = "announcements.json"
SHIFT_STATUS_FILE = "shift_status.json"
PROFILES_FILE = "profiles.json"
DIALOGS_STATE_FILE = "dialogs_state.json"
FINES_FILE = "fines.json"

MSK_TZ = ZoneInfo("Europe/Moscow")
LATE_FINE_AMOUNT = 500

DAY_SHIFT_START = time(11, 0)
DAY_SHIFT_LATE_AFTER = time(11, 15)
DAY_SHIFT_END = time(17, 30)

EVENING_SHIFT_START = time(17, 30)
EVENING_SHIFT_LATE_AFTER = time(17, 45)
EVENING_SHIFT_END = time(23, 59, 59)

# =========================================================
# АДМИНЫ
# =========================================================
ADMIN_IDS = [781922474, 135479524, 5384930958]

# =========================================================
# РАБОТНИКИ ПО ПЛАТФОРМАМ
# =========================================================
AI_WORKERS = [8225013907, 8177004956, 781922474, 5384930958, 1920853728, 844359525, 1294614140, 135479524, 1323864732]
STEAM_WORKERS = 7135999120, 742038308, 5384930958, 135479524, 1312771702, 5493517866]

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
            },
            "apple_email_password": {
                "button": "Вход через Apple ID",
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
                "button": "Вход через Google",
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
                "button": "Регионы подписок",
                "text": (
                    "🔴 Регион оплаты подписки:\n"
                    "➖ Подписка Индивидуал 3-6 месяцев - Египет\n"
                    "➖ Подписка Индивидуал 12 месяцев - Египет\n"
                    "➖ Подписки 1 месяц Индивидуал, Дуо, Фемели - Нигерия\n"
                    "➖ Подписки Дуо 3-6-12 месяцев - Египет\n"
                    "➖ Подписки Platinum/Standard/Lite - Индия"
                )
            },
            "lossless": {
                "button": "Lossless уже доступен",
                "text": (
                    "Если у тебя уже Premium-подписка, возможно, lossless уже доступен — "
                    "просто нужно проверить настройки и обновить приложение.\n"
                    " • Тебе не обязательно менять на новый тариф, если lossless уже поддерживается в твоём Premium."
                )
            },
            "duo_different_regions": {
                "button": "Spotify Duo разные регионы",
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
            },
            "cancel_plan": {
                "button": "Отменить автооплату",
                "text": (
                    "Пожалуйста отмените план нажав по Manage plan затем cancel plan указав любой из причин. "
                    "Это действие не отменит саму подписку а следующую оплату. Надеемся на ваше понимание"
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


USERS: Set[int] = load_users()
SENT_REVIEWS: Set[str] = load_sent_reviews()
ANNOUNCEMENTS: Dict[str, dict] = load_announcements()
SHIFT_STATUS: Dict[str, dict] = load_shift_status()
USER_PROFILES: Dict[str, dict] = load_profiles()
DIALOGS_STATE: Dict[str, dict] = load_dialogs_state()
FINES: List[dict] = load_fines()

# =========================================================
# КНОПКИ
# =========================================================
def services_keyboard():
    builder = InlineKeyboardBuilder()
    for service_key, service_data in DATA.items():
        builder.button(text=service_data["title"], callback_data=f"service:{service_key}")
    builder.button(text="👤 Мой профиль", callback_data="my_profile")
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


def admin_dialogs_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📨 Проверить диалоги", callback_data="admin_dialogs_check")
    builder.button(text="👤 Мой профиль", callback_data="my_profile")
    builder.adjust(1)
    return builder.as_markup()


def profile_keyboard(is_on_shift: bool):
    builder = InlineKeyboardBuilder()
    if not is_on_shift:
        builder.button(text="🟢 Вышел на смену", callback_data="shift_on_btn")
    else:
        builder.button(text="🔴 Ушел со смены", callback_data="shift_off_btn")
    builder.button(text="🏠 В главное меню", callback_data="back_main")
    builder.adjust(1)
    return builder.as_markup()

# =========================================================
# HELPERS
# =========================================================
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def update_profile_from_user(user) -> None:
    user_id = str(user.id)
    USER_PROFILES[user_id] = {
        "username": user.username or "",
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "updated_at": datetime.now(MSK_TZ).strftime("%Y-%m-%d %H:%M:%S")
    }
    save_profiles(USER_PROFILES)


def get_platform_name(user_id: int) -> str:
    if user_id in AI_WORKERS:
        return "AI"
    if user_id in STEAM_WORKERS:
        return "Steam"
    return "не назначена"


def get_role_name(user_id: int) -> str:
    return "админ" if is_admin(user_id) else "сотрудник"


def msk_now() -> datetime:
    return datetime.now(MSK_TZ)


def current_shift_type(now: datetime | None = None) -> str | None:
    now = now or msk_now()
    now_t = now.time()

    if DAY_SHIFT_START <= now_t < DAY_SHIFT_END:
        return "day"
    if EVENING_SHIFT_START <= now_t <= EVENING_SHIFT_END:
        return "evening"
    return None


def current_shift_name(now: datetime | None = None) -> str:
    shift_type = current_shift_type(now)
    if shift_type == "day":
        return "дневная"
    if shift_type == "evening":
        return "вечерняя"
    return "вне смены"


def is_late_for_current_shift(now: datetime | None = None) -> bool:
    now = now or msk_now()
    shift_type = current_shift_type(now)
    if shift_type == "day":
        return now.time() > DAY_SHIFT_LATE_AFTER
    if shift_type == "evening":
        return now.time() > EVENING_SHIFT_LATE_AFTER
    return False


def format_shift_window(now: datetime | None = None) -> str:
    shift_type = current_shift_type(now)
    if shift_type == "day":
        return "11:00–17:30 МСК"
    if shift_type == "evening":
        return "17:30–00:00 МСК"
    return "сейчас вне времени смен"


def ensure_shift_user(user_id: int):
    uid = str(user_id)
    if uid not in SHIFT_STATUS:
        SHIFT_STATUS[uid] = {
            "is_on_shift": False,
            "last_shift_on": "",
            "last_shift_off": "",
            "last_shift_type": "",
            "last_shift_date": "",
            "last_late": False
        }
        save_shift_status(SHIFT_STATUS)


def add_fine(user_id: int, amount: int, reason: str, source: str = "auto_late"):
    entry = {
        "user_id": int(user_id),
        "amount": int(amount),
        "reason": reason,
        "source": source,
        "created_at": msk_now().strftime("%Y-%m-%d %H:%M:%S")
    }
    FINES.append(entry)
    save_fines(FINES)


def get_user_fines(user_id: int) -> List[dict]:
    return [x for x in FINES if int(x["user_id"]) == int(user_id)]


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


def get_profile_text(user_id: int) -> str:
    ensure_shift_user(user_id)
    profile = USER_PROFILES.get(str(user_id), {})
    shift = SHIFT_STATUS.get(str(user_id), {})

    username = profile.get("username") or "нет"
    first_name = profile.get("first_name") or ""
    last_name = profile.get("last_name") or ""
    full_name = f"{first_name} {last_name}".strip() or "не указано"

    is_on_shift = shift.get("is_on_shift", False)
    last_shift_on = shift.get("last_shift_on") or "не было"
    last_shift_off = shift.get("last_shift_off") or "не было"
    last_shift_type = shift.get("last_shift_type") or "неизвестно"

    weekly_sum = get_user_weekly_fines_sum(user_id)
    total_sum = get_user_total_fines_sum(user_id)
    fines_count = len(get_user_fines(user_id))

    return (
        "👤 Ваш профиль\n\n"
        f"ID: {user_id}\n"
        f"Username: @{username}\n"
        f"Имя: {full_name}\n"
        f"Роль: {get_role_name(user_id)}\n"
        f"Платформа: {get_platform_name(user_id)}\n"
        f"Статус: {'на смене' if is_on_shift else 'не на смене'}\n"
        f"Текущая смена по МСК: {current_shift_name()}\n"
        f"Последняя отмеченная смена: {last_shift_type}\n"
        f"Последний выход на смену: {last_shift_on}\n"
        f"Последний уход со смены: {last_shift_off}\n"
        f"Штрафов всего: {fines_count}\n"
        f"Штрафы за 7 дней: {weekly_sum} руб\n"
        f"Общая сумма штрафов: {total_sum} руб"
    )


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
    ensure_shift_user(user_id)
    if SHIFT_STATUS.get(str(user_id), {}).get("is_on_shift", False):
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
        "/fine <user_id> <сумма> <причина> — отправить штраф сотруднику\n"
        "/weekly_fines — штрафы за последние 7 дней\n"
        "/dialogs — показать активные диалоги Digiseller\n"
        "/debug_dialogs — показать HTML-кусок страницы сообщений\n"
        "/watch_dialogs_on — включить авто-мониторинг диалогов\n"
        "/watch_dialogs_off — выключить авто-мониторинг диалогов\n"
        "/profile — мой профиль\n\n"
        "Команды работников:\n"
        "/shift_on — выйти на смену\n"
        "/shift_off — уйти со смены\n"
        "/profile — мой профиль\n"
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
        f"Номер счета: {review['invoice']}\n"
        f"Товар: {review['product']}\n"
        f"Покупатель: {review['buyer']}\n"
        "Отзыв:\n"
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
            f"   Товар: {row['product']}\n"
            f"   Сообщений всего/новых: {row['total_count']} / {row['new_count']}\n"
            f"   Время: {row['time']}\n"
        )

    if len(rows) > 20:
        lines.append(f"... и ещё {len(rows) - 20}")

    return "\n".join(lines)

# =========================================================
# МОНИТОРИНГ
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

# =========================================================
# СМЕНЫ И ШТРАФЫ
# =========================================================
async def process_shift_on(user_id: int, bot: Bot) -> str:
    ensure_shift_user(user_id)
    now = msk_now()
    shift_type = current_shift_type(now)

    if shift_type is None:
        return (
            "Сейчас нет активного окна смены.\n"
            "Дневная смена: 11:00–17:30 МСК\n"
            "Вечерняя смена: 17:30–00:00 МСК"
        )

    user_shift = SHIFT_STATUS[str(user_id)]
    if user_shift.get("is_on_shift", False):
        return "Вы уже отмечены как сотрудник на смене."

    late = is_late_for_current_shift(now)
    shift_name = "дневная" if shift_type == "day" else "вечерняя"

    user_shift["is_on_shift"] = True
    user_shift["last_shift_on"] = now.strftime("%Y-%m-%d %H:%M:%S")
    user_shift["last_shift_type"] = shift_name
    user_shift["last_shift_date"] = now.strftime("%Y-%m-%d")
    user_shift["last_late"] = late
    save_shift_status(SHIFT_STATUS)

    if not late:
        return (
            f"✅ Молодец, успел на {shift_name} смену.\n"
            f"Время отметки: {now.strftime('%H:%M:%S')} МСК\n"
            f"Окно смены: {format_shift_window(now)}"
        )

    add_fine(
        user_id=user_id,
        amount=LATE_FINE_AMOUNT,
        reason=f"Опоздание на {shift_name} смену",
        source="auto_late"
    )

    fine_text = (
        f"⚠️ Вы вышли на {shift_name} смену с опозданием.\n"
        f"Время отметки: {now.strftime('%H:%M:%S')} МСК\n"
        f"Штраф: {LATE_FINE_AMOUNT} руб"
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"⚠️ Авто-штраф за опоздание\n\n"
                f"{get_profile_text(user_id)}\n"
                f"Штраф: {LATE_FINE_AMOUNT} руб\n"
                f"Причина: опоздание на {shift_name} смену"
            )
        except Exception:
            pass

    return fine_text


async def process_shift_off(user_id: int) -> str:
    ensure_shift_user(user_id)
    now = msk_now()
    user_shift = SHIFT_STATUS[str(user_id)]

    if not user_shift.get("is_on_shift", False):
        return "Вы и так не отмечены как сотрудник на смене."

    user_shift["is_on_shift"] = False
    user_shift["last_shift_off"] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_shift_status(SHIFT_STATUS)

    return (
        "🔴 Вы ушли со смены.\n"
        f"Время: {now.strftime('%H:%M:%S')} МСК"
    )


def build_weekly_fines_report() -> str:
    border = msk_now() - timedelta(days=7)

    sums: Dict[int, int] = {}
    reasons: Dict[int, int] = {}

    for fine in FINES:
        try:
            dt = datetime.strptime(fine["created_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=MSK_TZ)
        except Exception:
            continue

        if dt < border:
            continue

        uid = int(fine["user_id"])
        sums[uid] = sums.get(uid, 0) + int(fine["amount"])
        reasons[uid] = reasons.get(uid, 0) + 1

    if not sums:
        return "За последние 7 дней штрафов нет."

    lines = ["📊 Штрафы за последние 7 дней:\n"]
    for uid, total in sorted(sums.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"{get_profile_text(uid)} | штрафов: {reasons[uid]} | сумма: {total} руб")

    return "\n".join(lines)

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
    ensure_shift_user(user_id)

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


async def profile_handler(message: Message):
    ensure_shift_user(message.chat.id)
    await message.answer(
        get_profile_text(message.chat.id),
        reply_markup=profile_keyboard(SHIFT_STATUS[str(message.chat.id)]["is_on_shift"])
    )


async def admin_handler(message: Message):
    if not is_admin(message.chat.id):
        await message.answer("У вас нет доступа к этой команде.")
        return
    await message.answer(admin_commands_text(), reply_markup=admin_dialogs_keyboard())


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
    update_profile_from_user(message.from_user)
    ensure_shift_user(message.chat.id)
    text = await process_shift_on(message.chat.id, message.bot)
    await message.answer(text, reply_markup=profile_keyboard(True))


async def shift_off_handler(message: Message):
    update_profile_from_user(message.from_user)
    ensure_shift_user(message.chat.id)
    text = await process_shift_off(message.chat.id)
    await message.answer(text, reply_markup=profile_keyboard(False))


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

    try:
        amount = int(parts[2])
    except ValueError:
        await message.answer("Сумма штрафа должна быть числом.")
        return

    reason = parts[3]

    add_fine(target_user_id, amount, reason, source="manual")

    fine_text = (
        "⚠️ Вам назначен штраф\n\n"
        f"Сумма штрафа: {amount} руб\n"
        f"Причина: {reason}"
    )

    try:
        await message.bot.send_message(target_user_id, fine_text)
        await message.answer(f"✅ Штраф отправлен пользователю {target_user_id}.")
    except Exception as e:
        await message.answer(f"Не удалось отправить штраф: {e}")


async def weekly_fines_handler(message: Message):
    if not is_admin(message.chat.id):
        await message.answer("У вас нет доступа к этой команде.")
        return
    await message.answer(build_weekly_fines_report())


async def dialogs_handler(message: Message):
    if not is_admin(message.chat.id):
        await message.answer("У вас нет доступа к этой команде.")
        return

    try:
        active_count, new_count_sum, rows = await asyncio.to_thread(parse_dialogs_page)
        await message.answer(build_dialogs_message(active_count, new_count_sum, rows), disable_web_page_preview=True)
    except Exception as e:
        await message.answer(f"Не удалось получить диалоги: {e}")


async def debug_dialogs_handler(message: Message):
    if not is_admin(message.chat.id):
        await message.answer("У вас нет доступа к этой команде.")
        return

    try:
        raw_html = await asyncio.to_thread(fetch_url, DIGISELLER_DIALOGS_URL)
        snippet = html.escape(raw_html[:3500])
        await message.answer(f"<pre>{snippet}</pre>", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Ошибка debug: {e}")


async def watch_dialogs_on_handler(message: Message):
    if not is_admin(message.chat.id):
        await message.answer("У вас нет доступа к этой команде.")
        return
    DIALOGS_STATE["watch_enabled"] = True
    save_dialogs_state(DIALOGS_STATE)
    await message.answer("✅ Авто-мониторинг диалогов включен.")


async def watch_dialogs_off_handler(message: Message):
    if not is_admin(message.chat.id):
        await message.answer("У вас нет доступа к этой команде.")
        return
    DIALOGS_STATE["watch_enabled"] = False
    save_dialogs_state(DIALOGS_STATE)
    await message.answer("🛑 Авто-мониторинг диалогов выключен.")


async def acknowledge_handler(callback: CallbackQuery):
    _, announcement_id = callback.data.split(":", 1)

    if announcement_id not in ANNOUNCEMENTS:
        await callback.answer("Сообщение не найдено", show_alert=True)
        return

    user_id = callback.from_user.id
    update_profile_from_user(callback.from_user)
    ensure_shift_user(user_id)

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


async def admin_dialogs_check_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    try:
        active_count, new_count_sum, rows = await asyncio.to_thread(parse_dialogs_page)
        msg = build_dialogs_message(active_count, new_count_sum, rows)
        await callback.message.answer(msg, disable_web_page_preview=True)
        await callback.answer("Обновлено")
    except Exception as e:
        await callback.answer("Ошибка", show_alert=True)
        await callback.message.answer(f"Не удалось получить диалоги: {e}")


async def my_profile_handler(callback: CallbackQuery):
    ensure_shift_user(callback.from_user.id)
    update_profile_from_user(callback.from_user)
    is_on = SHIFT_STATUS[str(callback.from_user.id)]["is_on_shift"]
    await callback.message.answer(get_profile_text(callback.from_user.id), reply_markup=profile_keyboard(is_on))
    await callback.answer()


async def shift_on_btn_handler(callback: CallbackQuery):
    update_profile_from_user(callback.from_user)
    ensure_shift_user(callback.from_user.id)
    text = await process_shift_on(callback.from_user.id, callback.bot)
    await callback.message.answer(text, reply_markup=profile_keyboard(True))
    await callback.answer()


async def shift_off_btn_handler(callback: CallbackQuery):
    update_profile_from_user(callback.from_user)
    ensure_shift_user(callback.from_user.id)
    text = await process_shift_off(callback.from_user.id)
    await callback.message.answer(text, reply_markup=profile_keyboard(False))
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
    dp.message.register(profile_handler, Command("profile"))
    dp.message.register(admin_handler, Command("admin"))
    dp.message.register(users_count_handler, Command("users"))
    dp.message.register(list_users_handler, Command("list_users"))
    dp.message.register(workers_ai_handler, Command("workers_ai"))
    dp.message.register(workers_steam_handler, Command("workers_steam"))
    dp.message.register(shift_on_handler, Command("shift_on"))
    dp.message.register(shift_off_handler, Command("shift_off"))
    dp.message.register(news_handler, Command("news"))
    dp.message.register(fine_handler, Command("fine"))
    dp.message.register(weekly_fines_handler, Command("weekly_fines"))
    dp.message.register(dialogs_handler, Command("dialogs"))
    dp.message.register(debug_dialogs_handler, Command("debug_dialogs"))
    dp.message.register(watch_dialogs_on_handler, Command("watch_dialogs_on"))
    dp.message.register(watch_dialogs_off_handler, Command("watch_dialogs_off"))

    dp.callback_query.register(acknowledge_handler, F.data.startswith("ack:"))
    dp.callback_query.register(service_handler, F.data.startswith("service:"))
    dp.callback_query.register(item_handler, F.data.startswith("item:"))
    dp.callback_query.register(back_main_handler, F.data == "back_main")
    dp.callback_query.register(admin_dialogs_check_handler, F.data == "admin_dialogs_check")
    dp.callback_query.register(my_profile_handler, F.data == "my_profile")
    dp.callback_query.register(shift_on_btn_handler, F.data == "shift_on_btn")
    dp.callback_query.register(shift_off_btn_handler, F.data == "shift_off_btn")

    asyncio.create_task(monitor_negative_reviews(bot))
    asyncio.create_task(monitor_dialogs(bot))

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())










