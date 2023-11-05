import random

from loguru import logger

from config import (
    tokens_mapping,
    use_mobile_proxy,
    sleep_time,
    loss_ratio,
    send_ratio,
    sleep_time_wallets,
    names_txt_path,
    timestamps_txt_path
)
from models.account import Wallet
from models.database import Database
from modules.cex import gas_withdraw, low_bank_withdraw
from sdk.client import Client
from utils import (
    sleep,
    send_msg,
    change_mobile_ip,
    update_database_warmup,
    warmup_event,
    update_database_stake,
    get_signature_to_mint,
    get_available_name,
    update_database_aptosname,
    get_circle_swaps_count,
    data_item_swaps_count, read_from_txt
)


def warmup(bot, mode="default", collector_swaps_count=0, data_item_index=None, circle_swaps_count=0):
    database = Database.read_database()

    while len(database["data"]) != 0:
        try:
            logger.info(Database.get_database_tx_count(database["data"]))

            if data_item_index is None or circle_swaps_count == 0:
                if use_mobile_proxy:
                    change_mobile_ip()
                data_item, data_item_index = Database.get_random_data_item(database["data"])
                circle_swaps_count = get_circle_swaps_count()
                withdraw_circle = True
            else:
                data_item, data_item_index = Database.get_random_data_item(
                    database["data"],
                    data_item_index=data_item_index
                )
                withdraw_circle = False

            account = Wallet(data_item.private_key, data_item.proxy)

            logger.debug(f"Wallet: {account.address}")
            logger.debug(f"Proxy: {account.proxy}")

            if withdraw_circle:
                send_msg(bot, f"👛 Wallet address:\n{account.address}")

            client = Client(account, mode, bot)

            if mode == "gas":
                success = gas_withdraw(bot, account, client, mode="gas")
                warmup(bot, mode) if not success else None
            if mode == "low_bank" and withdraw_circle:
                success = gas_withdraw(bot, account, client, mode="low_bank")
                if not success:
                    text = f"Problem with cex withdraw while start new wallet in low bank warmup"
                    logger.error(text)
                    send_msg(bot, f"🔴 {text}")
                    exit()

            data_item, swaps_before_stake = warmup_event(data_item, client)
            swaps_count = data_item_swaps_count(data_item)
            collector_dexes = []

            if data_item.pancakeswap_swaps_count > 0:
                collector_dexes.append("pancakeswap")

            if data_item.liquidswap_swaps_count > 0:
                collector_dexes.append("liquidswap")

            if len(collector_dexes) == 0:
                collector_dex = "liquidswap"
            else:
                collector_dex = random.choice(collector_dexes)

            if mode == "default" or mode == "gas":
                sleep(sleep_time)
                logger.info("Back swap")

                try:
                    for token_name in tokens_mapping.keys():
                        balance = client.get_token_balance(token_name)
                        if balance > 0 and token_name != "apt":
                            if collector_dex == "pancakeswap":
                                pancakeswap_swaps_count = client.swap_pancakeswap(token_name, "apt", balance,
                                                                                  loss_ratio, 1)
                                if pancakeswap_swaps_count == 0:
                                    collector_swaps_count = 1
                                    circle_swaps_count -= 1
                                else:
                                    collector_swaps_count = 0
                            else:
                                liquidswap_swaps_count = client.swap_liquidswap(token_name, "apt", balance, loss_ratio,
                                                                                1)
                                if liquidswap_swaps_count == 0:
                                    collector_swaps_count = 1
                                    circle_swaps_count -= 1
                                else:
                                    collector_swaps_count = 0

                except Exception as e:
                    logger.error(f"Back swap with liquidswap error: {str(e)}")

            elif mode == "low_bank":
                if circle_swaps_count == 1 or swaps_count == 0:
                    sleep(sleep_time)
                    logger.info("Start collector")
                    send_msg(bot, "ℹ️ Start collector")

                    try:
                        for token_name in tokens_mapping.keys():
                            balance = client.get_token_balance(token_name)

                            if balance > 0 and token_name != "apt":
                                if collector_dex == "pancakeswap":
                                    pancakeswap_swaps_count = client.swap_pancakeswap(
                                        token_name,
                                        "apt",
                                        balance,
                                        loss_ratio,
                                        1
                                    )
                                    if pancakeswap_swaps_count == 0:
                                        collector_swaps_count += 1
                                        circle_swaps_count -= 1
                                else:
                                    liquidswap_swaps_count = client.swap_liquidswap(
                                        token_name,
                                        "apt",
                                        balance,
                                        loss_ratio,
                                        1
                                    )
                                    if liquidswap_swaps_count == 0:
                                        collector_swaps_count += 1
                                        circle_swaps_count -= 1

                                sleep(sleep_time)

                    except Exception as e:
                        logger.error(f"Swap for collector with liquidswap error: {str(e)}")

            try:
                data_item.liquidswap_swaps_count -= swaps_before_stake

                if collector_dex == "pancakeswap":
                    data_item.pancakeswap_swaps_count -= collector_swaps_count
                else:
                    data_item.liquidswap_swaps_count -= collector_swaps_count

                database, data_item_index = update_database_warmup(database, data_item, data_item_index)
                Database.save_database(database)
                circle_swaps_count -= 1
                logger.info(f"Database has been updated")

            except Exception as e:
                text = f"Database update error: {str(e)}"
                logger.error(text)
                send_msg(bot, f"🔴 {text}", disable_notification=False)

            if mode == "low_bank":
                if circle_swaps_count == 0 or data_item_index is None:
                    amount = client.get_token_balance("apt") * send_ratio
                    client.send_aptos(data_item.to_address, amount)
                    low_bank_withdraw(bot, amount)

            if circle_swaps_count == 0 or data_item_index is None:
                sleep(sleep_time_wallets)
            else:
                sleep(sleep_time)

        except Exception as e:
            if "empty range for randrange()" in str(e):
                text = "All accounts are finished"
                logger.success(text)
                send_msg(bot, f"🟢 {text}")
            else:
                text = f"Warmap \"{mode}\" mode: stopped with error: {str(e)}"
                logger.error(text)
                send_msg(bot, f"🔴 {text}", disable_notification=False)


