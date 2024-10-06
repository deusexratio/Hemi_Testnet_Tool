import random
import asyncio
from datetime import datetime, timedelta, timezone
from ipaddress import summarize_address_range

from sqlalchemy.testing import startswith_
from web3 import Web3
from loguru import logger
from sqlalchemy import select, func, or_, and_

from libs.eth_async import client
from libs.eth_async.client import Client
from libs.eth_async.data.models import Network, Networks, TokenAmount, RawContract

from data.models import Settings, Contracts
from data.config import DELAY_IN_CASE_OF_ERROR
from utils.db_api.wallet_api import db, reset_daily_tasks, get_wallets
from libs.eth_async.transactions import Transactions
from utils.db_api.models import Wallet
from tasks.controller import Controller
from functions.select_random_action import select_random_action
from utils.update_expired import update_next_action_time, update_today_activity

# todo: разобраться до конца с исключением по газу,
#  а также ValueError: {'code': -32000, 'message': 'replacement transaction underpriced'}
#  вот такое еще было ValueError: {'code': -32000, 'message': 'already known'}
#  и такое ValueError: {'code': -32000, 'message': 'nonce too low: next nonce 6, tx nonce 5'}
async def hourly_check_failed_txs(contract: RawContract | str,
                                  function_names: str | list[str] | None = None,
                                  network: Network = Networks.Sepolia) -> bool:
    await asyncio.sleep(90) # sleep at start not to interfere with activity logs, mostly for debug
    while True:
        try:
            # later delete function_name argument maybe
            if function_names is None:
                function_names = ['depositETH', 'depositERC20']
            wallets = get_wallets()
            now_utc = datetime.now(timezone.utc)
            midnight_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            after_timestamp = int(midnight_utc.timestamp())
            for wallet in wallets:
                print(f'Checking txs statuses for wallet: {wallet}')
                client = Client(private_key=wallet.private_key, network=network)
                if isinstance(contract, RawContract):
                    contract = contract.address
                error_txs_dict = {}
                non_error_txs_dict = {}
                if isinstance(function_names, list):

                    # Update statuses in db for failed txs
                    for function in function_names:
                        txs_with_error = await client.transactions.find_txs(
                            contract=contract,
                            function_name=function,
                            after_timestamp=after_timestamp,
                            address=wallet.address,
                            is_error='1'
                        )
                        error_txs_dict[function] = txs_with_error
                    for key, value in error_txs_dict.items():
                        # print(key, value)
                        if value:  # check if tx exists, failed to come up with additional checks for now
                            print(f'failed {key}')
                            update_today_activity(private_key=wallet.private_key, activity=key, key=False)

                    # Update statuses in DB for successful txs (needed bc failed txs been marked so for a whole day
                    # which leads to an endless daily activity cycle for a wallet)
                    for function in function_names:
                        txs_without_error = await client.transactions.find_txs(
                            contract=contract,
                            function_name=function,
                            after_timestamp=after_timestamp,
                            address=wallet.address,
                            is_error='0'
                        )
                        non_error_txs_dict[function] = txs_without_error
                    for key, value in non_error_txs_dict.items():
                        # print(key, value)
                        if value:  # check if tx exists, failed to come up with additional checks for now
                            print(f'not failed {key}')
                            update_today_activity(private_key=wallet.private_key, activity=key, key=True)

                # STRING NOT TESTED
                elif isinstance(function_names, str):
                    txs_with_error = await client.transactions.find_txs(
                        contract=contract,
                        function_name=function_names,
                        after_timestamp=after_timestamp,
                        address=wallet.address,
                        is_error='1'
                    )
                    txs_without_error = await client.transactions.find_txs(
                        contract=contract,
                        function_name=function_names,
                        after_timestamp=after_timestamp,
                        address=wallet.address,
                        is_error='0'
                    )
                    if txs_with_error:
                        update_today_activity(private_key=wallet.private_key, activity=function_names, key=False)
                    elif txs_without_error:
                        update_today_activity(private_key=wallet.private_key, activity=function_names, key=True)

                else:
                    logger.error(f'Wrong function names given to hourly_check_failed_txs: {function_names}')
                await asyncio.sleep(3)  # sleep to not exceed api request limit

        except BaseException as e:
            logger.exception(f'Something went wrong: {e}')
            return False
        finally:
            await asyncio.sleep(3600)  # sleep to check statuses every hour


async def auto_daily_reset_activities() -> bool:
    while True:
        try:
            now_utc_hour = int(datetime.now(timezone.utc).time().hour)
            print(f'Current UTC hour: {now_utc_hour}')
            if now_utc_hour == 0:
                for wallet in get_wallets():
                    wallet.today_activity_eth = False
                    wallet.today_activity_erc20 = False
                    wallet.today_activity_swaps = False
                    wallet.today_activity_capsule = False
                db.commit()
                logger.info(f'Succesfully reset activities at {datetime.now()}')
            await asyncio.sleep(1800)  # wait for next hour to try
        except BaseException:
            return False

def manual_daily_reset_activities() -> bool:
    try:
        for wallet in get_wallets():
            wallet.today_activity_eth = False
            wallet.today_activity_erc20 = False
            wallet.today_activity_swaps = False
            wallet.today_activity_capsule = False
        db.commit()
        logger.info(f'Succesfully reset activities at {datetime.now()}')
    except BaseException:
        return False


