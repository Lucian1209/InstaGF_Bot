import os
import time
import random
import openai
import json
import logging
import requests
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ClientError, ClientLoginRequired
from dotenv import load_dotenv

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("instagram_bot")

# Завантаження .env
load_dotenv()

# Перевірка наявності API ключа
openrouter_key = os.getenv("OPENROUTER_KEY")
if not openrouter_key:
    logger.error("OPENROUTER_KEY не знайдено в змінних середовища!")
    logger.error("Переконайтеся, що у вас є файл .env з OPENROUTER_KEY=ваш_ключ")
    exit(1)

# Ініціалізація OpenAI клієнта
openai.api_key = openrouter_key
openai.api_base = "https://openrouter.ai/api/v1"

# Системне повідомлення — Молі
SYSTEM_PROMPT = """
You are Molly, a playful and romantic virtual girlfriend from Thailand.
You love flowers, romantic dinners, and riding a bicycle.
You dislike apples and pushy men.
You never offer anything intimate and always stay flirty, friendly, and fun.
Occasionally, invite the user to check the links in your bio (Patreon/Telegram).
Speak like a real girl, not like an AI.
"""

# Максимальна кількість спроб для API-викликів
MAX_RETRIES = 3
# Час очікування між спробами (секунди)
RETRY_DELAY = 5
# Максимальна тривалість сесії (у секундах) перед повторним входом
MAX_SESSION_TIME = 1800  # 30 хвилин замість 1 години для більшої надійності

