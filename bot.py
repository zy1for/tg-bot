import asyncio
import json
import logging
import os
import re
from typing import Dict, List, Set

import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =========================================================
# НАСТРОЙКИ
# =========================================================
TOKEN = os.getenv("8568651712:AAHUlJCPzQy5KNko2Esu_BeuBpli6fwivuI")
DIGISELLER_COOKIE = os.getenv("curr=WMZ; period=days; tabMessages1=buyers; lang=ru%2DRU; ASPSESSIONIDCSSBDSDR=JKALLGHDHHIDIFGOKKDJAMEP")

DIGISELLER_NEGATIVE_URL = "https://my.digiseller.com/inside/responses.asp?gb=2&shop=-1"
DIGISELLER_BASE_URL = "https://my.digiseller.com/inside/"
CHECK_INTERVAL_SECONDS = 60

USERS_FILE = "users.json"
SENT_REVIEWS_FILE = "sent_reviews.json"
ANNOUNCEMENTS_FILE = "announcements.json"

# ВАЖНО:
# сюда вставь свой Telegram user ID
ADMIN_ID = 5384930958


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
# ФУНКЦИИ ХРАНЕНИЯ
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


USERS: Set[int] = load_users()
SENT_REVIEWS: Set[str] = load_sent_reviews()
ANNOUNCEMENTS: Dict[str, dict] = load_announcements()


# =========================================================
# КЛАВИАТУРЫ
# =========================================================
def services_keyboard():
    builder = InlineKeyboardBuilder()

    for service_key, service_data in DATA.items():
        builder.button(
            text=service_data["title"],
            callback_data=f"service:{service_key}"
        )

    builder.adjust(2)
    return builder.as_markup()


def instructions_keyboard(service_key: str):
    builder = InlineKeyboardBuilder()

    for item_key, item_data in DATA[service_key]["items"].items():
        builder.button(
            text=item_data["button"],
            callback_data=f"item:{service_key}:{item_key}"
        )

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

        found.append({
            "id": review_id,
            "link": full_link
        })

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
            await bot.send_message(
                chat_id=user_id,
                text=text,
                disable_web_page_preview=True
            )
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

    try:
        await message.bot.send_message(ADMIN_ID, admin_text)
    except Exception as e:
        logging.warning(f"Не удалось отправить уведомление админу о /start: {e}")


async def id_handler(message: Message):
    await message.answer(f"Ваш user ID: {message.chat.id}")


async def users_count_handler(message: Message):
    if message.chat.id != ADMIN_ID:
        await message.answer("У вас нет доступа к этой команде.")
        return
    await message.answer(f"Активированных пользователей: {len(USERS)}")


async def announce_handler(message: Message):
    if message.chat.id != ADMIN_ID:
        await message.answer("У вас нет доступа к этой команде.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование:\n/announce ваш текст")
        return

    announcement_text = parts[1]
    announcement_id = str(int(asyncio.get_event_loop().time() * 1000))

    ANNOUNCEMENTS[announcement_id] = {
        "text": announcement_text,
        "acked_by": []
    }
    save_announcements(ANNOUNCEMENTS)

    success_count = 0

    for user_id in USERS:
        try:
            await message.bot.send_message(
                user_id,
                f"📢 Новая информация от администратора\n\n{announcement_text}",
                reply_markup=acknowledge_keyboard(announcement_id)
            )
            success_count += 1
        except Exception as e:
            logging.warning(f"Не удалось отправить объявление пользователю {user_id}: {e}")

    await message.answer(f"✅ Сообщение отправлено.\nПолучателей: {success_count}")


async def acknowledge_handler(callback: CallbackQuery):
    _, announcement_id = callback.data.split(":", 1)

    if announcement_id not in ANNOUNCEMENTS:
        await callback.answer("Сообщение не найдено", show_alert=True)
        return

    user_id = callback.from_user.id
    username = callback.from_user.username
    first_name = callback.from_user.first_name or ""
    last_name = callback.from_user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()

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

    try:
        await callback.message.answer("✅ Вы подтвердили ознакомление.")
    except Exception:
        pass

    try:
        await callback.bot.send_message(
            ADMIN_ID,
            "✅ Сотрудник ознакомился с информацией\n\n"
            f"ID: {user_id}\n"
            f"Username: @{username if username else 'нет'}\n"
            f"Имя: {full_name or 'не указано'}\n"
            f"Текст: {ANNOUNCEMENTS[announcement_id]['text'][:300]}"
        )
    except Exception as e:
        logging.warning(f"Не удалось отправить админу подтверждение: {e}")


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
    dp.message.register(id_handler, F.text == "/id")
    dp.message.register(users_count_handler, F.text == "/users")
    dp.message.register(announce_handler, F.text.startswith("/announce"))
    dp.callback_query.register(acknowledge_handler, F.data.startswith("ack:"))
    dp.callback_query.register(service_handler, F.data.startswith("service:"))
    dp.callback_query.register(item_handler, F.data.startswith("item:"))
    dp.callback_query.register(back_main_handler, F.data == "back_main")

    asyncio.create_task(monitor_negative_reviews(bot))

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())











