class SwapInfo:
    def __init__(
            self,
            dex,
            percentage_tokens_for_swap,
            from_token_name,
            from_token_balance,
            to_token_name,
            amount
    ):
        self.dex = dex
        self.percentage_tokens_for_swap = percentage_tokens_for_swap
        self.from_token_name = from_token_name
        self.from_token_balance = from_token_balance
        self.to_token_name = to_token_name
        self.amount = amount
