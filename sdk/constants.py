pancakeswap_module_account = "0xc7efb4076dbe143cbcd98cfaaa929ecfc8f299203dfff63b95ccb6bfe19850fa"
liquidswap_module_account = "0x190d44266241744264b964a37b8f09863167a12d3e70cda39376cfb4e3561e12"
tortuga_module_account = "0x8f396e4246b2ba87b51c0739ef5ea4f26515a98375308c31ac2ec1e42142a57f"
ditto_module_account = "0xd11107bdf0d6d7040c6c0bfbdecb6545191fdf13e8d8d259952f53e1713f61b5"
layerzero_bridge = "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa"
aptos_names = "0x867ed1f6bf916171b1de3ee92849b8978b7d1b9e0a8cc982a3d19d535dfd9c0c"

curve_uncorrelated = f"{liquidswap_module_account}::curves::Uncorrelated"

network_modules = {
    "pancakeswap": {
        "resource_type": f"{pancakeswap_module_account}::swap::TokenPairReserve",
        "script": f"{pancakeswap_module_account}::router",
        "function": "swap_exact_input",
        "resource_account": "0xc7efb4076dbe143cbcd98cfaaa929ecfc8f299203dfff63b95ccb6bfe19850fa",
    },
    "liquidswap": {
        "resource_type": f"{liquidswap_module_account}::liquidity_pool::LiquidityPool",
        "script": f"{liquidswap_module_account}::scripts_v2",
        "function": "swap",
        "resource_account": "0x05a97986a9d031c4567e15b797be516910cfcb4156312482efc6a19c0a30c948",
    },
    "tortuga": {
        "script": f"{tortuga_module_account}::stake_router",
        "function": "stake",
    },
    "ditto": {
        "script": f"{ditto_module_account}::ditto_staking",
        "function": "stake_aptos",
    },
    "layerzero_bridge": {
        "script": f"{layerzero_bridge}::coin_bridge",
        "function": "claim_coin"
    },
    "aptos_names": {
        "script": f"{aptos_names}::domains",
        "function": "register_domain_with_signature",
        "function_sub": "register_subdomain"
    }
}

coin = {
    "info": "0x1::coin::CoinInfo",
    "store": "0x1::coin::CoinStore",
}
