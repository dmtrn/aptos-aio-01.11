import time

from ccxt import okx
from loguru import logger

from config import (
    use_proxy_okx,
    api_key,
    secret,
    password,
    total_tries,
    cex_sleep_time,
    gas_withdraw_deviation,
    min_gas_balance,
    withdraw_for_names,
    okx_sub_creds,
    low_bank_total_tries,
    withdraw_for_low_bank
)
from utils import sleep, send_msg, get_amount_to_withdraw


def okx_gas_withdraw(
        to_address: str,
        proxy: str,
        bot,
        retry=0,
        amount_to_withdraw=0
) -> None:
    if not use_proxy_okx or proxy is None:
        exchange = okx({
            'apiKey': api_key,
            'secret': secret,
            'password': password,
            'enableRateLimit': True,
        })
    else:
        exchange = okx({
            'apiKey': api_key,
            'secret': secret,
            'password': password,
            'enableRateLimit': True,
            'proxies': {"https": f"http://{proxy}"},
        })

    try:
        exchange.withdraw(
            "APT",
            amount_to_withdraw,
            to_address,
            params={
                "toAddress": to_address,
                "chainName": "APT-Aptos",
                "dest": 4,
                "fee": 0.001,
                "pwd": '-',
                "amt": amount_to_withdraw,
                "network": "Aptos"
            })

        text = f"[OKX] withdraw {amount_to_withdraw} APT"
        logger.success(text)
        send_msg(bot, f"🟢 {text}")

    except Exception as e:
        text = f"[OKX] withdraw {amount_to_withdraw} APT error: {str(e)}"
        logger.error(text)
        send_msg(bot, f"🔴 {text}", disable_notification=False)

        if retry < total_tries:
            sleep(cex_sleep_time)
            okx_gas_withdraw(to_address, proxy, bot, retry=retry + 1)
        else:
            raise logger.warning("Skip this wallet at this time")


# todo: добавить прокси к OKX
def withdraw_from_sub_account(bot, creds, from_uid: str, symbol: str) -> None:
    try:
        exchange = okx(creds)
        try:
            amount = exchange.fetch_balance(params={'type': 'funding'})['total'][symbol]
            logger.info(f"Sub account with uid: {from_uid} balance {amount} {symbol}")
        except:
            return

        if amount == "0":
            return

        exchange.load_markets()
        currency = exchange.currency(symbol)
        request = {
            'ccy': currency['id'],
            'amt': exchange.currency_to_precision(symbol, amount),
            'from': '6',
            'to': '6',
            'type': '3',
            'subAcct': from_uid,
        }

        exchange.private_post_asset_transfer(request)
        logger.info(f"Withdraw {symbol} from sub account with uid: '{from_uid}' to main account successful")
        time.sleep(5)

    except Exception as e:
        text = f"Withdraw {symbol} from {from_uid} to main account error: {str(e)}"
        logger.error(text)
        send_msg(bot, f"🔴 {text}", disable_notification=False)


def low_bank_withdraw(bot, amount_to_withdraw):
    try:
        amount = 0.0
        symbol = "APT"

        exchange = okx({
            'apiKey': api_key,
            'secret': secret,
            'password': password,
        })

        while amount <= amount_to_withdraw:
            for account_data in okx_sub_creds.items():
                uid, okx_creds = account_data
                withdraw_from_sub_account(bot, okx_creds, uid, symbol)

            amount = exchange.fetch_balance(params={'type': 'funding'})['total'][symbol]

    except Exception as e:
        text = f"Low bank withdraw error: {str(e)}"
        logger.error(text)
        send_msg(bot, f"🔴 {text}", disable_notification=False)
        return False


def gas_withdraw(bot, account, client, mode="gas") -> bool:
    try:
        if mode == "aptos_names":
            gas_balance = client.get_token_balance("apt")
            if gas_balance < 1.002:
                logger.info("Try to withdraw APT from OKX")
                okx_gas_withdraw(
                    account.address,
                    account.proxy,
                    bot,
                    amount_to_withdraw=get_amount_to_withdraw(withdraw_for_names)
                )
                client.okx_withdraw_checker(tries=total_tries)
        elif mode == "low_bank":
            logger.info("Try to withdraw APT from OKX")
            amount_to_withdraw = get_amount_to_withdraw(withdraw_for_low_bank)
            low_bank_withdraw(bot, amount_to_withdraw)
            okx_gas_withdraw(
                account.address,
                account.proxy,
                bot,
                amount_to_withdraw=amount_to_withdraw
            )
            client.okx_withdraw_checker(tries=low_bank_total_tries)
        else:
            gas_balance = client.get_token_balance("apt")
            if gas_balance < min_gas_balance:
                logger.info("Try to withdraw APT from OKX")
                okx_gas_withdraw(
                    account.address,
                    account.proxy,
                    bot,
                    amount_to_withdraw=get_amount_to_withdraw(gas_withdraw_deviation)
                )
                client.okx_withdraw_checker(tries=total_tries)

        return True

    except Exception as e:
        text = f"Gas withdraw in warmup module error: {str(e)}"
        logger.error(text)
        send_msg(bot, f"🔴 {text}", disable_notification=False)
        return False
