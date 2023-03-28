
from util.logs import create_logger
import sys
import requests
import openai
import traceback
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import tiktoken


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
current_key_index = 0


class ChatGPT:
    OPENAI_API_KEY = None
    CHATGPT_MODEL = None

    def __init__(self, session, config) -> None:
        """
        session: {'id': str, 'msg': list, 'send_voice': bool, 'new_bing': bool}
        config: config.json
        """
        self.config = config
        self.session = session
        self.logger = create_logger(__class__.__name__)

        if not ChatGPT.OPENAI_API_KEY:
            ChatGPT.OPENAI_API_KEY = self.config['openai']['api_key']
        if not ChatGPT.CHATGPT_MODEL:
            ChatGPT.CHATGPT_MODEL = self.config['chatgpt']['model']

    # 重置会话，但是保留人格
    def reset_chat(self):
       del self.session['msg'][1:len(self.session['msg'])]

    # 聊天 
    def chat(self, msg: str):
        try:
            if msg == '查询余额':
                balances = [
                    f"Key_{i+1} 余额: {round(self.__get_credit_summary(i), 2)}美元" for i in range(len(ChatGPT.OPENAI_API_KEY))]
                text = "\n".join(balances)
                return text
            if msg.startswith('/img'):
                pic_path = self.__generate_img(msg.replace('/img', ''))
                self.logger.info(f'开始直接生成图像: {pic_path}')
                return "![](" + pic_path + ")"

            # 设置本次对话内容
            self.session['msg'].append({"role": "user", "content": msg})
            # 设置时间
            self.session['msg'][1] = {"role": "system",
                                      "content": "current time is:" + get_bj_time()}
            # 检查是否超过tokens限制
            while self.__calculate_num_tokens() > ChatGPT.CHATGPT_MAX_TOKENS:
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
        openai.api_key = self.config['openai']['api_key'][current_key_index]
        response = openai.Image.create(
            prompt=desc,
            n=1,
            size=self.config['openai']['img_size']
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
        index = index or current_key_index
        res = requests.get(CREDIT_GRANTS_URL, headers={
            "Authorization": f"Bearer " + self.config['openai']['api_key'][index]
        }, timeout=60).json()
        self.logger.info(f"credit summary: {res}")
        return res['total_available'] if index else res

    # 向openai的api发送请求
    def __asking_gpt(self):
        OPENAI_API_KEY = self.config['openai']['api_key']
        CHATGPT_MODEL = self.config['chatgpt']['model']
        max_length = len(OPENAI_API_KEY) - 1
        try:
            if not OPENAI_API_KEY:
                return "请设置Api Key"
            else:
                if current_key_index > max_length:
                    current_key_index = 0
                    return "全部Key均已达到速率限制,请等待一分钟后再尝试"
                openai.api_key = OPENAI_API_KEY[current_key_index]

            resp = openai.ChatCompletion.create(
                model=CHATGPT_MODEL,
                messages=self.session['msg']
            )
            resp = resp['choices'][0]['message']['content']
        except openai.OpenAIError as e:
            resp = self.__handle_error(e)
        return resp

    # 处理error
    def __handle_error(self, error):
        if "Rate limit reached" in str(error) and current_key_index < len(ChatGPT.OPENAI_API_KEY) - 1:
            # 切换key
            current_key_index += 1
            self.logger.error(
                f"速率限制，尝试切换key：{ChatGPT.OPENAI_API_KEY[current_key_index]}")
            return self.__asking_gpt()
        elif "Your access was terminated" in str(error) and current_key_index < len(ChatGPT.OPENAI_API_KEY) - 1:
            self.logger.error(
                f"请及时确认该Key: {ChatGPT.OPENAI_API_KEY[current_key_index]}是否正常，若异常，请移除")
            # 切换key
            current_key_index += 1
            self.logger.error(
                f"访问被阻止，尝试切换key：{ChatGPT.OPENAI_API_KEY[current_key_index]}")
            return self.__asking_gpt()
        else:
            self.logger.error(f'openai 接口报错: {error}')
            return str(error)

    # 上报日志
    def __up_log(self, e: Exception):
        self.logger.error(f"New Bing接口报错: {str(e)}")
        self.logger.error(f"traceback: {traceback.format_exc()}")
        return "New Bing接口报错: " + str(e)


# 创建一个chatgpt实例
def create_chatgpt_instance(session_id: str, config: any) -> ChatGPT:
    session = deepcopy(session_config)
    session['id'] = session_id
    session['msg'].append(
        {"role": "system", "content": "current time is:" + get_bj_time()}
    )
    return ChatGPT(session, config)

#获取当前APIKeyIndex
def get_current_api_key_index():
    return current_key_index

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
