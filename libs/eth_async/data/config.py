import os
import sys
from pathlib import Path


from dotenv import load_dotenv
# from data.models import Settings
# from data.models import SETTINGS_FILE
# from libs.eth_async.utils.files import read_json

load_dotenv()

# settings = Settings()


# # json_data = os.open('files/settings.json', flags=os.O_NONBLOCK)
# if getattr(sys, 'frozen', False):
#     ROOT_DIR = Path(sys.executable).parent.absolute()
# else:
#     ROOT_DIR = Path(__file__).parent.parent.absolute()
#
# FILES_DIR = os.path.join(ROOT_DIR, 'files')
#
# SETTINGS_FILE = os.path.join(FILES_DIR, 'settings.json')
# json_data = read_json(path=SETTINGS_FILE)
# # etherscan_api_key: str = json_data['etherscan_api_key']
# ETHERSCAN_API_KEY = json_data['etherscan_api_key']

# json_data = read_json('./files/settings.json')
# ETHERSCAN_API_KEY = os.open('files/settings.json', flags=os.O_NONBLOCK)


# ETHERSCAN_API_KEY = settings.etherscan_api_key
ETHERSCAN_API_KEY = str(os.getenv('ETHERSCAN_API_KEY'))
ARBISCAN_API_KEY = str(os.getenv('ARBISCAN_API_KEY'))
OPTIMISTIC_API_KEY = str(os.getenv('OPTIMISTIC_API_KEY'))

# ETHEREUM_API_KEY = str(os.getenv('ETHEREUM_API_KEY'))
# ARBITRUM_API_KEY = str(os.getenv('ARBITRUM_API_KEY'))
# OPTIMISM_API_KEY = str(os.getenv('OPTIMISM_API_KEY'))
# BSC_API_KEY = str(os.getenv('BSC_API_KEY'))
# POLYGON_API_KEY = str(os.getenv('POLYGON_API_KEY'))
# AVALANCHE_API_KEY = str(os.getenv('AVALANCHE_API_KEY'))
# MOONBEAM_API_KEY = str(os.getenv('MOONBEAM_API_KEY'))
# FANTOM_API_KEY = str(os.getenv('FANTOM_API_KEY'))
# CELO_API_KEY = str(os.getenv('CELO_API_KEY'))
# GNOSIS_API_KEY = str(os.getenv('GNOSIS_API_KEY'))
# HECO_API_KEY = str(os.getenv('HECO_API_KEY'))
# GOERLI_API_KEY = str(os.getenv('GOERLI_API_KEY'))
# SEPOLIA_API_KEY = str(os.getenv('SEPOLIA_API_KEY'))
# LINEA_API_KEY = str(os.getenv('LINEA_API_KEY'))
# BASE_API_KEY = str(os.getenv('BASE_API_KEY'))
