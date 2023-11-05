import json
import random
from typing import Union

from loguru import logger

from config import (
    wallets_txt_path,
    proxys_txt_path,
    use_proxy,
    pancakeswap_swap_count,
    liquidswap_swap_count,
    tortuga_stake_count,
    ditto_stake_count,
    database_path,
    aptos_names_count,
    sub_aptos_names_count,
    addresses_txt_path, use_mobile_proxy
)
from models.account import Wallet
from models.data_item import DataItem
from utils import read_from_txt


class Database:
    def __init__(self, data):
        self.data = data

    def to_json(self):
        try:
            return json.dumps(self, default=lambda o: o.__dict__, indent=4)
        except Exception as e:
            logger.error(f"Database to json object error: {str(e)}")

    @staticmethod
    def get_random_data_item(data, data_item_index=None) -> Union[DataItem, int]:
        try:
            data_len = len(data)
            index = random.randint(0, data_len - 1) if data_item_index is None else data_item_index

            data_item = data[index]
            if data_len > 0:
                wallet = Wallet(data_item["private_key"], data_item["proxy"])
                data_item_object = DataItem(
                    wallet,
                    data_item["pancakeswap_swaps_count"],
                    data_item["liquidswap_swaps_count"],
                    data_item["tortuga_stake_count"],
                    data_item["ditto_stake_count"],
                    data_item["aptos_names_count"],
                    data_item["sub_aptos_names_count"],
                    data_item["to_address"]
                )
                return data_item_object, index
            else:
                logger.warning(f"Data item length is {data_len}. Reason 1: all jobs are completed. "
                               f"Reason 2: some problems with data from database")
                exit()
        except Exception as e:
            if "empty range for randrange() (0, 0, 0)" in str(e):
                text = "All accounts are finished"
                logger.success(text)
                exit()
            else:
                logger.error(f"Get random data item from database error: {str(e)}")

    @staticmethod
    def create_database() -> None:
        try:
            data = []
            wallets = read_from_txt(wallets_txt_path)
            proxys = read_from_txt(proxys_txt_path)
            addresses = read_from_txt(addresses_txt_path)

            if use_mobile_proxy:
                if len(wallets) != len(proxys) and len(proxys):
                    proxys[0] *= len(wallets)

            try:
                for wallet in wallets:
                    wallet_index = wallets.index(wallet)
                    proxy = proxys[wallet_index] if use_proxy else None
                    to_address = addresses[wallet_index] if len(addresses) == len(wallets) else None
                    account = Wallet(wallet, proxy)
                    data_item = DataItem(
                        account,
                        pancakeswap_swap_count,
                        liquidswap_swap_count,
                        tortuga_stake_count,
                        ditto_stake_count,
                        aptos_names_count,
                        sub_aptos_names_count,
                        to_address
                    )
                    data.append(data_item)

            except IndexError as e:
                logger.error(f"Problems with the proxy when creating a database: {str(e)}")
            except Exception as e:
                logger.error(f"Problems with data items while crate database: {str(e)}")

            Database.save_database(Database(data).to_json())
            logger.success(f"Database was been created")

        except Exception as e:
            logger.error(f"Database creation error: {str(e)}")

    @staticmethod
    def read_database():
        try:
            with open(database_path) as json_file:
                return json.load(json_file)
        except FileNotFoundError as e:
            logger.error(f"{str(e)} while try to open \"{database_path}\"")
        except Exception as e:
            logger.error(f"{str(e)} while open json file: \"{database_path}\"")

    @staticmethod
    def save_database(database) -> None:
        if type(database) is dict:
            database = json.dumps(database, indent=4)
        try:
            with open(database_path, 'w') as json_file:
                json_file.write(database)
        except FileNotFoundError as e:
            logger.error(f"{str(e)} while try to open {database_path}")
        except Exception as e:
            logger.error(f"{str(e)} while write to json file: \"{database_path}\"")

    @staticmethod
    def get_data_item_tx_count(data_item: DataItem):
        total_tx_count = sum([
            data_item.liquidswap_swaps_count,
            data_item.pancakeswap_swaps_count,
            data_item.ditto_stake_count,
            data_item.tortuga_stake_count
        ])

        return total_tx_count

    @staticmethod
    def get_database_tx_count(data):
        tx_count = 0

        for item in data:
            if isinstance(item, dict):
                for key, value in item.items():
                    if key.endswith("_count"):
                        tx_count += value

        return tx_count