def stake(bot, dex):
    try:
        if use_mobile_proxy:
            change_mobile_ip()

        database = Database.read_database()
        data_item, data_item_index = Database.get_random_data_item(database["data"])
        account = Wallet(data_item.private_key, data_item.proxy)

        logger.debug(f"Wallet: {account.address}")
        logger.debug(f"Proxy: {account.proxy}")
        send_msg(bot, f"Wallet address:\n{account.address}")

        client = Client(account, "default", bot)
        stakes_count = data_item.tortuga_stake_count if dex == "tortuga" else data_item.ditto_stake_count
        stakes_count, swaps_count = client.stake(dex, stakes_count=stakes_count)

        try:
            update_database_stake(
                database,
                dex,
                data_item.liquidswap_swaps_count,
                data_item_index,
                stakes_count,
                swaps_count
            )
            Database.save_database(database)
            logger.info(f"Database has been updated")
        except Exception as e:
            logger.error(f"Database update error: {str(e)}")

        sleep(sleep_time)
        stake(bot, dex)

    except Exception as e:
        if "empty range for randrange()" in str(e):
            text = "All accounts are finished"
            logger.success(text)
            send_msg(bot, f"🟢 {text}")
        else:
            text = f"Stake on {dex} error: {str(e)}"
            logger.error(text)
            send_msg(bot, f"🔴 {text}", disable_notification=False)


def collector(bot, swaps_count=0):
    try:
        if use_mobile_proxy:
            change_mobile_ip()

        database = Database.read_database()
        data_item, data_item_index = Database.get_random_data_item(database["data"])
        account = Wallet(data_item.private_key, data_item.proxy)

        logger.debug(f"Wallet: {account.address}")
        logger.debug(f"Proxy: {account.proxy}")
        send_msg(bot, f"Wallet address:\n{account.address}")

        client = Client(account, "default", bot)

        try:
            for token_name in tokens_mapping.keys():
                balance = client.get_token_balance(token_name)
                if balance > 0 and token_name != "apt":
                    client.swap_liquidswap(token_name, "apt", balance, loss_ratio, 1)
                    sleep(sleep_time)
                swaps_count += 1
        except Exception as e:
            logger.error(f"Swap for collector with liquidswap error: {str(e)}")

        try:
            if swaps_count == len(tokens_mapping):
                database["data"].pop(data_item_index)
                Database.save_database(database)
                logger.info(f"Database has been updated")
        except Exception as e:
            logger.error(f"Database update error: {str(e)}")

        sleep(sleep_time)
        collector(bot)

    except Exception as e:
        if "empty range for randrange()" in str(e):
            text = "All accounts are finished"
            logger.success(text)
            send_msg(bot, f"🟢 {text}")
        else:
            text = f"Collector error: {str(e)}"
            logger.error(text)
            send_msg(bot, f"🔴 {text}", disable_notification=False)


