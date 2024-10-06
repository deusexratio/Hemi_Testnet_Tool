import asyncio
import random

from web3.types import TxParams
from fake_useragent import UserAgent

from libs.eth_async.data.models import TokenAmount, RawContract, TxArgs, Network, Networks
from libs.eth_async.utils.web_requests import async_post
from libs.eth_async.client import Client
from data.models import Contracts, Settings
from tasks.base import Base


class Testnet_Bridge(Base):
    @staticmethod
    async def get_price_seth(client: Client,
                             amount_eth: TokenAmount | None = None,
                             slippage: float = 5) -> int | None:
        headers = {
            'accept': '*/*',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'content-type': 'text/plain;charset=UTF-8',
            'origin': 'https://app.uniswap.org',
            'priority': 'u=1, i',
            'referer': 'https://app.uniswap.org/',
            'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': UserAgent().chrome,
            'x-request-source': 'uniswap-web',
        }

        data = {
            "tokenInChainId": 42161,
            "tokenIn": "ETH",
            "tokenOutChainId": 42161,
            "tokenOut": "0xe71bdfe1df69284f00ee185cf0d95d0c7680c0d4",
            "amount": str(amount_eth.Wei),
            "sendPortionEnabled": 'true',
            "type": "EXACT_INPUT",
            "intent": "quote",
            "configs": [
                {
                    "enableUniversalRouter": 'true',
                    "protocols": [
                        "V2",
                        "V3",
                        "MIXED"
                    ],
                    "routingType": "CLASSIC",
                    "recipient": client.account.address,
                    "enableFeeOnTransferFeeFetching": 'true'
                }
            ],
            "useUniswapX": 'true',
            "swapper": client.account.address,
            "slippageTolerance": str(slippage)
        }
        response = await async_post(url='https://interface.gateway.uniswap.org/v2/quote',
                                    headers=headers, data=data)
        seth_price = response['quote']['quoteGasAndPortionAdjusted']
        return int(seth_price) # returns int in wei

    async def bridge(self, client: Client,
                            # amount_eth: TokenAmount,
                            slippage: float = 5) -> str | None:
        settings = Settings()
        amount_eth = TokenAmount(random.uniform(settings.autorefill_amount.from_, settings.autorefill_amount.to_))
        seth_amount = await Testnet_Bridge.get_price_seth(client=client, amount_eth=amount_eth, slippage=slippage)
        failed_text = f'Failed to bridge {amount_eth} ETH to Sepolia via Testnet Bridge'
        op_client = Client(private_key=client.account.key, network=Networks.Optimism)
        arb_client = Client(private_key=client.account.key, network=Networks.Arbitrum)
        op_balance = await op_client.wallet.balance()
        arb_balance = await arb_client.wallet.balance()

        if op_balance.Wei > arb_balance.Wei and op_balance.Ether > settings.autorefill_amount.to_:
            client = op_client
            contract = await self.client.contracts.get(contract_address=Contracts.Testnet_Bridge_Optimism)
            network = 'Optimism'
        elif arb_balance.Wei > op_balance.Wei and arb_balance.Ether > settings.autorefill_amount.to_:
            client = arb_client
            contract = await self.client.contracts.get(contract_address=Contracts.Testnet_Bridge_Arbitrum)
            network = 'Arbitrum'
        else:
            return 'Insufficient balances for refill'

        args = TxArgs(
            amountIn=amount_eth.Wei,
            amountOutMin=seth_amount,
            dstChainId=161,
            to=client.account.address,
            refundAddress=client.account.address,
            zroPaymentAddress='0x0000000000000000000000000000000000000000',
            adapterParams=b'',
        )

        tx_params = TxParams(
            to=contract.address,
            data=contract.encodeABI('swapAndBridge', args=args.tuple()),
            value=amount_eth.Wei
        )

        tx = await self.client.transactions.sign_and_send(tx_params=tx_params)
        receipt = await tx.wait_for_receipt(client=self.client, timeout=500)
        check_tx_error = await Base.check_tx(str(tx.hash))
        print(f'check_tx_error bridge eth: {check_tx_error.Error}')
        if bool(receipt) is True and check_tx_error.Error is False:
            return f'{amount_eth.Ether} ETH was bridged to Sepolia from {network} via Testnet Bridge: {tx.hash.hex()}'
        else:
            return f'{failed_text}! Error: {check_tx_error.ErrDescription}, Tx_hash: {tx.hash.hex()}'



