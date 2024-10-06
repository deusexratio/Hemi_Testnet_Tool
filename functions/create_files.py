import os
import csv

from libs.eth_async.utils.utils import update_dict
from libs.eth_async.utils.files import touch, write_json, read_json

from data import config
from data.models import WalletCSV


def create_files():
    touch(path=config.FILES_DIR)
    touch(path=config.LOG_FILE, file=True)
    touch(path=config.ERRORS_FILE, file=True)

    if not os.path.exists(config.IMPORT_FILE):
        with open(config.IMPORT_FILE, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(WalletCSV.header)

    try:
        current_settings: dict | None = read_json(path=config.SETTINGS_FILE)
    except Exception:
        current_settings = {}

    settings = {
        'maximum_gas_price': 500,
        'etherscan_api_key': '',
        'minimal_balance': 1,
        'use_autorefill': True,
        'autorefill_amount': {'from': 0.001, 'to': 0.002},
        'eth_amount_for_bridge': {'from': 0.1, 'to': 0.5},
        'eth_amount_for_swap': {'from': 1, 'to': 2},
        'stable_faucet_amount': {'from': 9000, 'to': 10000},
        'erc20_amount_to_bridge': {'from': 4000, 'to': 4200},
        'activity_actions_delay': {'from': 1000, 'to': 2000},
        'token_amount_for_capsule': {'from': 10, 'to': 50},
    }
    write_json(path=config.SETTINGS_FILE, obj=update_dict(modifiable=current_settings, template=settings), indent=2)


create_files()
