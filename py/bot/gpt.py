
from util.logs import create_logger
import sys
import requests
import openai
import traceback
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import tiktoken
from config.config import config


session_config = {
    'msg': [
        {"role": "system", "content": "You are a helpful assistant."}
    ],
    'send_voice': False,
    'new_bing': False
}
# 查询账单url
CREDIT_GRANTS_URL = "https://chat-gpt.aurorax.cloud/dashboard/billing/credit_grants"
# 当前API Key的索引
CURRENT_KEY_INDEX = 0


class ChatGPT:
    def __init__(self, session) -> None:
        """
        session: {'id': str, 'msg': list, 'send_voice': bool, 'new_bing': bool}
        """
        self.session = session
        self.logger = create_logger()

    # 重置会话，但是保留人格
    def reset_chat(self):
       del self.session['msg'][1:len(self.session['msg'])]

    # 聊天 
    def chat(self, msg: str):
        msg = msg.strip()
        try:
            if msg == '查询余额':
                balances = [
                    f"Key_{i+1} 余额($): {self.__get_credit_summary(i)}美元" for i in range(len(config.OPENAI.API_KEY))]
                text = "\n".join(balances)
                return text
            if msg.startswith('/img'):
                pic_path = self.generate_img(msg.replace('/img', ''))
                self.logger.info(f'开始直接生成图像: {pic_path}')
                return "![](" + pic_path + ")"

            # 设置本次对话内容
            self.session['msg'].append({"role": "user", "content": msg})
            # 设置时间
            self.session['msg'][1] = {"role": "system",
                                      "content": "current time is:" + get_bj_time()}
            # 检查是否超过tokens限制
            while self.__calculate_num_tokens() > config.CHATGPT.MAX_TOKENS:
                # 当超过记忆保存最大量时，清理一条
                del self.session['msg'][2:3]
            # 与ChatGPT交互获得对话内容
            message = self.__asking_gpt()
            # 记录上下文
            self.session['msg'].append({"role": "assistant", "content": message})
            self.logger.info(f"ChatGPT返回内容: {message}")
            return message
        except Exception as error:
            self.__up_log(error)

    # 使用openai生成图片
    def generate_img(self, desc: str) -> str:
        openai.api_key = config.OPENAI.get_curren_key()
        response = openai.Image.create(
            prompt=desc,
            n=1,
            size=config.OPENAI.IMG_SIZE
        )
        image_url = response['data'][0]['url']
        self.logger.info(f"图像已生成：{image_url}")
        return image_url

    # 计算消息使用的tokens数量
    def __calculate_num_tokens(self, model="gpt-3.5-turbo"):
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        if model == "gpt-3.5-turbo":
            num_tokens = 0
            for message in self.session['msg']:
                num_tokens += 4
                for key, value in message.items():
                    num_tokens += len(encoding.encode(value))
                    if key == "name":  # 如果name字段存在，role字段会被忽略
                        num_tokens += -1  # role字段是必填项，并且占用1token
            num_tokens += 2
            return num_tokens
        else:
            raise NotImplementedError(f"""当前模型不支持tokens计算: {model}.""")

    # 查询余额
    def __get_credit_summary(self, index=None):
        res = requests.get(CREDIT_GRANTS_URL, headers={
            "Authorization": f"Bearer " + config.OPENAI.get_curren_key(index)
        }, timeout=60).json()
        self.logger.info(f"credit summary: {res}")
        return res.get('total_available', None) or res.get('error').get('message')

    # 向openai的api发送请求
    def __asking_gpt(self):
        max_length = len(config.OPENAI.API_KEY) - 1
        try:
            if not config.OPENAI.API_KEY:
                return "请设置Api Key"
            else:
                if config.OPENAI.CURRENT_KEY_INDEX > max_length:
                    config.OPENAI.reset_key_index()
                    return "全部Key均已达到速率限制,请等待一分钟后再尝试"
                openai.api_key = config.OPENAI.get_curren_key()

            resp = openai.ChatCompletion.create(
                model=config.CHATGPT.MODEL,
                messages=self.session['msg']
            )
            resp = resp['choices'][0]['message']['content']
        except openai.OpenAIError as e:
            resp = self.__handle_error(e)
        return resp

    # 处理error
    def __handle_error(self, error):
        if "Rate limit reached" in str(error) and config.OPENAI.CURRENT_KEY_INDEX < len(config.OPENAI.API_KEY) - 1:
            # 切换key
            config.OPENAI.add_key_index()
            self.logger.error(
                f"速率限制，尝试切换key：{config.OPENAI.get_curren_key()}")
            return self.__asking_gpt()
        elif "Your access was terminated" in str(error) and config.OPENAI.CURRENT_KEY_INDEX < len(config.OPENAI.API_KEY) - 1:
            self.logger.error(
                f"请及时确认该Key: {config.OPENAI.get_curren_key()}是否正常，若异常，请移除")
            # 切换key
            config.OPENAI.add_key_index()
            self.logger.error(
                f"访问被阻止，尝试切换key：{config.OPENAI.get_curren_key()}")
            return self.__asking_gpt()
        else:
            self.logger.error(f'openai 接口报错: {error}')
            return str(error)

    # 上报日志
    def __up_log(self, e: Exception):
        self.logger.error(f"GPT接口报错: {str(e)}")
        self.logger.error(f"traceback: {traceback.format_exc()}")
        return "GPT接口报错: " + str(e)


# 创建一个chatgpt实例
def create_chatgpt_instance(session_id: str) -> ChatGPT:
    session = deepcopy(session_config)
    session['id'] = session_id
    session['msg'].append(
        {"role": "system", "content": "current time is:" + get_bj_time()}
    )
    return ChatGPT(session)

# 获取北京时间
def get_bj_time():
    utc_now = datetime.utcnow().replace(tzinfo=timezone.utc)
    SHA_TZ = timezone(
        timedelta(hours=8),
        name='Asia/Shanghai',
    )
    # 北京时间
    beijing_now = utc_now.astimezone(SHA_TZ)
    fmt = '%Y-%m-%d %H:%M:%S'
    now_fmt = beijing_now.strftime(fmt)
    return now_fmt
