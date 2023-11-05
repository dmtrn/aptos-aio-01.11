import random
import re
import time
from typing import Union, Any, Dict

from aptos_sdk import ed25519
from aptos_sdk.account import Account
from aptos_sdk.account_address import AccountAddress
from aptos_sdk.authenticator import Authenticator, Ed25519Authenticator
from aptos_sdk.bcs import Serializer
from aptos_sdk.client import RestClient, ResourceNotFound, ApiError
from aptos_sdk.transactions import (
    EntryFunction,
    TransactionPayload,
    TransactionArgument,
    SignedTransaction,
    RawTransaction
)
from aptos_sdk.type_tag import TypeTag, StructTag
from loguru import logger

from config import (
    tokens_mapping,
    node_url,
    total_tries,
    min_gas_balance,
    loss_ratio,
    loss_ratio_changer,
    sleep_time,
    cex_sleep_time,
    claimable_token
)
from models.account import Wallet
from sdk.constants import coin, network_modules, curve_uncorrelated
from utils import (
    get_explorer_hash_link,
    sleep,
    send_msg,
    stake_exception,
    get_stake_amount_in,
    send_aptos_exception,
    liquidswap_exception,
    pancakeswap_exception
)


class Client(RestClient):
    def __init__(
            self,
            account: Wallet,
            mode: str,
            bot
    ):
        super().__init__(node_url)
        self.signer = Account.load_key(account.private_key)
        self.proxy = account.proxy
        self.mode = mode
        self.bot = bot
        self.client_config.max_gas_amount = random.randint(4500, 5500)

    def get_coin_data(self, token: str) -> Union[dict, None]:
        try:
            coin_store_address = f"{coin['store']}<{tokens_mapping.get(token)}>"
            coin_data = self.account_resource(
                self.signer.address(), coin_store_address)
            return coin_data.get("data", {}).get("coin", {}).get("value")
        except:
            try:
                self.register(token)
            except Exception as e:
                logger.error(f"Get coin data error: {str(e)}")

    def get_decimals(self, token: str) -> int:
        try:
            token_address = AccountAddress.from_hex(
                tokens_mapping[token].split("::")[0])
            coin_info = self.account_resource(
                token_address, f"{coin['info']}<{tokens_mapping[token]}>")
            return coin_info["data"]["decimals"]
        except Exception as e:
            logger.error(f"Get coin info error: {str(e)}")
            return 0

    def get_token_balance(self, token_name: str, **kwargs) -> float:
        coin_data = self.get_coin_data(token_name)
        if coin_data is not None:
            return self.wei_to_float(int(coin_data), token_name)
        else:
            return 0

    def float_to_wei(self, amount: float, token: str) -> int:
        try:
            coin_info = self.get_decimals(token)
            return int(amount * 10 ** coin_info)
        except Exception as e:
            logger.error(f"Error while get wei from float: {str(e)}")

    def wei_to_float(self, amount: int, token_name: str) -> float:
        try:
            coin_info = self.get_decimals(token_name)
            return float(amount / 10 ** coin_info)
        except Exception as e:
            logger.error(f"Error while get float from wei: {str(e)}")

    def get_max_balance_token_name(self) -> Union[str, float]:
        try:
            max_balance = 0.0
            max_balance_token_name = ""

            for token_name in tokens_mapping.keys():
                token_balance = self.get_token_balance(token_name)

                if token_name != "apt":
                    balance_in_apt = self.get_token_balance_in_apt(token_balance, token_name)
                else:
                    balance_in_apt = token_balance

                if balance_in_apt > max_balance:
                    max_balance = balance_in_apt
                    max_balance_token_name = token_name

                logger.info(f"{round(token_balance, 5)} {token_name} is {round(balance_in_apt, 5)} apt")

            logger.info(f"Token with max balance: {max_balance_token_name}")
            return max_balance_token_name
        except Exception as e:
            logger.error(f"Get max balance token error: {str(e)}")

    def get_token_balance_in_apt(self, amount_in, from_token_name):
        try:
            to_token_name = "apt"
            dex = "liquidswap"
            from_token = tokens_mapping[from_token_name]
            to_token = tokens_mapping[to_token_name]

            resource_type_account = network_modules[dex]["resource_type"]
            resource_account = AccountAddress.from_hex(network_modules[dex]["resource_account"])

            try:
                resource_type = f"{resource_type_account}<{from_token}, {to_token}, {curve_uncorrelated}>"
                data = self.account_resource(
                    resource_account, resource_type)["data"]
                coin_x_reserve_value = int(data["coin_x_reserve"]["value"])
                coin_y_reserve_value = int(data["coin_y_reserve"]["value"])
            except:
                resource_type = f"{resource_type_account}<{to_token}, {from_token}, {curve_uncorrelated}>"
                data = self.account_resource(
                    resource_account, resource_type)["data"]
                coin_y_reserve_value = int(data["coin_x_reserve"]["value"])
                coin_x_reserve_value = int(data["coin_y_reserve"]["value"])

            reserve_x = self.wei_to_float(coin_x_reserve_value, from_token_name)
            reserve_y = self.wei_to_float(coin_y_reserve_value, to_token_name)

            return amount_in * reserve_y / reserve_x

        except IndexError as e:
            logger.error(f"Simulation tx to get token balance in apt error: {str(e)}")
        except Exception as e:
            logger.error(f"Can't get token balance in apt: {str(e)}")

    def get_resource_type(self, dex, resource_type_account, token_x, token_y):
        if dex == "pancakeswap":
            return f"{resource_type_account}<{tokens_mapping[token_x]}, {tokens_mapping[token_y]}>"
        if dex == "liquidswap":
            return f"{resource_type_account}<{tokens_mapping[token_x]}, {tokens_mapping[token_y]}, {curve_uncorrelated}>"

    def get_tokens_reserves(self, token_x: str, token_y: str, dex: str) -> Union[int, int]:
        try:
            resource_type = self.get_resource_type(
                dex,
                network_modules[dex]["resource_type"],
                token_x,
                token_y
            )
            resource_account = network_modules[dex]["resource_account"]

            data = self.account_resource(
                AccountAddress.from_hex(resource_account),
                resource_type
            )["data"]
            return int(data["coin_x_reserve"]["value"]), int(data["coin_y_reserve"]["value"])

        except:
            resource_type = self.get_resource_type(
                dex,
                network_modules[dex]["resource_type"],
                token_y,
                token_x
            )
            resource_account = network_modules[dex]["resource_account"]

            data = self.account_resource(
                AccountAddress.from_hex(resource_account),
                resource_type
            )["data"]
            return int(data["coin_y_reserve"]["value"]), int(data["coin_x_reserve"]["value"])

    def register(self, token: str) -> None:
        try:
            payload = EntryFunction.natural(
                "0x1::managed_coin",
                "register",
                [TypeTag(StructTag.from_str(tokens_mapping[token]))],
                [],
            )
            signed_transaction = self.create_bcs_signed_transaction(self.signer, TransactionPayload(payload))
            tx = self.submit_bcs_transaction(signed_transaction)
            self.wait_for_transaction(tx)

            logger.success(f"Token \"{token}\" is registered: {get_explorer_hash_link(tx)}")
            sleep(sleep_time)

        except Exception as e:
            if "account_not_found" in str(e):
                if self.mode == "default":
                    text = f"Stop default warmup: don't use this mode for wallets without gas"
                    logger.error(text)
                    send_msg(self.bot, f"🔴 {text}")
                    exit()

                if self.mode == "gas":
                    logger.warning("Account wasn't activated, send gas to activate this account")
            else:
                logger.error(f"Register token error: {str(e)}")

    def get_type_args(self, dex: str, from_token, to_token) -> list[TypeTag]:
        try:
            type_args = [
                TypeTag(StructTag.from_str(tokens_mapping[from_token])),
                TypeTag(StructTag.from_str(tokens_mapping[to_token]))
            ]
            if dex == "liquidswap":
                type_args.append(TypeTag(StructTag.from_str(curve_uncorrelated)))

            return type_args

        except Exception as e:
            logger.error(f"Get type args error for {dex}: {str(e)}")

    def okx_withdraw_checker(self, retry=0, tries=total_tries) -> None:
        sleep(cex_sleep_time)
        gas_balance = self.get_token_balance("apt")
        if gas_balance < min_gas_balance:
            logger.info("Wait gas from CEX")
            if retry < tries:
                self.okx_withdraw_checker(retry + 1)
            else:
                raise logger.warning("Skip this wallet at this time")

    def swap_liquidswap(
            self,
            from_token_name: str,
            to_token_name: str,
            amount_in: float,
            local_loss_ratio: float,
            liquidswap_swaps_count: int,
            retry=0
    ) -> int:
        start_amount_in = amount_in

        try:
            from_token = tokens_mapping[from_token_name]
            to_token = tokens_mapping[to_token_name]
            resource_type_account = network_modules["liquidswap"]["resource_type"]
            resource_account = AccountAddress.from_hex(network_modules["liquidswap"]["resource_account"])

            try:
                resource_type = f"{resource_type_account}<{from_token}, {to_token}, {curve_uncorrelated}>"
                data = self.account_resource(resource_account, resource_type)["data"]
                coin_x_reserve_value = int(data["coin_x_reserve"]["value"])
                coin_y_reserve_value = int(data["coin_y_reserve"]["value"])

            except:
                resource_type = f"{resource_type_account}<{to_token}, {from_token}, {curve_uncorrelated}>"
                data = self.account_resource(resource_account, resource_type)["data"]
                coin_y_reserve_value = int(data["coin_x_reserve"]["value"])
                coin_x_reserve_value = int(data["coin_y_reserve"]["value"])

            reserve_x = self.wei_to_float(coin_x_reserve_value, from_token_name)
            reserve_y = self.wei_to_float(coin_y_reserve_value, to_token_name)
            amount_out = self.float_to_wei(amount_in * reserve_y / reserve_x * local_loss_ratio, to_token_name)
            amount_in = self.float_to_wei(amount_in, from_token_name)

            payload = EntryFunction.natural(
                network_modules["liquidswap"]["script"],
                network_modules["liquidswap"]["function"],
                self.get_type_args("liquidswap", from_token_name, to_token_name),
                [
                    TransactionArgument(amount_in, Serializer.u64),
                    TransactionArgument(amount_out, Serializer.u64),
                ],
            )

            signed_transaction = self.create_bcs_signed_transaction(self.signer, TransactionPayload(payload))
            tx = self.submit_bcs_transaction(signed_transaction)
            self.wait_for_transaction(tx)

            text = f"Success liquidswap swap {self.wei_to_float(amount_in, from_token_name)} " \
                   f"{from_token_name} in {to_token_name}\n{get_explorer_hash_link(tx)}"
            logger.success(text)
            send_msg(self.bot, f"🟢 {text}")

            return liquidswap_swaps_count - 1

        except Exception as e:
            swaps_count = liquidswap_exception(
                self.bot,
                liquidswap_swaps_count,
                from_token_name,
                to_token_name,
                str(e),
                self.proxy
            )

            if swaps_count < liquidswap_swaps_count:
                return swaps_count

            if retry < total_tries:
                sleep(sleep_time)
                self.swap_liquidswap(
                    from_token_name,
                    to_token_name,
                    start_amount_in,
                    local_loss_ratio - loss_ratio_changer,
                    liquidswap_swaps_count,
                    retry + 1
                )
            else:
                return liquidswap_swaps_count

            return liquidswap_swaps_count - 1

    def swap_pancakeswap(
            self,
            from_token_name: str,
            to_token_name: str,
            amount_in: float,
            local_loss_ratio: float,
            pancakeswap_swaps_count: int,
            retry=0
    ) -> int:
        start_amount_in = amount_in

        try:
            amount_in = self.float_to_wei(amount_in, from_token_name)

            simulation_payload = EntryFunction.natural(
                network_modules["pancakeswap"]["script"],
                network_modules["pancakeswap"]["function"],
                self.get_type_args("pancakeswap", from_token_name, to_token_name),
                [
                    TransactionArgument(amount_in, Serializer.u64),
                    TransactionArgument(0, Serializer.u64),
                ]
            )

            tx = self.create_bcs_transaction(self.signer, TransactionPayload(simulation_payload))
            simulation = self.simulate_transaction(tx, self.signer)
            amount_out = int(int(simulation[0]['events'][-1]['data']['amount_x_out']) * local_loss_ratio)

            payload = EntryFunction.natural(
                network_modules["pancakeswap"]["script"],
                network_modules["pancakeswap"]["function"],
                self.get_type_args("pancakeswap", from_token_name, to_token_name),
                [
                    TransactionArgument(amount_in, Serializer.u64),
                    TransactionArgument(amount_out, Serializer.u64),
                ]
            )

            signed_transaction = self.create_bcs_signed_transaction(self.signer, TransactionPayload(payload))
            tx = self.submit_bcs_transaction(signed_transaction)
            self.wait_for_transaction(tx)

            text = f"Success pancakeswap swap {self.wei_to_float(amount_in, from_token_name)} " \
                   f"{from_token_name} in {to_token_name}\n{get_explorer_hash_link(tx)}"
            logger.success(text)
            send_msg(self.bot, f"🟢 {text}")

            return pancakeswap_swaps_count - 1

        except Exception as e:
            tries = pancakeswap_exception(
                self.bot,
                from_token_name,
                to_token_name,
                str(e),
                self.proxy
            )

            if retry < tries:
                sleep(sleep_time)
                self.swap_pancakeswap(
                    from_token_name,
                    to_token_name,
                    start_amount_in,
                    local_loss_ratio - loss_ratio_changer,
                    pancakeswap_swaps_count,
                    retry + 1
                )
            else:
                return pancakeswap_swaps_count

            return pancakeswap_swaps_count - 1

    def stake(self, dex: str, stakes_count=1, retry=0, swaps_count=0) -> Union[int, int]:
        amount_in, self.client_config.max_gas_amount = get_stake_amount_in(dex, self.client_config.max_gas_amount)

        try:
            amount_in_wei = self.float_to_wei(amount_in, "apt")
            apt_balance = self.get_token_balance("apt")
            wallet_balance_in_apt = self.get_wallet_balance_in_apt()

            if wallet_balance_in_apt < amount_in:
                text = f"Can't stake {amount_in} apt, wallet balance less than minimum"
                logger.warning(text)
                send_msg(self.bot, f"🟡 {text}", disable_notification=False)
                return 0, swaps_count

            if apt_balance < amount_in_wei:
                for token_name in tokens_mapping:
                    balance = self.get_token_balance(token_name)
                    if balance > 0 and token_name != "apt":
                        liquidswap_swaps_count = self.swap_liquidswap(
                            token_name,
                            "apt",
                            balance,
                            loss_ratio,
                            liquidswap_swaps_count=1
                        )
                        if liquidswap_swaps_count == 0:
                            swaps_count += 1

                        sleep(sleep_time)
                    apt_balance = self.get_token_balance("apt")
                    if apt_balance > self.wei_to_float(amount_in_wei, "apt"):
                        break

            payload = EntryFunction.natural(
                network_modules[dex]["script"],
                network_modules[dex]["function"],
                [],
                [TransactionArgument(amount_in_wei, Serializer.u64)],
            )

            signed_transaction = self.create_bcs_signed_transaction(self.signer, TransactionPayload(payload))
            tx = self.submit_bcs_transaction(signed_transaction)
            self.wait_for_transaction(tx)

            text = f"Success {dex} stake {amount_in} apt\n{get_explorer_hash_link(tx)}"
            logger.success(text)
            send_msg(self.bot, f"🟢 {text}")

            return stakes_count - 1, swaps_count

        except Exception as e:
            self.client_config.max_gas_amount = stake_exception(
                self.bot,
                self.client_config.max_gas_amount,
                amount_in,
                str(e),
                self.proxy
            )

            if retry < total_tries:
                sleep(sleep_time)
                self.stake(dex, retry=retry + 1)
            else:
                return stakes_count, swaps_count

    def get_wallet_balance_in_apt(self):
        balance = 0
        for token_name in tokens_mapping:
            token_balance = self.get_token_balance(token_name)
            if token_name != "apt":
                token_balance = self.get_token_balance_in_apt(
                    token_balance, token_name)

            balance += token_balance
        return balance

    def send_aptos(self, to_address: str, amount: float) -> bool:
        try:
            to_account = AccountAddress.from_hex(to_address)
            amount = self.float_to_wei(amount, "apt")

            payload = EntryFunction.natural(
                "0x1::aptos_account",
                "transfer",
                [],
                [
                    TransactionArgument(to_account, Serializer.struct),
                    TransactionArgument(amount, Serializer.u64),
                ]
            )

            signed_transaction = self.create_bcs_signed_transaction(self.signer, TransactionPayload(payload))
            tx = self.submit_bcs_transaction(signed_transaction)
            self.wait_for_transaction(tx)

            text = f"Success send {self.wei_to_float(amount, 'apt')} apt to {to_address}\n{get_explorer_hash_link(tx)}"
            logger.success(text)
            send_msg(self.bot, f"🟢 {text}")

        except Exception as e:
            send_aptos_exception(self.bot, to_address, amount, str(e), self.proxy)

    def claim_bridged_tokens(self, bot) -> bool:
        try:
            token = TypeTag(StructTag.from_str(tokens_mapping[claimable_token]))
            payload = EntryFunction.natural(
                network_modules["layerzero_bridge"]["script"],
                network_modules["layerzero_bridge"]["function"],
                [token],
                []
            )

            signed_transaction = self.create_bcs_signed_transaction(self.signer, TransactionPayload(payload))
            tx = self.submit_bcs_transaction(signed_transaction)
            self.wait_for_transaction(tx)

            text = f"Success claim tokens\n{get_explorer_hash_link(tx)}"
            logger.success(text)
            send_msg(self.bot, f"🟢 {text}")

        except Exception as e:
            if "hash" in str(e):
                hash_pattern = r'"hash":"(0x[a-fA-F0-9]+)"'
                tx_hash = re.search(hash_pattern, str(e))
                if self.proxy is None:
                    response = self.client.get(f"{node_url}/transactions/by_hash/{tx_hash}")
                else:
                    response = self.client.get(
                        f"{node_url}/transactions/by_hash/{tx_hash}",
                        proxies={"https": f"http://{self.proxy}"}
                    )
                if "success" in response.json():
                    text = f"Success claim tokens\n{get_explorer_hash_link(tx_hash)}"
                    logger.success(text)
                    send_msg(bot, f"🟢 {text}")
                else:
                    text = f"No claimable tokens"
                    logger.warning(text)
                    send_msg(bot, f"🟡 {text}")
            else:
                text = f"Claim tokens from layerzero bridge error: {str(e)}"
                logger.error(text)
                send_msg(bot, f"🔴 {text}", disable_notification=False)

    def register_domain(self, name, signature, retry=0):
        try:
            self.client_config.max_gas_amount += 5000

            payload = EntryFunction.natural(
                network_modules["aptos_names"]["script"],
                network_modules["aptos_names"]["function"],
                [],
                [
                    TransactionArgument(name, Serializer.str),
                    TransactionArgument(1, Serializer.u8),
                    TransactionArgument(bytes.fromhex(signature[2:]), Serializer.to_bytes),
                ],
            )

            signed_transaction = self.create_bcs_signed_transaction(self.signer, TransactionPayload(payload))
            tx = self.submit_bcs_transaction(signed_transaction)
            self.wait_for_transaction(tx)

            text = f"Claimed `{name}` domain\n{get_explorer_hash_link(tx)}"
            logger.success(text)
            send_msg(self.bot, f"🟢 {text}")

        except Exception as e:
            if "Out of gas" in str(e):
                self.client_config.max_gas_amount += random.randint(4500, 6500)
                logger.warning("Gas less than minimum, try with more gas")
            elif "EINVALID_PROOF_OF_KNOWLEDGE" in str(e):
                logger.warning(
                    "Invalid proof of knowledge while try to register domain. Skip this wallet and get another")
                return False
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                if retry == 0:
                    text = "Need more APT to claim domain"
                    logger.error(text)
                    send_msg(self.bot, f"🔴 {text}")
                    return False
                else:
                    text = f"Problem with rpc connection, last swap was success. " \
                           f"Claimed `{name}` domain\n{get_explorer_hash_link(tx)}"
                    logger.success(text)
                    send_msg(self.bot, f"🟢 {text}")
                    return True
            elif "hash" in str(e):
                hash_pattern = r'"hash":"(0x[a-fA-F0-9]+)"'
                tx_hash = re.search(hash_pattern, str(e))
                if self.proxy is None:
                    response = self.client.get(f"{node_url}/transactions/by_hash/{tx_hash}")
                else:
                    response = self.client.get(
                        f"{node_url}/transactions/by_hash/{tx_hash}",
                        proxies={"https": f"http://{self.proxy}"}
                    )
                if "success" in response.json():
                    text = f"Claimed `{name}` domain\n{get_explorer_hash_link(tx_hash)}"
                    logger.success(text)
                    send_msg(self.bot, f"🟢 {text}")
                else:
                    text = f"Claim domain error: {str(e)}"
                    logger.error(text)
                    send_msg(self.bot, f"🔴 {text}")
            else:
                text = f"Claim domain error: {str(e)}"
                logger.error(text)
                send_msg(self.bot, f"🔴 {text}")

            if retry < total_tries:
                sleep(sleep_time)
                self.register_domain(name, signature, retry + 1)

            return False

        return True

    def register_subdomain(self, name, sub_name, timestamp, retry=0):
        try:
            self.client_config.max_gas_amount += 5000

            # todo: получить aptos name для аккаунта
            # todo: получить timestamp для aptos name

            payload = EntryFunction.natural(
                network_modules["aptos_names"]["script"],
                network_modules["aptos_names"]["function_sub"],
                [],
                [
                    TransactionArgument(sub_name, Serializer.str),
                    TransactionArgument(name, Serializer.str),
                    TransactionArgument(timestamp, Serializer.u64),
                ],
            )

            signed_transaction = self.create_bcs_signed_transaction(self.signer, TransactionPayload(payload))
            tx = self.submit_bcs_transaction(signed_transaction)
            self.wait_for_transaction(tx)

            text = f"Claimed `{sub_name}` sub domain\n{get_explorer_hash_link(tx)}"
            logger.success(text)
            send_msg(self.bot, f"🟢 {text}")

        except Exception as e:
            if "Out of gas" in str(e):
                self.client_config.max_gas_amount += random.randint(4500, 6500)
                logger.warning("Gas less than minimum, try with more gas")
            elif "EINVALID_PROOF_OF_KNOWLEDGE" in str(e):
                logger.warning(
                    "Invalid proof of knowledge while try to register domain. Skip this wallet and get another")
                return False
            elif "INSUFFICIENT_BALANCE_FOR_TRANSACTION_FEE" in str(e):
                if retry == 0:
                    text = "Need more APT to claim domain"
                    logger.error(text)
                    send_msg(self.bot, f"🔴 {text}")
                    return False
                else:
                    text = f"Problem with rpc connection, last swap was success. " \
                           f"Claimed `{name}` sub domain\n{get_explorer_hash_link(tx)}"
                    logger.success(text)
                    send_msg(self.bot, f"🟢 {text}")
                    return True
            elif "hash" in str(e):
                hash_pattern = r'"hash":"(0x[a-fA-F0-9]+)"'
                tx_hash = re.search(hash_pattern, str(e))
                if self.proxy is None:
                    response = self.client.get(f"{node_url}/transactions/by_hash/{tx_hash}")
                else:
                    response = self.client.get(
                        f"{node_url}/transactions/by_hash/{tx_hash}",
                        proxies={"https": f"http://{self.proxy}"}
                    )
                if "success" in response.json():
                    text = f"Claimed `{name}` domain\n{get_explorer_hash_link(tx_hash)}"
                    logger.success(text)
                    send_msg(self.bot, f"🟢 {text}")
                else:
                    text = f"Claim domain error: {str(e)}"
                    logger.error(text)
                    send_msg(self.bot, f"🔴 {text}")
            else:
                text = f"Claim sub domain error: {str(e)}"
                logger.error(text)
                send_msg(self.bot, f"🔴 {text}")

            if retry < total_tries:
                sleep(sleep_time)
                self.register_domain(name, signature, retry + 1)

            return False

        return True

    def account_resource(self, account_address, resource_type, ledger_version=None):
        if not ledger_version:
            request = f"{self.base_url}/accounts/{account_address}/resource/{resource_type}"
        else:
            request = f"{self.base_url}/accounts/{account_address}/resource/{resource_type}" \
                      f"?ledger_version={ledger_version}"

        if self.proxy is None:
            response = self.client.get(request)
        else:
            response = self.client.get(request, proxies={"https": f"http://{self.proxy}"})

        if response.status_code == 404:
            raise ResourceNotFound(resource_type, resource_type)
        if response.status_code >= 400:
            raise ApiError(f"{response.text} - {account_address}", response.status_code)
        return response.json()

    def submit_bcs_transaction(self, signed_transaction: SignedTransaction) -> str:
        headers = {"Content-Type": "application/x.aptos.signed_transaction+bcs"}

        if self.proxy is None:
            response = self.client.post(
                f"{self.base_url}/transactions",
                headers=headers,
                data=signed_transaction.bytes(),
            )
        else:
            response = self.client.post(
                f"{self.base_url}/transactions",
                headers=headers,
                data=signed_transaction.bytes(),
                proxies={"https": f"http://{self.proxy}"}
            )

        if response.status_code >= 400:
            if "hash" not in response.json():
                raise ApiError(response.text, response.status_code)
        return response.json()["hash"]

    def wait_for_transaction(self, txn_hash: str) -> None:
        time.sleep(3)
        count = 0
        while self.transaction_pending(txn_hash):
            assert (count < self.client_config.transaction_wait_in_seconds), f"transaction {txn_hash} timed out"
            time.sleep(1)
            count += 1

        if self.proxy is None:
            response = self.client.get(f"{self.base_url}/transactions/by_hash/{txn_hash}")
        else:
            response = self.client.get(
                f"{self.base_url}/transactions/by_hash/{txn_hash}",
                proxies={"https": f"http://{self.proxy}"}
            )
        assert ("success" in response.json() and response.json()["success"]), f"{response.text} - {txn_hash}"

    def transaction_pending(self, txn_hash: str) -> bool:
        if self.proxy is None:
            response = self.client.get(f"{self.base_url}/transactions/by_hash/{txn_hash}")
        else:
            response = self.client.get(
                f"{self.base_url}/transactions/by_hash/{txn_hash}",
                proxies={"https": f"http://{self.proxy}"}
            )
        if response.status_code == 404:
            return True
        if response.status_code >= 400:
            raise ApiError(response.text, response.status_code)
        return response.json()["type"] == "pending_transaction"

    def simulate_transaction(self, transaction: RawTransaction, sender: Account) -> Dict[str, Any]:
        authenticator = Authenticator(Ed25519Authenticator(sender.public_key(), ed25519.Signature(b"\x00" * 64)))
        signed_transaction = SignedTransaction(transaction, authenticator)

        headers = {"Content-Type": "application/x.aptos.signed_transaction+bcs"}
        if self.proxy is None:
            response = self.client.post(
                f"{self.base_url}/transactions/simulate",
                headers=headers,
                data=signed_transaction.bytes()
            )
        else:
            response = self.client.post(
                f"{self.base_url}/transactions/simulate",
                headers=headers,
                data=signed_transaction.bytes(),
                proxies={"https": f"http://{self.proxy}"}
            )
        if response.status_code >= 400:
            raise ApiError(response.text, response.status_code)

        return response.json()
