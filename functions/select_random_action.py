import random

from loguru import logger

from libs.eth_async.blockscan_api import APIFunctions
from tasks.controller import Controller
from data.models import Settings, Contracts
from libs.eth_async.data.models import Networks
from utils.db_api.models import Wallet


async def select_random_action(controller: Controller, wallet: Wallet):
    settings = Settings()

    possible_actions = []
    weights = []

    eth_balance = await controller.client.wallet.balance()

    sufficient_balance_eth = float(eth_balance.Ether) > settings.minimal_balance # + settings.eth_amount_for_bridge.to_

    usdc_balance = await controller.client.wallet.balance(token=Contracts.Sepolia_USDC)
    dai_balance = await controller.client.wallet.balance(token=Contracts.Sepolia_DAI)
    usdt_balance = await controller.client.wallet.balance(token=Contracts.Sepolia_USDT)

    print(f'Balances: eth: {eth_balance.Ether}; usdc: {usdc_balance.Ether}; '
          f'dai: {dai_balance.Ether}; usdt: {usdt_balance.Ether}')

    if not sufficient_balance_eth:
        return 'Insufficient balance'
        # todo: добавить сюда функцию для обратного бриджа

    # todo: изменить логику выбора: добавить ветвление, сначала провверяем труфолс эфира и стейблов,
    #  потом рандомим либо ветка бридж эфира, либо ветка бридж стейблов с проверкой баланса и краном

    # if usdc_balance.Ether < 4000 or usdt_balance.Ether < 4000 or dai_balance.Ether < 4000:
    #     if usdc_balance.Ether < 4000:
    #         possible_actions += [
    #             controller.sepolia.faucet_usdc,
    #             controller.sepolia.faucet_usdt,
    #             controller.sepolia.faucet_dai,
    #             controller.sepolia.deposit_eth_to_hemi
    #         ]
    #         weights += [
    #             10,
    #             1,
    #             1,
    #             3
    #         ]
    #     if usdt_balance.Ether < 4000:
    #         possible_actions += [
    #             controller.sepolia.faucet_usdc,
    #             controller.sepolia.faucet_usdt,
    #             controller.sepolia.faucet_dai,
    #             controller.sepolia.deposit_eth_to_hemi
    #         ]
    #         weights += [
    #             1,
    #             10,
    #             1,
    #             3
    #         ]
    #     if dai_balance.Ether < 4000:
    #         possible_actions += [
    #             controller.sepolia.faucet_usdc,
    #             controller.sepolia.faucet_usdt,
    #             controller.sepolia.faucet_dai,
    #             controller.sepolia.deposit_eth_to_hemi
    #         ]
    #         weights += [
    #             1,
    #             1,
    #             10,
    #             3
    #         ]
    # print('0', wallet.today_activity_eth, wallet.today_activity_erc20, usdc_balance.Ether)
    # if wallet.today_activity_eth is False and wallet.today_activity_erc20 is False:
    #     possible_actions += [
    #         controller.sepolia.deposit_eth_to_hemi,
    #         controller.sepolia.bridge_dai_to_hemi,
    #         controller.sepolia.bridge_usdc_to_hemi,
    #         controller.sepolia.bridge_usdt_to_hemi,
    #         # todo: сюда добавлять потом свапы и капсулу
    #     ]
    #     weights += [
    #         1,
    #         1,
    #         1,
    #         1,
    #     ]
    # # print('1', wallet.today_activity_eth, wallet.today_activity_erc20, usdc_balance.Ether)
    # if wallet.today_activity_eth is False and wallet.today_activity_erc20 is True:
    #     possible_actions += [
    #         controller.sepolia.deposit_eth_to_hemi,
    #         # todo: сюда добавлять потом свапы и капсулу
    #     ]
    #     weights += [
    #         1,
    #     ]

        # if wallet.today_activity_eth is True and wallet.today_activity_erc20 is False\
        #         and usdc_balance.Ether > 4000 and usdt_balance.Ether > 4000 and dai_balance.Ether > 4000:
        #     possible_actions += [
        #         controller.sepolia.bridge_dai_to_hemi,
        #         controller.sepolia.bridge_usdc_to_hemi,
        #         controller.sepolia.bridge_usdt_to_hemi,
        #         # todo: сюда добавлять потом свапы и капсулу
        #     ]
        #     weights += [
        #         1,
        #         1,
        #         1
        #     ]
    # print('2', wallet.today_activity_eth, wallet.today_activity_erc20, usdc_balance.Ether)
    # if wallet.today_activity_eth is True and wallet.today_activity_erc20 is False\
    #         and usdc_balance.Ether > 4000:
    #
    #     possible_actions += [
    #             controller.sepolia.bridge_dai_to_hemi,
    #             controller.sepolia.bridge_usdc_to_hemi,
    #             controller.sepolia.bridge_usdt_to_hemi,
    #             # todo: сюда добавлять потом свапы и капсулу
    #         ]
    #     weights += [
    #             1,
    #             5,
    #             1
    #         ]
    #
    # if wallet.today_activity_eth is True and wallet.today_activity_erc20 is False\
    #             and usdt_balance.Ether > 4000:
    #     possible_actions += [
    #             controller.sepolia.bridge_dai_to_hemi,
    #             controller.sepolia.bridge_usdc_to_hemi,
    #             controller.sepolia.bridge_usdt_to_hemi,
    #             # todo: сюда добавлять потом свапы и капсулу
    #         ]
    #     weights += [
    #             1,
    #             1,
    #             5
    #         ]
    #
    # if wallet.today_activity_eth is True and wallet.today_activity_erc20 is False\
    #             and dai_balance.Ether > 4000:
    #     possible_actions += [
    #             controller.sepolia.bridge_dai_to_hemi,
    #             controller.sepolia.bridge_usdc_to_hemi,
    #             controller.sepolia.bridge_usdt_to_hemi,
    #             # todo: сюда добавлять потом свапы и капсулу
    #         ]
    #     weights += [
    #             5,
    #             1,
    #             1
    #         ]

    if wallet.today_activity_eth < 25:
        possible_actions += [
            controller.sepolia.deposit_eth_to_hemi,
        ]
        weights += [
            1,
        ]
    if possible_actions:
        action = None
        while not action:
            action = random.choices(possible_actions, weights=weights)[0]

        else:
            return action

    return None
