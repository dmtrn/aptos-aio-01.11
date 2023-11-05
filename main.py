import telebot
from loguru import logger

from config import tg_token
from models.database import Database
from modules.warmup import (
    warmup,
    stake,
    collector,
    aptos_name,
    withdraw_aptos,
    claim_bridged_tokens,
    sub_aptos_name
)
from utils import send_msg

start_message = r'''

                                  ^Y                  
                                 ~&@7                
                      75~:.     !@&~&:       , .      
                      .&&PYY7^.7@@# J#   .^7JPB^      
                       ^@&Y:^?Y&@@P  GBB&@@GP&~       
                        7@@&?  :&@J  G@@&Y.~#^        
                     .:~?&#&@&? !@! B@G~  !&:         
                :75PPY?!^. .:?GG~P!5P~^!YG@@GJ~.      
                .~YG#&&##B#BGPJ?J??J?J5GBBBB##&#B5!.  
                    .^?P&@BJ!^^5G~G^5GJ^. .:!?Y5P57:\  
                       .#?  ^P@#.:@J !&@@#&J~^.       
                      :#7.J&@@#. !@@~  !&@@5          
                     ^&GP@@&BG#. J@@@5?~:?&@7         
                    :BGJ7^..  GG P@@J.:!JY5&@:        
                    .         .&7B@?      .~YJ        
                              ^&@7                   
                                ?!                  
                                                                       
               __    _ __                        __                  
   _______  __/ /_  (_) /  _   __   ____  ____ _/ /______  ____  ___ 
  / ___/ / / / __ \/ / /  | | / /  /_  / / __ `/ //_/ __ \/ __ \/ _ \
 (__  ) /_/ / /_/ / / /   | |/ /    / /_/ /_/ / ,< / /_/ / / / /  __/   
/____/\__, /_.___/_/_/    |___/    /___/\__,_/_/|_|\____/_/ /_/\___/ 
     /____/                                                          

Modules v2.0:
1: create_database        | создать базу данных
2: default_warmup         | обычный прогрев кошельков
3: okx_gas_warmup         | прогрев кошельков с выводом газа
4: low_bank_warmup        | прогрев через okx для лоубанков
5: collector              | сбор всех монет на аккаунте в apt токен
6: register_domain        | регистрирует на аккаунт домен (aptosname)
7: register_subdomain     | регистрирует на аккаунт субдомен (sub aptosname)
8: claim_bridged_tokens   | клеймит токены отправленные из evm (юзать только там, где они есть)
9: stake_tortuga_only     | только стейк apt на tortuga
10: stake_ditto_only      | только стейк apt на ditto
11: send_aptos            | отправка apt токенов на указанные кошельки
'''

try:
    bot = telebot.TeleBot(tg_token, disable_web_page_preview=True, parse_mode='HTML')

    try:
        logger.debug(start_message)
        module = input("Start module: ")

        if module == "1":  # create_database
            Database.create_database()
        elif module == "2":  # default_warmup
            warmup(bot)
        elif module == "3":  # okx_gas_warmup
            warmup(bot, mode="gas")
        elif module == "4":  # low_bank_warmup
            warmup(bot, mode="low_bank")
        elif module == "5":  # collector
            collector(bot)
        elif module == "6":  # register_domain
            aptos_name(bot)
        elif module == "7":  # register_subdomain
            sub_aptos_name(bot)
        elif module == "8":  # claim_bridged_tokens
            claim_bridged_tokens(bot)
        elif module == "9":  # stake_tortuga_only
            stake(bot, "tortuga")
        elif module == "10":  # stake_ditto_only
            stake(bot, "ditto")
        elif module == "11":  # send_aptos
            withdraw_aptos(bot)
        else:
            logger.error(f"Invalid module number: {module}")

    except ValueError as e:
        if str(e) == "empty range for randrange()":
            text = "All accounts are finished"
            logger.success(text)
            send_msg(bot, f"🟢 {text}", disable_notification=False)

    except Exception as e:
        text = f"Module error: {str(e)}"
        logger.error(text)
        send_msg(bot, f"🔴 {text}", disable_notification=False)

except Exception as e:
    if "token" in str(e):
        logger.error("Invalid tg_token")