async def select_wallet(queue, tasks_num):
    if queue.empty():  # check if wallet is in queue
        # print(queue)
        stmt_start = (select(Wallet).where(
            or_(Wallet.today_activity_eth.is_(False),
                Wallet.today_activity_erc20.is_(False),
                # Wallet.today_activity_swaps.is_(False)
                )
        ).where(Wallet.next_action_time <= datetime.now()
                ).order_by(Wallet.next_action_time)
                      )
        wallet: Wallet = db.one(Wallet, stmt=stmt_start)
        await queue.put(wallet)
        return wallet
    elif not queue.empty():
        random_number = random.randint(1, tasks_num)
        q_size: int = queue.qsize()
        # print(f'queue not empty: {queue}')
        queue.get_nowait()  # get wallet just to put it out of queue
        # print(f'queue after get_nowait: {queue}')
        stmt_start = (select(Wallet).where(
            or_(Wallet.today_activity_eth.is_(False),
                Wallet.today_activity_erc20.is_(False),
                # Wallet.today_activity_swaps.is_(False)
                )
        ).where(Wallet.next_action_time <= datetime.now()
                ).order_by(Wallet.next_action_time).offset(random_number).limit(random_number)
                      )
        wallet: Wallet = db.one(Wallet, stmt=stmt_start)
        return wallet

async def correct_next_action_time():
    # Check if next action time is assigned correctly
    # and if not, add 30 minutes to a wallet that has been already done
    while True:
        try:
            for wallet in get_wallets():
                if wallet.today_activity_eth and wallet.today_activity_erc20:
                    update_next_action_time(private_key=wallet.private_key, seconds=1800)
                    logger.info(
                        f'Added 30 minutes to next action time '
                        f'for already done wallet: {wallet} : {wallet.next_action_time}')
            await asyncio.sleep(1800)
        except BaseException:
            return False


async def activity(queue, tasks_num):
    await asyncio.sleep(random.randint(5, 15))  # sleep to one of the tasks become first and put wallet to queue
    while True:
        try:
            settings = Settings() # settings are updated automatically at each iteration НЕТ
            delay = 5

            # Fill in next action time for newly initialized wallets in DB
            stmt_first = (select(Wallet).filter(Wallet.next_action_time.is_(None)))
            first_time_wallet: Wallet = db.one(Wallet, stmt=stmt_first)

            if first_time_wallet:
                print(f'first_time_wallet: {first_time_wallet}')
                first_time_wallet.next_action_time = datetime.now() + timedelta(seconds=random.randint(10, 20))
                db.insert(first_time_wallet)

            # Check if gas price is OK
            client = Client(private_key='', network=Networks.Sepolia)
            gas_price = await client.transactions.gas_price()

            while float(gas_price.Wei) > Web3.to_wei(settings.maximum_gas_price, 'gwei'):
                logger.debug(f'Gas price is too high'
                             f'({Web3.from_wei(gas_price.Wei, "gwei")} > {settings.maximum_gas_price})')
                await asyncio.sleep(60 * 1)
                gas_price = await client.transactions.gas_price()

            # Select wallet from DB to do an activity
            wallet = await select_wallet(queue,tasks_num)
            # print(stmt_start)
            print(f'{datetime.now().time().replace(microsecond=0)} : wallet: {wallet}')
            if not wallet:
                await asyncio.sleep(delay)
                continue

            # Create Client and Controller instances for selected wallet
            client = Client(private_key=wallet.private_key, network=Networks.Sepolia, proxy=wallet.proxy)
            controller = Controller(client=client)

            # Pick an action for selected wallet
            action = await select_random_action(controller=controller, wallet=wallet)
            if action:  # debug
                print(wallet, action)  # debug


            if not action:
                logger.error(f'{wallet.address} | select_random_action | can not choose the action')
                update_next_action_time(private_key=wallet.private_key, seconds=DELAY_IN_CASE_OF_ERROR)
                continue

            if action == 'Insufficient balance':
                logger.error(f'{wallet.address}: Insufficient balance')
                if settings.use_autorefill:
                    controller.testnet_bridge.bridge(client=client)
                update_next_action_time(private_key=wallet.private_key, seconds=DELAY_IN_CASE_OF_ERROR)
                # wallet.insufficient_balance = True
                # db.commit()
                continue

            # Process result of action: log what has been done or if action failed
            status = await action()

            if 'Failed' not in status:
                update_next_action_time(
                    private_key=wallet.private_key,
                    seconds=random.randint(settings.activity_actions_delay.from_,
                                           settings.activity_actions_delay.to_)
                )
                print(status)
                wallet.today_activity_eth += 1
                db.commit()
                logger.success(f'{wallet}: {status}')

                if 'ETH was bridged to Hemi via official bridge' in status:
                    update_today_activity(private_key=wallet.private_key, activity='depositETH')
                if 'stablecoin was bridged to Hemi via official bridge' in status:
                    update_today_activity(private_key=wallet.private_key, activity='depositERC20')
                if 'swapped' in status:
                    update_today_activity(private_key=wallet.private_key, activity='swaps')  # todo: change method name
                if 'capsule' in status:
                    update_today_activity(private_key=wallet.private_key,
                                          activity='capsule')  # todo: change method name

                # Display next action time
                stmt = (select(func.min(Wallet.next_action_time)).where(
                    or_(Wallet.today_activity_eth.is_(False),
                        Wallet.today_activity_erc20.is_(False),
                        Wallet.today_activity_swaps.is_(False)
                        )
                )
                )
                next_action_time = db.one(stmt=stmt)
                logger.info(f'The next closest activity action will be performed at {next_action_time}')
                await asyncio.sleep(delay)

            else:
                update_next_action_time(private_key=wallet.private_key, seconds=DELAY_IN_CASE_OF_ERROR)
                db.commit()
                logger.error(f'{wallet.address}: {status}')


        except BaseException as e:
            logger.exception(f'Something went wrong: {e}')

        except ValueError as err:
            logger.exception(f'Something went wrong: {err}')

        finally:
            await asyncio.sleep(delay)