class Sepolia(Base):
    async def deposit_eth_to_hemi(self, amount: TokenAmount | None = None) -> str:
        failed_text = f'Failed to bridge {amount} ETH to Hemi via Official Bridge'
        if not amount:
            amount = Base.get_eth_amount_for_bridge()
        contract = await self.client.contracts.get(contract_address=Contracts.Hemi_Bridge_Sepolia)
        args = TxArgs(
            _minGasLimit=200000,
            _extraData=b''
        )

        tx_params = TxParams(
            to=contract.address,
            data=contract.encodeABI('depositETH', args=args.tuple()),
            value=amount.Wei
        )

        tx = await self.client.transactions.sign_and_send(tx_params=tx_params)
        receipt = await tx.wait_for_receipt(client=self.client, timeout=500)
        check_tx_error = await Base.check_tx(str(tx.hash))
        print(f'check_tx_error bridge eth: {check_tx_error.Error}')
        if bool(receipt) is True and check_tx_error.Error is False:
            return f'{amount.Ether} ETH was bridged to Hemi via official bridge: {tx.hash.hex()}'
        else:
            return f'{failed_text}! Error: {check_tx_error.ErrDescription}, Tx_hash: {tx.hash.hex()}'

    async def _deposit_erc20_to_hemi(self, token: RawContract, amount: TokenAmount | None = None) -> str:
        if not amount:
            amount = Base.get_erc20_amount_for_bridge(token)
        # amount = TokenAmount(amount=amount, decimals=from_token.decimals)
        from_token = await self.client.contracts.default_token(contract_address=token.address)
        from_token_name = await from_token.functions.symbol().call()

        # print(amount.Wei, amount.decimals)
        # print(await self.client.wallet.balance(token=from_token))

        failed_text = f'Failed to bridge {amount.Ether} {from_token_name} to Hemi via Official Bridge'
        contract = await self.client.contracts.get(contract_address=Contracts.Hemi_Bridge_Sepolia)

        wallet_amount = await self.client.wallet.balance(token=from_token)
        # print(wallet_amount)
        if wallet_amount == 0:
            wallet_amount = random.randint(10000, 100000)
            await self.approve_interface(token_address=token.address,
                                         spender=self.client.account.address,
                                         amount=TokenAmount(amount=wallet_amount))

        if await self.approve_interface(
                token_address=from_token.address,
                spender=contract.address,
                amount=wallet_amount
        ):
            await asyncio.sleep(random.randint(10, 15))
            print(f'approved {from_token_name}')
        else:
            return f'{failed_text} | can not approve'

        to_token = ''
        if from_token == Contracts.Sepolia_USDT:
            to_token = Contracts.Hemi_USDTe
        elif from_token == Contracts.Sepolia_USDC:
            to_token = Contracts.Hemi_USDCe
        elif from_token == Contracts.Sepolia_DAI:
            to_token = Contracts.Hemi_DAI
        else:
            return 'wrong token'

        args = TxArgs(
            _l1Token=f'{from_token.address}',
            _l2Token=f'{to_token.address}',
            _amount=amount.Wei,
            _minGasLimit=200000,
            _extraData=b''
        )

        tx_params = TxParams(
            to=contract.address,
            data=contract.encodeABI('depositERC20', args=args.tuple()),
            value=0
        )

        tx = await self.client.transactions.sign_and_send(tx_params=tx_params)

        receipt = await tx.wait_for_receipt(client=self.client, timeout=500)
        check_tx_error = await Base.check_tx(tx.hash.hex())
        print(f'check_tx_error bridge erc20: {check_tx_error.Error}')
        if bool(receipt) is True and check_tx_error.Error is False:
            return f'{amount.Ether} {from_token_name} stablecoin was bridged to Hemi via official bridge: {tx.hash.hex()}'
        else:
            return f'{failed_text}! Error: {check_tx_error.ErrDescription}, Tx_hash: {tx.hash.hex()}'

    async def bridge_usdc_to_hemi(self) -> str:
        return await self._deposit_erc20_to_hemi(token=Contracts.Sepolia_USDC)

    async def bridge_usdt_to_hemi(self) -> str:
        return await self._deposit_erc20_to_hemi(token=Contracts.Sepolia_USDT)

    async def bridge_dai_to_hemi(self) -> str:
        return await self._deposit_erc20_to_hemi(token=Contracts.Sepolia_DAI)

    async def _faucet(self, token: RawContract, amount: int | None = None):
        if not amount:
            amount = Base.get_stable_faucet_amount()
            amount = 10000
        amount = TokenAmount(amount=amount, decimals=token.decimals)

        contract = await self.client.contracts.get(contract_address=Contracts.Aave_Faucet)
        # get_token = await self.client.contracts.default_token(contract_address=token.address)
        from_token = await self.client.contracts.default_token(contract_address=token.address)
        from_token_name = await from_token.functions.symbol().call()
        failed_text = f'Failed to faucet {amount} {from_token_name} via Aave Faucet'

        args = TxArgs(
            token=from_token.address,
            to=self.client.account.address,
            amount=amount.Wei,
        )

        tx_params = TxParams(
            to=contract.address,
            data=contract.encodeABI('mint', args=args.tuple()),
            value=0
        )

        tx = await self.client.transactions.sign_and_send(tx_params=tx_params)
        receipt = await tx.wait_for_receipt(client=self.client, timeout=500)
        await asyncio.sleep(15)
        check_tx_error = await Base.check_tx(str(tx.hash))
        # print(check_tx_error)
        # print(type(check_tx_error))
        print(f'check_tx_error faucet: {check_tx_error.Error}')
        # print(bool(receipt))
        if bool(receipt) is True and check_tx_error.Error is False:
            return f'{amount.Ether} {from_token_name} was minted via Aave: {tx.hash.hex()}'
        else:
            return f'{failed_text}! Error: {check_tx_error.ErrDescription}, Tx_hash: {tx.hash.hex()}'

    async def faucet_usdc(self) -> str:
        return await self._faucet(token=Contracts.Sepolia_USDC)

    async def faucet_usdt(self) -> str:
        return await self._faucet(token=Contracts.Sepolia_USDT)

    async def faucet_dai(self) -> str:
        return await self._faucet(token=Contracts.Sepolia_DAI)


