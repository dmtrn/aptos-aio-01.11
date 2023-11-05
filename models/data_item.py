import random


class DataItem:
    def __init__(
            self,
            wallet,
            pancakeswap_swaps_count,
            liquidswap_swaps_count,
            tortuga_stake_count,
            ditto_stake_count,
            aptos_names_count,
            sub_aptos_names_count,
            to_address
    ):
        try:
            self.private_key = wallet.private_key
            self.address = wallet.address
            self.proxy = wallet.proxy
            self.to_address = to_address
            self.pancakeswap_swaps_count = random.randint(pancakeswap_swaps_count[0], pancakeswap_swaps_count[1])
            self.liquidswap_swaps_count = random.randint(liquidswap_swaps_count[0], liquidswap_swaps_count[1])
            self.tortuga_stake_count = random.randint(tortuga_stake_count[0], tortuga_stake_count[1])
            self.ditto_stake_count = random.randint(ditto_stake_count[0], ditto_stake_count[1])
            self.aptos_names_count = random.randint(aptos_names_count[0], aptos_names_count[1])
            self.sub_aptos_names_count = random.randint(sub_aptos_names_count[0], sub_aptos_names_count[1])
        except:
            self.private_key = wallet.private_key
            self.address = wallet.address
            self.proxy = wallet.proxy
            self.to_address = to_address
            self.pancakeswap_swaps_count = pancakeswap_swaps_count
            self.liquidswap_swaps_count = liquidswap_swaps_count
            self.tortuga_stake_count = tortuga_stake_count
            self.ditto_stake_count = ditto_stake_count
            self.aptos_names_count = aptos_names_count
            self.sub_aptos_names_count = sub_aptos_names_count
