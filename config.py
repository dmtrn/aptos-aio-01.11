wallets_txt_path = "data/wallets.txt"
proxys_txt_path = "data/proxys.txt"
addresses_txt_path = "data/addresses.txt"
names_txt_path = "data/names.txt"
timestamps_txt_path = "data/timestamps.txt"
database_path = "data/database.json"
node_url = "https://fullnode.mainnet.aptoslabs.com/v1"

# token mapping setup
tokens_mapping = {
    "apt": "0x1::aptos_coin::AptosCoin",
    # "lz_usdt": "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDT",
    "lz_usdc": "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC",
    # "lz_weth": "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::WETH",
    # "wh_usdc": "0x5e156f1207d0ebfa19a9eeff00d62a282278fb8719f4fab3a586a0a2c0fffbea::coin::T",
    # "tapt": "0x84d7aeef42d38a5ffc3ccef853e1b82e4958659d16a7de736a29c55fbbeb0114::staked_aptos_coin::StakedAptosCoin",
    # "ditto": "0xd11107bdf0d6d7040c6c0bfbdecb6545191fdf13e8d8d259952f53e1713f61b5::staked_coin::StakedAptos"
}

# тут указывать название из tokens_mapping
claimable_token = "lz_usdc"  # USDT: "lz_usdt"

# Токен для тг бота
tg_token = ""
# ID тг акков, куда слать сообщения боту
tg_ids = []

# OKX creds
api_key = ""
secret = ""
password = ""

okx_sub_creds = {
    "ui1": {
        "apiKey": "",
        "secret": "",
        "password": "",
    }
}

# True если нужно использовать прокси для вывода с OKX. False, если нет
use_proxy_okx = False

# время ожидания между свапами
sleep_time = [5, 5]
sleep_time_wallets = [10, 10]
cex_sleep_time = [100, 150]

# количество попыток, если свап с ошибкой
total_tries = 3

# количество попыток, которые скрипт будет запускать ожидание ввода средств на OKX в low bank warmup режиме
# в случае если все попытки закончатся и деньги так и не дойдут, то скрипт остановит работу
low_bank_total_tries = 100

# минимальный баланс в APT на акке (в случае, если он меньше,
# то будет вызван модуль, который докинет с биржи APT на акк)
min_gas_balance = 0.03

# количество APT на gas для вывода с биржи для модуля warmup with gas
# учитывайте то, что min_gas_balance должен быть меньше, чем значение "от"
gas_withdraw_deviation = [0.05, 0.1]

# количество APT на gas для вывода с биржи для клейма aptosname
withdraw_for_names = [1.002, 1.007]

# количество APT на gas для вывода с биржи для low bank warmup
withdraw_for_low_bank = [0.15, 0.20]

# Ключ от https://rucaptcha.com/
captcha_key = ""

# для свапа берется монета с наибольшим балансом
# количество [от, до] в % сколько токенов свапать
swap_deviation = [0.5, 0.9]

# True если использовать прокси (вне зависимости какой, даже если мобильный, то ставить True)
use_proxy = False

# True если вы используете мобильный прокси (тесты были только для "https://mobileproxy.space/")
use_mobile_proxy = False

# При использовании мобильных прокси есть ссылка для смены ip, если вы используете мобильные прокси,
# то впишите данную ссылку полностью ниже (тесты были только для "https://mobileproxy.space/")
change_ip_url = ""

# Количество свапов подряд на одном аккаунте
# учитывайте, что в low bank warmup есть встроенный коллектор, его свапы сюда не входят
circle_swaps_count = [5, 5]

# количество свапов, которые будут сделаны на панкейксвапе и ликвидсвапе
pancakeswap_swap_count = [10, 20]
liquidswap_swap_count = [10, 20]

# количество раз сколько делать стейк с акка на тортуге
tortuga_stake_count = [0, 0]
# количество токенов для стейка на tortuga (МИНИМАЛКА 0.01)
tortuga_stake_deviation = [0.01, 0.01]

# количество раз сколько делать стейк с акка на дитто
ditto_stake_count = [0, 0]
# количество токенов для стейка на ditto (нет минимального значения, но лучше не ставить меньше 0.0001)
ditto_stake_deviation = [0.001, 0.001]

# количество раз сколько клеймить aptosname
aptos_names_count = [0, 0]
# количество раз сколько клеймить субдомен aptosname
sub_aptos_names_count = [5, 5]

# С ЭТИМ ОЧЕНЬ АККУРАТНО
# коэффициент потерь при свапе (пример: 1 usdt = 1 * loss_ratio usdc after swap)
loss_ratio = 0.99
# дословно уменьшитель коэффициента loss_ratio (если свап не прошел, то следующая попытка уменьшит loss_ratio
# на loss_ratio_changer, количество таких попыток указано в total_tries в конфиге выше)
loss_ratio_changer = 0.01

# коэффициент токен для отправки APT на адрес (к примеру биржи OKX), также используется для low_bank_warmup
# (пример: 1 APT = 1 * send_ratio APT будет отправлено, следовательно при send_ratio = 0.9 будет отправлено 0.9 APT)
send_ratio = 0.95