class Hemi(Base):
    async def create_capsule(self, token: RawContract, amount: int | None = None):
        if not amount:
            amount = Base.get_token_amount_for_capsule()
        from_token = await self.client.contracts.default_token(contract_address=token.address)
        from_token_name = token.address

        failed_text = f'Failed to create capsule {amount} {from_token_name} via Capsule'

        contract = await self.client.contracts.get(contract_address=Contracts.Hemi_Capsule)

        # if await self.approve_interface(
        #         token_address=from_token.address,
        #         spender=contract.address,
        #         amount=await self.client.wallet.balance(token=from_token)
        # ):
        #     await asyncio.sleep(random.randint(10, 15))
        #     print(f'approved {from_token_name}')
        # else:
        #     return f'{failed_text} | can not approve'

        '''
            shipPackage((bytes[],string) packageContent_, 
            (bytes32,uint64,address,uint256) securityInfo_, 
            address receiver_)  
        '''
        '''
                               '      0x0000000000000000000000000000000000000000000000000000000000000001'
                                     '0000000000000000000000003adf21a6cbc9ce6d5a3ea401e7bae9499d39129800'
                                     '0000000000000000000000000000000000000000000000000000000000000000000'
                                     '00000000000000000000000000000000000000000000000000005f5e100',
                               '''
        # args = TxArgs(
        #     packageContent_=TxArgs
        #     (bytes=[(
        #                 f'0x{"1".zfill(64)}'
        #                 f'{str(from_token.address)[2:].zfill(64)}'
        #                 f'{"".zfill(64)}'
        #                 f'{str(amount.Wei).zfill(64)}'
        #             ).encode('utf-8')],
        #      infuraLink=
        #      'https://capsulepackaging.infura-ipfs.io/ipfs/QmYQ4roMMbVx9vUM9suYm5GCdK1gsANhGANqSVyPb3GEER'
        #      ).tuple(),
        #     securityInfo_=
        #     TxArgs(
        #         bytes32=b'0xe1de53ee25c3efbf8cfb0ba5b12df7650ec5249de5933249507f0614934ca202',
        #         uint64=0,
        #         address='0x0000000000000000000000000000000000000000',
        #         uint256=0
        #     ).tuple(),
        #     address=f'{self.client.account.address}'
        # )
        packageContent_ = [
            TxArgs(bytes=(f'0x'
                          f'{"1".zfill(64)}'
                          f'{str(from_token.address)[2:].zfill(64)}'
                          f'{"".zfill(64)}'
                          f'{str(amount.Wei).zfill(64)}').encode('utf-8')).list(),
            'https://capsulepackaging.infura-ipfs.io/ipfs/QmYQ4roMMbVx9vUM9suYm5GCdK1gsANhGANqSVyPb3GEER'
        ]

        securityInfo_ = [
            b'0x0000000000000000000000000000000000000000000000000000000000000000',
            0,
            '0x0000000000000000000000000000000000000000',
            0
        ]

        args = TxArgs(
            packageContent_=packageContent_,
            securityInfo_=securityInfo_,
            address=f'{self.client.account.address}'
        )

        tx_params = TxParams(
            to=contract.address,
            data=contract.encodeABI('shipPackage', args=args.tuple()),
            value=0.001
        )

        tx = await self.client.transactions.sign_and_send(tx_params=tx_params)
        receipt = await tx.wait_for_receipt(client=self.client, timeout=300)
        check_tx_error = await Base.check_tx(tx.hash)
        if receipt is True and check_tx_error is False:
            return f'{amount.Ether} {from_token_name} was created capsule: {tx.hash.hex()}'
        else:
            return f'{failed_text}! Error: {check_tx_error.ErrDescription}, Tx_hash: {tx.hash.hex()}'