def aptos_name(bot):
    try:
        if use_mobile_proxy:
            change_mobile_ip()

        database = Database.read_database()
        data_item, data_item_index = Database.get_random_data_item(database["data"])
        account = Wallet(data_item.private_key, data_item.proxy)

        logger.debug(f"Wallet: {account.address}")
        logger.debug(f"Proxy: {account.proxy}")
        send_msg(bot, f"Wallet address:\n{account.address}")

        client = Client(account, "aptos_names", bot)

        success = gas_withdraw(bot, account, client, mode=client.mode)
        aptos_name(bot) if not success else None

        try:
            nickname = get_available_name(account.proxy)
            signature = get_signature_to_mint(account.address, nickname, account.proxy)

            if not signature:
                raise ValueError(f'problem with signature')

            client.register_domain(nickname, signature)

        except Exception as e:
            logger.error(f"Claim domain error: {str(e)}")

        try:
            database = update_database_aptosname(database, data_item, data_item_index)
            Database.save_database(database)
            logger.info(f"Database has been updated")
        except Exception as e:
            logger.error(f"Database update error: {str(e)}")

        sleep(sleep_time)
        aptos_name(bot)

    except Exception as e:
        if "empty range for randrange()" in str(e):
            text = "All accounts are finished"
            logger.success(text)
            send_msg(bot, f"🟢 {text}")
        else:
            text = f"Claim aptosname error: {str(e)}"
            logger.error(text)
            send_msg(bot, f"🔴 {text}", disable_notification=False)


def sub_aptos_name(bot):
    names = read_from_txt(names_txt_path)
    timestamps = read_from_txt(timestamps_txt_path)

    try:
        if use_mobile_proxy:
            change_mobile_ip()

        database = Database.read_database()
        data_item, data_item_index = Database.get_random_data_item(database["data"])
        account = Wallet(data_item.private_key, data_item.proxy)

        logger.debug(f"Wallet: {account.address}")
        logger.debug(f"Proxy: {account.proxy}")
        send_msg(bot, f"Wallet address:\n{account.address}")

        if len(names) < len(database["data"]):
            logger.error(f"Number of names does not match the number of private keys")
            exit()

        if len(timestamps) < len(database["data"]):
            logger.error(f"Number of timestamps does not match the number of private keys")
            exit()

        client = Client(account, "aptos_names", bot)
        unix_date = int(timestamps[data_item_index]) + 31470526
        timestamp_without_fractional = int(str(unix_date).split('.')[0])

        try:
            nickname = get_available_name(account.proxy)
            client.register_subdomain(names[data_item_index], nickname, timestamp_without_fractional)
        except Exception as e:
            logger.error(f"Claim domain error: {str(e)}")

        try:
            database = update_database_aptosname(database, data_item, data_item_index)
            Database.save_database(database)
            logger.info(f"Database has been updated")
        except Exception as e:
            logger.error(f"Database update error: {str(e)}")

        sleep(sleep_time)
        sub_aptos_name(bot)

    except Exception as e:
        if "empty range for randrange()" in str(e):
            text = "All accounts are finished"
            logger.success(text)
            send_msg(bot, f"🟢 {text}")
        else:
            text = f"Claim aptosname error: {str(e)}"
            logger.error(text)
            send_msg(bot, f"🔴 {text}", disable_notification=False)


def withdraw_aptos(bot):
    try:
        if use_mobile_proxy:
            change_mobile_ip()

        database = Database.read_database()
        data_item, data_item_index = Database.get_random_data_item(database["data"])
        account = Wallet(data_item.private_key, data_item.proxy)

        logger.debug(f"Wallet: {account.address}")
        logger.debug(f"Proxy: {account.proxy}")
        send_msg(bot, f"Wallet address:\n{account.address}")

        client = Client(account, "aptos_names", bot)

        amount = client.get_token_balance("apt") * send_ratio
        client.send_aptos(data_item.to_address, amount)

        try:
            database["data"].pop(data_item_index)
            Database.save_database(database)
            logger.info(f"Database has been updated")
        except Exception as e:
            logger.error(f"Database update error: {str(e)}")

        sleep(sleep_time)
        withdraw_aptos(bot)

    except Exception as e:
        if "empty range for randrange()" in str(e):
            text = "All accounts are finished"
            logger.success(text)
            send_msg(bot, f"🟢 {text}")
        else:
            text = f"Claim bridger tokens error: {str(e)}"
            logger.error(text)
            send_msg(bot, f"🔴 {text}", disable_notification=False)


def claim_bridged_tokens(bot):
    try:
        if use_mobile_proxy:
            change_mobile_ip()

        database = Database.read_database()
        data_item, data_item_index = Database.get_random_data_item(database["data"])
        account = Wallet(data_item.private_key, data_item.proxy)

        logger.debug(f"Wallet: {account.address}")
        logger.debug(f"Proxy: {account.proxy}")
        send_msg(bot, f"Wallet address:\n{account.address}")

        client = Client(account, "aptos_names", bot)
        client.claim_bridged_tokens(bot)

        try:
            database["data"].pop(data_item_index)
            Database.save_database(database)
            logger.info(f"Database has been updated")
        except Exception as e:
            logger.error(f"Database update error: {str(e)}")

        sleep(sleep_time)
        claim_bridged_tokens(bot)

    except Exception as e:
        if "empty range for randrange()" in str(e):
            text = "All accounts are finished"
            logger.success(text)
            send_msg(bot, f"🟢 {text}")
        else:
            text = f"Claim bridger tokens error: {str(e)}"
            logger.error(text)
            send_msg(bot, f"🔴 {text}", disable_notification=False)
