from aptos_sdk import ed25519
from aptos_sdk.account_address import AccountAddress


class Wallet:
    def __init__(self, private_key, proxy):
        self.private_key = private_key
        self.address = self.get_account_address(private_key)
        self.proxy = proxy

    @staticmethod
    def get_account_address(private_key: str):
        private_key = ed25519.PrivateKey.from_hex(private_key)
        return AccountAddress.from_key(private_key.public_key()).hex()
