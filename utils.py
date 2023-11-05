import json
import random
import re
import time

import requests
from aptos_sdk import ed25519
from aptos_sdk.account import Account
from aptos_sdk.account_address import AccountAddress
from loguru import logger
from tqdm import tqdm

from config import (
    tokens_mapping,
    change_ip_url,
    min_gas_balance,
    swap_deviation,
    tg_ids,
    loss_ratio,
    tortuga_stake_deviation,
    ditto_stake_deviation,
    use_proxy,
    captcha_key,
    total_tries,
    send_ratio,
    circle_swaps_count, node_url
)
from models.swap_info import SwapInfo


def change_mobile_ip():
    try:
        requests.get(change_ip_url)
        logger.debug(f"Success change IP")
    except Exception as e:
        logger.error(f"Change ip error: {str(e)}")


def read_from_txt(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as file:
            return [line.strip() for line in file]
    except FileNotFoundError as e:
        logger.error(f"{str(e)} while try to open \"{file_path}\"")
    except Exception as e:
        logger.error(f"{str(e)} while open txt file: \"{file_path}\"")


def read_from_json(file_path):
    try:
        with open(file_path) as json_file:
            return json.load(json_file)
    except FileNotFoundError as e:
        logger.error(f"{str(e)} while try to open \"{file_path}\"")
    except Exception as e:
        logger.error(f"{str(e)} while open json file: \"{file_path}\"")


def write_to_json(file_path, data):
    try:
        with open(file_path, 'w') as json_file:
            json_file.write(data)
    except FileNotFoundError as e:
        logger.error(f"{str(e)} while try to open {file_path}")
    except Exception as e:
        logger.error(f"{str(e)} while write to json file: \"{file_path}\"")


def get_amount_to_stake(stake_deviation):
    try:
        return round(random.uniform(*stake_deviation), 5)
    except Exception as e:
        logger.error(f"Get amount to stake error: {str(e)}")


def get_amount_to_withdraw(withdraw_deviation):
    try:
        return round(random.uniform(*withdraw_deviation), 3)
    except Exception as e:
        logger.error(f"Get amount to withdraw error: {str(e)}")


def get_percentage_tokens_for_swap():
    try:
        return random.uniform(*swap_deviation)
    except Exception as e:
        logger.error(f"Get percentage for swap error: {str(e)}")


def get_explorer_hash_link(tx_hash: str):
    try:
        return f"https://explorer.aptoslabs.com/txn/{tx_hash}?network=mainnet"
    except Exception as e:
        logger.error(f"Get explorer hash link error: {str(e)}")


def get_client_account(private_key: str):
    try:
        private_key = ed25519.PrivateKey.from_hex(private_key)
        return Account(
            account_address=AccountAddress.from_key(private_key.public_key()),
            private_key=private_key
        )
    except Exception as e:
        logger.error(f"Get client account error: {str(e)}")


def get_to_token_name_for_swap(from_token: str):
    try:
        tokens = (list(tokens_mapping))
        tokens.remove(from_token)
        to_token = str(random.choice(tokens))
        return to_token
    except Exception as e:
        logger.error(f"Get to_token name for swap error: {str(e)}")


def send_msg(bot, text, disable_notification=True):
    for tg_id in tg_ids:
        try:
            bot.send_message(tg_id, text, disable_notification=disable_notification)
        except Exception as error:
            logger.error(f'Telegram send error: {error}')


def sleep(sleep_time: list):
    try:
        for _ in tqdm(range(random.randint(*sleep_time)), colour="green"):
            time.sleep(1)
    except Exception as e:
        logger.error(f"Sleep error: {str(e)}")


def get_dex(data_item):
    dexs = []
    if data_item.pancakeswap_swaps_count > 0:
        dexs.append("pancakeswap")
    if data_item.liquidswap_swaps_count > 0:
        dexs.append("liquidswap")
    if data_item.tortuga_stake_count > 0:
        dexs.append("tortuga")
    if data_item.ditto_stake_count > 0:
        dexs.append("ditto")

    return random.choice(dexs)


def get_amount_for_swap(from_token_name, from_token_balance, percentage_tokens_for_swap, mode):
    if from_token_name == "apt" and mode == "gas":
        return (from_token_balance - min_gas_balance) * percentage_tokens_for_swap
    else:
        return from_token_balance * percentage_tokens_for_swap


def update_database_warmup(database, data_item, index):
    if data_item.liquidswap_swaps_count < 0:
        data_item.liquidswap_swaps_count = 0

    if data_item.pancakeswap_swaps_count < 0:
        data_item.pancakeswap_swaps_count = 0

    all_events_count = (
            data_item.pancakeswap_swaps_count +
            data_item.liquidswap_swaps_count +
            data_item.tortuga_stake_count +
            data_item.ditto_stake_count
    )

    if all_events_count <= 0:
        database["data"].pop(index)
        return database, None
    else:
        database["data"][index]["liquidswap_swaps_count"] = data_item.liquidswap_swaps_count
        database["data"][index]["pancakeswap_swaps_count"] = data_item.pancakeswap_swaps_count
        database["data"][index]["tortuga_stake_count"] = data_item.tortuga_stake_count
        database["data"][index]["ditto_stake_count"] = data_item.ditto_stake_count

    return database, index


def update_database_stake(database, dex, liquidswap_swaps_count, index, stakes_count, swaps_count):
    try:
        if stakes_count < 1:
            database["data"].pop(index)
        else:
            database["data"][index][f"{dex}_stake_count"] = stakes_count
            database["data"][index]["liquidswap_swaps_count"] = liquidswap_swaps_count - swaps_count

    except Exception as e:
        logger.error(f"Database update error: {str(e)}")

    return database


def update_database_aptosname(database, data_item, index):
    data_item.sub_aptos_names_count -= 1
    if data_item.sub_aptos_names_count < 1:
        database["data"].pop(index)
    return database


def warmup_event(data_item, client):
    swaps_before_stake = 0
    swap_info = get_swap_info(data_item, client)
    dex = swap_info.dex

    try:
        if swap_info.dex == "liquidswap":
            data_item.liquidswap_swaps_count = client.swap_liquidswap(
                swap_info.from_token_name,
                swap_info.to_token_name,
                swap_info.amount,
                loss_ratio,
                data_item.liquidswap_swaps_count
            )

        if swap_info.dex == "pancakeswap":
            data_item.pancakeswap_swaps_count = client.swap_pancakeswap(
                swap_info.from_token_name,
                swap_info.to_token_name,
                swap_info.amount,
                loss_ratio,
                data_item.pancakeswap_swaps_count
            )

        if swap_info.dex == "tortuga":
            data_item.tortuga_stake_count, swaps_before_stake = client.stake(dex)

        if swap_info.dex == "ditto":
            data_item.ditto_stake_count, swaps_before_stake = client.stake(dex)

    except Exception as e:
        logger.error(f"Event with {swap_info.dex} error: {str(e)}")

    return data_item, swaps_before_stake


def data_item_swaps_count(data_item):
    swaps_count = data_item.pancakeswap_swaps_count + \
                  data_item.tortuga_stake_count + \
                  data_item.ditto_stake_count + \
                  data_item.liquidswap_swaps_count

    return swaps_count


def get_swap_info(data_item, client):
    dex = get_dex(data_item)
    percentage_tokens_for_swap = get_percentage_tokens_for_swap()
    from_token_name = client.get_max_balance_token_name()
    from_token_balance = client.get_token_balance(from_token_name)
    to_token_name = get_to_token_name_for_swap(from_token_name)
    amount = get_amount_for_swap(from_token_name, from_token_balance, percentage_tokens_for_swap, client.mode)

    logger.info(f"Dex: {dex}")
    logger.info(f"Percentage tokens for swap: {percentage_tokens_for_swap}")

    return SwapInfo(
        dex,
        percentage_tokens_for_swap,
        from_token_name,
        from_token_balance,
        to_token_name,
        amount
    )


def liquidswap_exception(bot, swaps_count, from_token_name, to_token_name, error, proxy):
    if "ERR_COIN_OUT_NUM_LESS_THAN_EXPECTED_MINIMUM" in error:
        logger.warning(f"High loss coefficient while swap from {from_token_name} to {to_token_name}")
    elif "EINSUFFICIENT_BALANCE" in error:
        text = "Problem with rpc connection, last swap was success"
        logger.warning(text)
        send_msg(bot, f"🟢 {text}")
        return swaps_count - 1
    elif "list index out of range" in error:
        text = "Problem with simulate tx"
        logger.warning(text)
        send_msg(bot, f"🟡 {text}", disable_notification=False)
    elif "hash" in error:
        hash_pattern = r'"hash":"(0x[a-fA-F0-9]+)"'
        tx_hash = re.search(hash_pattern, error)
        if proxy is None:
            response = requests.get(f"{node_url}/transactions/by_hash/{tx_hash}")
        else:
            response = requests.get(
                f"{node_url}/transactions/by_hash/{tx_hash}",
                proxies={"https": f"http://{proxy}"}
            )
        if "success" in response.json():
            text = f"Success swap {from_token_name} in {to_token_name}\n{get_explorer_hash_link(tx_hash)}"
            logger.success(text)
            send_msg(bot, f"🟢 {text}")
            return swaps_count - 1
        else:
            text = f"Swap from {from_token_name} to {to_token_name} error: {error}"
            logger.error(text)
            send_msg(bot, f"🔴 {text}", disable_notification=False)
    else:
        text = f"Swap from {from_token_name} to {to_token_name} error: {error}"
        logger.error(text)
        send_msg(bot, f"🔴 {text}", disable_notification=False)

    return swaps_count


def pancakeswap_exception(bot, from_token_name, to_token_name, error, proxy):
    if "ERR_COIN_OUT_NUM_LESS_THAN_EXPECTED_MINIMUM" in error:
        logger.warning(f"High loss coefficient while swap from {from_token_name} to {to_token_name}")
    elif "EINSUFFICIENT_BALANCE" in error:
        text = "Problem with rpc connection, last swap was success"
        logger.warning(text)
        send_msg(bot, f"🟢 {text}")
    elif "list index out of range" in error:
        text = "Problem with simulate tx"
        logger.warning(text)
        send_msg(bot, f"🟡 {text}", disable_notification=False)
        return 1
    elif "hash" in error:
        hash_pattern = r'"hash":"(0x[a-fA-F0-9]+)"'
        tx_hash = re.search(hash_pattern, error)
        if proxy is None:
            response = requests.get(f"{node_url}/transactions/by_hash/{tx_hash}")
        else:
            response = requests.get(
                f"{node_url}/transactions/by_hash/{tx_hash}",
                proxies={"https": f"http://{proxy}"}
            )
        if "success" in response.json():
            text = f"Success swap {from_token_name} in {to_token_name}\n{get_explorer_hash_link(tx_hash)}"
            logger.success(text)
            send_msg(bot, f"🟢 {text}")
        else:
            text = f"Swap from {from_token_name} to {to_token_name} error: {error}"
            logger.error(text)
            send_msg(bot, f"🔴 {text}", disable_notification=False)
    else:
        text = f"Swap from {from_token_name} to {to_token_name} error: {error}"
        logger.error(text)
        send_msg(bot, f"🔴 {text}", disable_notification=False)

    return total_tries


def stake_exception(bot, max_gas_amount, amount_in, error, proxy):
    try:
        if "Out of gas" in error:
            max_gas_amount += random.randint(4000, 6000)
            logger.warning("Gas less than minimum, try with more gas")
        elif "hash" in error:
            hash_pattern = r'"hash":"(0x[a-fA-F0-9]+)"'
            tx_hash = re.search(hash_pattern, error)
            if proxy is None:
                response = requests.get(f"{node_url}/transactions/by_hash/{tx_hash}")
            else:
                response = requests.get(
                    f"{node_url}/transactions/by_hash/{tx_hash}",
                    proxies={"https": f"http://{proxy}"}
                )
            if "success" in response.json():
                text = f"Success stake {amount_in} apt\n{get_explorer_hash_link(tx_hash)}"
                logger.success(text)
                send_msg(bot, f"🟢 {text}")
        else:
            logger.error(f"Error stake {amount_in}: {error}")

        return max_gas_amount
    except Exception as e:
        logger.error(f"Stake exception error: {str(e)}")


def send_aptos_exception(bot, to_address, amount, error, proxy):
    if "EINSUFFICIENT_BALANCE" in error:
        text = f"Send {amount} aptos to address {to_address} error: not enough balance"
        logger.error(text)
        send_msg(bot, f"🔴 {text}", disable_notification=False)
    elif "hash" in error:
        hash_pattern = r'"hash":"(0x[a-fA-F0-9]+)"'
        tx_hash = re.search(hash_pattern, error)
        if proxy is None:
            response = requests.get(f"{node_url}/transactions/by_hash/{tx_hash}")
        else:
            response = requests.get(
                f"{node_url}/transactions/by_hash/{tx_hash}",
                proxies={"https": f"http://{proxy}"}
            )
        if "success" in response.json():
            text = f"Success stake {amount} apt\n{get_explorer_hash_link(tx_hash)}"
            logger.success(text)
            send_msg(bot, f"🟢 {text}")
    else:
        text = f"Send {amount} aptos to address {to_address} error: {error}"
        logger.error(text)
        send_msg(bot, f"🔴 {text}", disable_notification=False)


def get_stake_amount_in(dex, max_gas_amount):
    try:
        if dex == "tortuga":
            max_gas_amount += random.randint(8000, 10000)
            amount_in = get_amount_to_stake(tortuga_stake_deviation)
        else:
            amount_in = get_amount_to_stake(ditto_stake_deviation)

        return amount_in, max_gas_amount
    except Exception as e:
        logger.error(f"Get stake amount in error: {str(e)}")


def get_send_aptos_amount(amount):
    try:
        return round(amount * send_ratio)
    except Exception as e:
        logger.error(f"Get amount to stake error: {str(e)}")


def get_circle_swaps_count():
    try:
        return random.randint(*circle_swaps_count)
    except Exception as e:
        logger.error(f"Get circle swaps count error: {str(e)}")


def get_random_usernames():
    url = 'https://spinxo.com/services/NameService.asmx/GetNames'
    payload = {
        "snr": {
            "category": 0,
            "UserName": "",
            "Hobbies": "",
            "ThingsILike": "",
            "Numbers": "",
            "WhatAreYouLike": "",
            "Words": "",
            "Stub": "username",
            "LanguageCode": "en",
            "NamesLanguageID": "45",
            "Rhyming": False,
            "OneWord": False,
            "UseExactWords": False,
            "ScreenNameStyleString": "Any",
            "GenderAny": False,
            "GenderMale": False,
            "GenderFemale": False
        }
    }
    r = requests.post(url, json=payload)
    names = r.json()['d']['Names']
    return names


def get_available_name(proxy):
    names = get_random_usernames()
    while True:
        if len(names) == 0:
            return get_available_name(proxy)

        name = names.pop(random.randint(0, len(names) - 1)).lower()

        if len(name) < 6:
            continue

        url = f'https://www.aptosnames.com/api/mainnet/v1/address/{name}'

        if use_proxy:
            r = requests.get(url, proxies={"https": f"http://{proxy}"})
        else:
            r = requests.get(url)
        if r.text == "{}":
            return name


def get_sequence_number(address, proxy):
    url = f'https://mainnet.aptoslabs.com/v1/accounts/{address}'
    if use_proxy:
        r = requests.get(url, proxies={"https": f"http://{proxy}"})
    else:
        r = requests.get(url)
    return r.json()['sequence_number']


def captcha_solver():
    logger.debug(f'Solving captcha by recaptcha')

    url = f'http://rucaptcha.com/in.php?' \
          f'key={captcha_key}&' \
          f'method=userrecaptcha&' \
          f'googlekey=6LdSUooiAAAAAMdpPgeiWzuTmCK2wzuswCrnWWku&' \
          f'pageurl=https://www.aptosnames.com&' \
          f'json=1'
    r = requests.get(url)

    if r.json().get('status') == 1:
        request_id = r.json()['request']
    else:
        logger.error(f'captcha error: {r.json()}')
        return False

    while True:
        url = f'http://rucaptcha.com/res.php?' \
              f'key={captcha_key}&' \
              f'action=get&' \
              f'id={request_id}&' \
              f'json=1'
        r = requests.get(url)
        if r.json()['status'] == 1:
            return r.json()['request']

        time.sleep(10)


def get_signature_to_mint(address, name, proxy):
    captcha_response = captcha_solver()
    if not captcha_response:
        return False
    nonce = get_sequence_number(address, proxy)

    url = 'https://www.aptosnames.com/api/mainnet/v1/verify'
    payload = {
        "recaptchaToken": captcha_response,
        "registerDomainProofChallenge": {
            "sequenceNumber": nonce,
            "registerAddress": address,
            "domainName": name
        }
    }
    if use_proxy:
        r = requests.post(url, json=payload, proxies={"https": f"http://{proxy}"})
    else:
        r = requests.post(url, json=payload)
    return r.json()['signedMessage']['hexString']