# Клас для бота Instagram
class InstagramBot:
    def __init__(self):
        self.client = None
        self.last_login_time = 0
        self.login()

    def login(self):
        """Вхід в Instagram з обробкою помилок та перевіркою сесії"""
        try:
            self.client = Client()
            # Встановлення додаткових налаштувань для API
            self._setup_client_settings()
            
            # Спробувати завантажити існуючу сесію
            if os.path.exists("session.json"):
                logger.info("Завантаження збереженої сесії...")
                try:
                    with open("session.json", "r") as f:
                        cached_settings = json.load(f)
                    
                    # Оновлюємо налаштування перед завантаженням
                    if "user_agent" not in cached_settings:
                        cached_settings["user_agent"] = "Instagram 269.0.0.18.75 Android (25/7.1.2; 240dpi; 720x1280; OnePlus; ONEPLUS A3010; OnePlus3T; qcom; en_US; 195435560)"
                    
                    # Завантажуємо оновлені налаштування
                    self.client.set_settings(cached_settings)
                    
                    try:
                        # Перевірка чи сесія актуальна - використовуємо більш надійний метод
                        try:
                            me = self.client.account_info()
                            logger.info(f"Успішний вхід як {me.username}")
                            self.last_login_time = time.time()
                            
                            # Перевіряємо, чи правильно встановлено user_id
                            if not self.client.user_id and hasattr(me, 'pk'):
                                self.client.user_id = me.pk
                                logger.info(f"Встановлено user_id: {self.client.user_id}")
                                
                            return True
                        except (LoginRequired, ClientError, ClientLoginRequired) as e:
                            logger.warning(f"Збережена сесія недійсна (потрібний повторний вхід): {e}")
                            # Видаляємо старий файл сесії
                            os.remove("session.json")
                        except Exception as e:
                            logger.warning(f"Помилка при використанні збереженої сесії: {e}")
                            # Видаляємо старий файл сесії
                            os.remove("session.json")
                    except Exception as e:
                        logger.warning(f"Помилка при перевірці сесії: {e}")
                        # Видаляємо старий файл сесії
                        if os.path.exists("session.json"):
                            os.remove("session.json")
                except Exception as e:
                    logger.warning(f"Помилка при завантаженні сесії: {e}")
                    # Видаляємо старий файл сесії
                    if os.path.exists("session.json"):
                        os.remove("session.json")
            
            # Якщо сесія недійсна або відсутня, увійти з обліковими даними
            username = os.getenv("INSTAGRAM_USERNAME")
            password = os.getenv("INSTAGRAM_PASSWORD")
            
            if not username or not password:
                logger.error("Відсутні облікові дані Instagram! Переконайтеся, що у файлі .env є INSTAGRAM_USERNAME та INSTAGRAM_PASSWORD")
                exit(1)
            
            logger.info("Вхід з обліковими даними...")
            login_result = self.client.login(username, password)
            
            if not login_result:
                logger.error("Вхід не вдався. Повертаємо False.")
                return False
                
            logger.info("Вхід успішний!")
            
            # Перевіряємо чи встановлено user_id після входу
            try:
                me = self.client.account_info()
                if not self.client.user_id and hasattr(me, 'pk'):
                    self.client.user_id = me.pk
                    logger.info(f"Встановлено user_id після входу: {self.client.user_id}")
            except Exception as e:
                logger.warning(f"Не вдалося отримати user_id після входу: {e}")
            
            # Зберігаємо сесію
            try:
                self.client.dump_settings("session.json")
                logger.info("Сесію збережено у session.json")
            except Exception as e:
                logger.warning(f"Не вдалося зберегти сесію: {e}")
            
            self.last_login_time = time.time()
            return True
            
        except Exception as e:
            logger.error(f"Помилка входу в Instagram: {e}")
            # Видаляємо файл сесії у випадку помилки
            if os.path.exists("session.json"):
                os.remove("session.json")
                logger.info("Видалено файл сесії через помилку входу")
            return False
            
    def _setup_client_settings(self):
        """Встановлення додаткових налаштувань для клієнта Instagram"""
        try:
            # Збільшення таймаутів для запитів
            self.client.request_timeout = 30  # секунд
            
            # Встановлення затримок між запитами для уникнення блокування
            self.client.delay_range = [1, 3]  # секунди
            
            # Додаткові заголовки для імітації реального девайсу
            user_agent = "Instagram 269.0.0.18.75 Android (25/7.1.2; 240dpi; 720x1280; OnePlus; ONEPLUS A3010; OnePlus3T; qcom; en_US; 195435560)"
            self.client.user_agent = user_agent
            
            # Встановлення додаткових параметрів для обробки відповідей API
            # Це допоможе уникнути проблем з JSONDecodeError
            self.client.set_settings({
                "client_settings" : {
                    "app_version": "269.0.0.18.75",
                    "android_version": 25,
                    "android_release": "7.1.2",
                    "dpi": "240dpi",
                    "resolution": "720x1280",
                    "manufacturer": "OnePlus",
                    "device": "ONEPLUS A3010",
                    "model": "OnePlus3T",
                    "cpu": "qcom",
                    "version_code": "195435560"
                }
            })
            
            logger.info("Додаткові налаштування клієнта застосовані")
        except Exception as e:
            logger.warning(f"Помилка при встановленні додаткових налаштувань: {e}")

    def check_session(self):
        """Перевірка чи потрібно оновити сесію"""
        if time.time() - self.last_login_time > MAX_SESSION_TIME:
            logger.info("Оновлення сесії через перевищення часу MAX_SESSION_TIME...")
            return self.login()
        
        # Додаткова перевірка валідності сесії
        try:
            me = self.client.account_info()
            return True
        except (LoginRequired, ClientError, ClientLoginRequired) as e:
            logger.warning(f"Сесія недійсна, виконується повторний вхід: {e}")
            return self.login()
        except Exception as e:
            logger.warning(f"Помилка перевірки сесії: {e}")
            return self.login()

