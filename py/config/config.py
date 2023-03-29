import json
from pathlib import Path
CONFIG_FILE = "./config/config.json"


class OPENAI: 
	def __init__(self, config):
		"""		config: config['OPENAI']
		"""
		self.API_KEY: list = config['api_key']
		self.IMG_SIZE: str = config['img_size']
		self.API_BASE: str = config['api_base']
		self.CURRENT_KEY_INDEX:int = 0

	def get_curren_key(self, index:int = None):
		if index:
			return self.API_KEY[index]
		return self.CURRENT_KEY_INDEX

	def add_key_index(self):
		self.CURRENT_KEY_INDEX += 1

	def reset_key_index(self):
		self.CURRENT_KEY_INDEX = 0



class CHATGPT: 
	def __init__(self, config):
		"""		config: config['CHATGPT']
		"""
		self.MODEL: str = config['model']
		self.TEMPERATURE: float = config['temperature']
		self.MAX_TOKENS: int = config['max_tokens']
		self.TOP_P: int = config['top_p']
		self.ECHO: bool = config['echo']
		self.PRESENCE_PENALTY: int = config['presence_penalty']
		self.FREQUENCY_PENALTY: int = config['frequency_penalty']
		self.PRESET: str = config['preset']


class NEW_BING: 
	def __init__(self, config):
		"""		config: config['NEW_BING']
		"""
		self.COOKIE_PATH: str = config['cookie_path']
		self.CONVERSATION_STYLE: str = config['conversation_style']


class QQ_BOT: 
	def __init__(self, config):
		"""		config: config['QQ_BOT']
		"""
		self.QQ_NO: str = config['qq_no']
		self.CQHTTP_URL: str = config['cqhttp_url']
		self.MAX_LENGTH: int = config['max_length']
		self.IMAGE_PATH: str = config['image_path']
		self.VOICE_PATH: str = config['voice_path']
		self.VOICE: str = config['voice']
		self.AUTO_CONFIRM: bool = config['auto_confirm']
		self.ADMIN_QQ: str = config['admin_qq']


class TEXT_TO_IMAGE: 
	def __init__(self, config):
		"""		config: config['TEXT_TO_IMAGE']
		"""
		self.FONT_SIZE: int = config['font_size']
		self.WIDTH: int = config['width']
		self.FONT_PATH: str = config['font_path']
		self.OFFSET_X: int = config['offset_x']
		self.OFFSET_Y: int = config['offset_y']


class REPLICATE: 
	def __init__(self, config):
		"""		config: config['REPLICATE']
		"""
		self.API_TOKEN: str = config['api_token']


class ConfigManager:
	def __init__(self, config_file):
		config_file = Path(config_file).resolve()
		with open(config_file, "r", encoding="utf-8") as f:
			self.config_manager = json.load(f)
		self.OPENAI = OPENAI(self.config_manager['openai'])
		self.CHATGPT = CHATGPT(self.config_manager['chatgpt'])
		self.NEW_BING = NEW_BING(self.config_manager['new_bing'])
		self.QQ_BOT = QQ_BOT(self.config_manager['qq_bot'])
		self.TEXT_TO_IMAGE = TEXT_TO_IMAGE(self.config_manager['text_to_image'])
		self.REPLICATE = REPLICATE(self.config_manager['replicate'])

	def get_config(self, key):
		return self.config_manager.get(key)

config = ConfigManager(CONFIG_FILE)