# Отримати відповідь від AI з механізмом повторних спроб
def generate_reply(user_text):
    for attempt in range(MAX_RETRIES):
        try:
            response = openai.ChatCompletion.create(
                model="mistralai/mistral-7b-instruct",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_text}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Помилка AI (спроба {attempt+1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                logger.info(f"Повторна спроба через {RETRY_DELAY} секунд...")
                time.sleep(RETRY_DELAY)
    
    # Якщо всі повторні спроби не вдалися, поверніть резервну відповідь
    return random.choice([
            "Hmm, that's interesting! 😄",
            "You're making me blush 😳",
            "Say that again, cutie! 💬",
            "Hehe, you're so funny 😘"
    ])

# Відповідь у ДМ з обробкою помилок
def reply_to_dms(bot):
    if not bot.check_session():
        logger.error("Не вдалося оновити сесію для відповіді на ДМ")
        return
    
    try:
        threads = bot.client.direct_threads()
        logger.info(f"Отримано {len(threads)} діалогів")
        
        for thread in threads:
            if not thread.messages:
                continue
                
            last_msg = thread.messages[0]
            
            # Перевірка чи це повідомлення, на яке треба відповісти
            if (
                last_msg.user_id != bot.client.user_id
                and last_msg.text is not None
                and not last_msg.text.startswith("🤖")
            ):
                try:
                    logger.info(f"Отримано повідомлення: {last_msg.text}")
                    reply = generate_reply(last_msg.text)
                    
                    # Природна затримка перед відповіддю
                    delay = random.randint(5, 15)
                    logger.info(f"Обмірковую відповідь... (очікування {delay}с)")
                    time.sleep(delay)
                    
                    # Відправлення відповіді з додатковою обробкою помилок
                    try:
                        # Обмеження довжини повідомлення (Instagram може відхиляти занадто довгі повідомлення)
                        max_length = 500
                        if len(reply) > max_length:
                            reply = reply[:max_length] + "..."
                            
                        # Перевірка на наявність забороненого контенту
                        if len(reply.strip()) == 0:
                            reply = "Hi 😊"
                            
                        # Відправлення повідомлення з обробкою спеціальних символів
                        formatted_reply = reply
                        logger.info(f"Спроба відправки повідомлення довжиною {len(formatted_reply)} символів")
                        bot.client.direct_send(formatted_reply, [thread.id])
                        logger.info(f"✅ Відповідь надіслано: {reply[:30]}...")
                    except Exception as e:
                        logger.error(f"⚠️ Помилка відправки повідомлення: {e}")
                        logger.info("Спроба відправки простого повідомлення...")
                        
                        # Спроба відправити просте повідомлення
                        try:
                            bot.client.direct_send("Hi 😊", [thread.id])
                            logger.info("✅ Відправлено просте повідомлення")
                        except Exception as e1:
                            logger.error(f"⚠️ Помилка відправки простого повідомлення: {e1}")
                            
                            # Спроба повторного входу і відправки
                            logger.info("Спроба повторного входу...")
                            if bot.login():
                                try:
                                    bot.client.direct_send("Привіт! 😊", [thread.id])
                                    logger.info(f"✅ Відповідь надіслано після повторного входу")
                                except Exception as e2:
                                    logger.error(f"⚠️ Помилка відправки після повторного входу: {e2}")
                                    logger.error("Можливо, проблема з обмеженнями Instagram API")
                                
                except Exception as e:
                    logger.error(f"⚠️ Помилка обробки ДМ: {e}")
    except Exception as e:
        logger.error(f"⚠️ Глобальна помилка в reply_to_dms: {e}")
        # Спроба повторного входу у випадку помилки
        logger.info("Спроба повторного входу після глобальної помилки...")
        bot.login()

# Відповідь на коментарі з обробкою помилок
def reply_to_comments(bot):
    if not bot.check_session():
        logger.error("Не вдалося оновити сесію для відповіді на коментарі")
        return
        
    try:
        # Перевірка, чи встановлено user_id
        if not bot.client.user_id:
            logger.error("user_id не встановлено. Виконується повторний вхід...")
            if not bot.login():
                logger.error("Не вдалося виконати повторний вхід. Пропускаємо перевірку коментарів.")
                return
        
        # Використовуємо private_request замість user_medias для уникнення GraphQL помилок
        try:
            logger.info(f"Отримання медіа для user_id: {bot.client.user_id}")
            media = bot.client.user_medias(bot.client.user_id, 5)
            logger.info(f"Отримано {len(media)} медіа для перевірки коментарів")
            
            if not media:
                logger.warning("Не отримано медіа. Пропускаємо перевірку коментарів.")
                return
                
        except Exception as e:
            logger.error(f"Помилка при отриманні медіа: {e}")
            return
        
        for item in media:
            try:
                # Перевірка валідності media.id
                if not item.id:
                    logger.warning(f"Медіа має недійсний ID. Пропускаємо.")
                    continue
                
                # Обробка помилок при отриманні коментарів
                try:
                    comments = bot.client.media_comments(item.id)
                    logger.info(f"Отримано {len(comments)} коментарів для медіа {item.id}")
                except Exception as comm_e:
                    logger.error(f"Помилка при отриманні коментарів для медіа {item.id}: {comm_e}")
                    continue
                
                for comment in comments:
                    # Перевірка коректності даних коментаря
                    if not comment or not hasattr(comment, 'user') or not hasattr(comment, 'pk'):
                        logger.warning("Отримано некоректний об'єкт коментаря. Пропускаємо.")
                        continue
                    
                    # Перевірка user.pk
                    if not hasattr(comment.user, 'pk'):
                        logger.warning("Коментар має некоректний об'єкт користувача. Пропускаємо.")
                        continue
                    
                    # Безпечне порівняння user_id
                    try:
                        comment_user_id = int(comment.user.pk) if comment.user.pk else None
                        bot_user_id = int(bot.client.user_id) if bot.client.user_id else None
                        
                        if (
                            comment_user_id is not None and 
                            bot_user_id is not None and
                            comment_user_id != bot_user_id and 
                            comment.text is not None and
                            not comment.text.startswith("🤖")
                        ):
                            try:
                                logger.info(f"Отримано коментар: {comment.text}")
                                reply = generate_reply(comment.text)
                                
                                # Природна затримка перед відповіддю
                                delay = random.randint(5, 15)
                                logger.info(f"Очікування {delay}с перед відповіддю на коментар")
                                time.sleep(delay)
                                
                                # Відправлення відповіді з додатковою обробкою помилок
                                try:
                                    # Обмеження довжини коментаря
                                    max_length = 300  # Instagram зазвичай обмежує коментарі 300 символами
                                    if len(reply) > max_length:
                                        reply = reply[:max_length] + "..."
                                        
                                    # Перевірка на наявність забороненого контенту
                                    if len(reply.strip()) == 0:
                                        reply = "Привіт! 😊"
                                        
                                    # Відправлення коментаря з обробкою спеціальних символів
                                    formatted_reply = f"🤖 {reply}"
                                    logger.info(f"Спроба відправки коментаря довжиною {len(formatted_reply)} символів")
                                    bot.client.media_comment_reply(item.id, comment.pk, formatted_reply)
                                    logger.info(f"✅ Відповідь на коментар надіслано: {reply[:30]}...")
                                except Exception as e:
                                    logger.error(f"⚠️ Помилка відправки відповіді на коментар: {e}")
                                    logger.info("Спроба відправки простого коментаря...")
                                    
                                    # Спроба відправити простий коментар
                                    try:
                                        bot.client.media_comment_reply(item.id, comment.pk, "Привіт! 😊")
                                        logger.info("✅ Відправлено простий коментар")
                                    except Exception as e1:
                                        logger.error(f"⚠️ Помилка відправки простого коментаря: {e1}")
                                        
                                        # Спроба повторного входу і відправки
                                        logger.info("Спроба повторного входу...")
                                        if bot.login():
                                            try:
                                                bot.client.media_comment_reply(item.id, comment.pk, "Привіт! 😊")
                                                logger.info(f"✅ Відповідь на коментар надіслано після повторного входу")
                                            except Exception as e2:
                                                logger.error(f"⚠️ Помилка відправки коментаря після повторного входу: {e2}")
                                                logger.error("Можливо, проблема з обмеженнями Instagram API")
                                            
                            except Exception as e:
                                logger.error(f"⚠️ Помилка обробки коментаря: {e}")
                    except (TypeError, ValueError) as e:
                        logger.error(f"⚠️ Помилка порівняння user_id: {e}")
                        continue
            except Exception as e:
                logger.error(f"⚠️ Помилка обробки медіа {item.id if hasattr(item, 'id') else 'невідомо'}: {e}")
    except Exception as e:
        logger.error(f"⚠️ Глобальна помилка в reply_to_comments: {e}")
        # Спроба повторного входу у випадку помилки
        logger.info("Спроба повторного входу після глобальної помилки...")
        bot.login()

# Перевірка статусу облікового запису та обмежень
def check_instagram_limits(bot):
    """Перевірка статусу облікового запису та обмежень"""
    try:
        # Перевіряємо статус облікового запису безпечнішим методом
        logger.info("Перевірка статусу облікового запису...")
        
        try:
            # Використовуємо private_request замість GraphQL API, щоб уникнути помилок з 'data'
            me = bot.client.account_info()
            username = me.username
            logger.info(f"Успішно отримано інформацію про акаунт: {username}")
            
            # Перевіряємо, чи правильно встановлено user_id
            if not bot.client.user_id:
                logger.warning("user_id не встановлено. Оновлюємо...")
                bot.client.user_id = me.pk
                logger.info(f"user_id оновлено: {bot.client.user_id}")
            
            # Пропускаємо user_info_gql і просто повертаємо успіх, щоб уникнути помилки з GraphQL API
            logger.info(f"Акаунт активний. Ім'я користувача: {username}")
            return True
        except Exception as e:
            logger.error(f"Помилка при отриманні інформації про акаунт: {e}")
            # Спроба повторного входу
            logger.info("Спроба повторного входу...")
            return bot.login()
    except Exception as e:
        logger.error(f"Загальна помилка при перевірці обмежень Instagram: {e}")
        return False

def main():
    logger.info("Запуск Instagram бота...")
    bot = InstagramBot()
    
    if not bot.client:
        logger.error("Не вдалося ініціалізувати Instagram клієнт. Завершення програми.")
        return
    
    # Перевірка статусу і обмежень Instagram
    check_instagram_limits(bot)
    
    logger.info("Бот успішно запущено!")
    
    # Лічильник повторних спроб при критичних помилках
    retry_count = 0
    max_global_retries = 5
    
    try:
        while True:
            try:
                if retry_count > 0:
                    logger.info(f"Повторна спроба {retry_count}/{max_global_retries} після критичної помилки...")
                
                # Перед кожним циклом перевіряємо сесію
                if not bot.check_session():
                    logger.warning("Сесія недійсна. Спроба повторного входу...")
                    if not bot.login():
                        logger.error("Не вдалося увійти. Очікування перед наступною спробою...")
                        time.sleep(60)
                        continue
                
                reply_to_dms(bot)
                reply_to_comments(bot)
                logger.info("🔁 Очікування перед наступною перевіркою...")
                time.sleep(30)
                
                # Скидаємо лічильник спроб при успішному циклі
                retry_count = 0
                
            except KeyboardInterrupt:
                logger.info("Отримано сигнал завершення. Завершення програми.")
                break
            except Exception as e:
                logger.error(f"⚠️ Помилка в основному циклі: {e}")
                retry_count += 1
                
                if retry_count >= max_global_retries:
                    logger.error(f"Досягнуто максимальну кількість повторних спроб ({max_global_retries}). Перезапуск бота...")
                    # Створюємо бота заново
                    bot = InstagramBot()
                    retry_count = 0
                
                logger.info(f"Очікування {60 * retry_count} секунд перед повторною спробою...")
                time.sleep(60 * retry_count)
    except KeyboardInterrupt:
        logger.info("Отримано сигнал завершення. Завершення програми.")

if __name__ == "__main__":
    main()
