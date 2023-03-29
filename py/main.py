import json
import requests
import openai
import sys

sys.path.append("./util")
sys.path.append("./bot")

from util.logs import create_logger
from bot.gpt import create_chatgpt_instance, get_current_api_key_index
from bot.new_bing import create_new_bing_instance
from message_sender import MessageSender
from stable_diffusion import get_stable_diffusion_img
from flask import request, Flask


with open("./config/config.json", "r", encoding="utf-8") as jsonfile:
    config_data = json.load(jsonfile)
QQ_NO = config_data['qq_bot']['qq_no']
QQ_AUTO_CONFIRM = config_data['qq_bot']['auto_confirm']
QQ_ADMIN_QQ = config_data['qq_bot']['admin_qq']
QQ_CQHTTP_URL = config_data['qq_bot']['cqhttp_url']
REPLICATE_API_TOKEN = config_data['replicate']['api_token']

# 全局的所有session都在这里
global_sessions = {}
logger = create_logger("Main")
# OpenAI API Base
openai.api_base = "https://chat-gpt.aurorax.cloud/v1"
# 查询账单url
CREDIT_GRANTS_URL = "https://chat-gpt.aurorax.cloud/dashboard/billing/credit_grants"


class ChatSession:
    def __init__(self, session, config) -> None:
        """
        session: {'id': str, 'msg':"", 'send_voice':bool, 'new_bing':bool}
        """
        self.session = session
        self.chatgpt = create_chatgpt_instance(session['id'], config)
        self.newbing = create_new_bing_instance(session['id'], config)

    def request(self, msg: str):
        """
          向GPT or NewBing发送请求
        """
        msg = msg.strip()
        if msg in config_data:
            if msg == '重置会话':
                if self.session['new_bing']:
                    self.newbing.reset_chat()
                else:
                    self.chatgpt.reset_chat()
            elif msg == '/gpt':
                self.session['new_bing'] = False
            elif msg == '/newbing':
                self.session['new_bing'] = True
            elif msg == '语音开启':
                self.session['send_voice'] = True
            elif msg == '语音关闭':
                self.session['send_voice'] = False
            return self.config[msg]
        return self.newbing.chat(msg) if self.session['new_bing'] else self.chatgpt.chat(msg)

    def request_chatgpt(self, msg):
        return self.chatgpt.chat(msg)

    def generate_image(self, msg):
        return self.chatgpt.generate_img(msg)


# 创建一个服务，把当前这个python文件当做一个服务
server = Flask(__name__)


# 测试接口，可以测试本代码是否正常启动
@server.route('/', methods=["GET"])
def index():
    return f"It's Ok<br/>"


# 测试接口，可以用来测试与ChatGPT的交互是否正常，用来排查问题
@server.route('/chat', methods=["POST"])
def chatapi():
    requestJson = request.get_data()
    if requestJson is None or requestJson == "" or requestJson == {}:
        resu = {'code': 1, 'msg': '请求内容不能为空'}
        return json.dumps(resu, ensure_ascii=False)
    data = json.loads(requestJson)
    if data.get('id') is None or data['id'] == "":
        resu = {'code': 1, 'msg': '会话id不能为空'}
        return json.dumps(resu, ensure_ascii=False)
    print(data)
    try:
        s = get_chat_session(data['id'])
        msg = s.request_chatgpt(data['msg'])
        if '查询余额' == data['msg'].strip():
            msg = msg.replace('\n', '<br/>')
        resu = {'code': 0, 'data': msg, 'id': data['id']}
        return json.dumps(resu, ensure_ascii=False)
    except Exception as error:
        print("接口报错")
        resu = {'code': 1, 'msg': '请求异常: ' + str(error)}
        return json.dumps(resu, ensure_ascii=False)


# 获取账号余额接口
@server.route('/credit_summary', methods=["GET"])
def credit_summary():
    url = "https://chat-gpt.aurorax.cloud/dashboard/billing/credit_grants"
    res = requests.get(url, headers={
        "Authorization": f"Bearer " + config_data['openai']['api_key'][get_current_api_key_index()]
    }, timeout=60).json()
    return res


# qq消息上报接口，qq机器人监听到的消息内容将被上报到这里
@server.route('/', methods=["POST"])
def get_message():
    data = request.get_json()

    # 处理私聊消息
    if data['message_type'] == 'private':
        uid = data['sender']['user_id']
        message = data['raw_message']
        logger.info(f"收到私聊消息：\n{message}")
        process_message(message, 'private', uid, None)

    # 处理群消息
    elif data['message_type'] == 'group':
        gid = data['group_id']
        uid = data['sender']['user_id']
        message = data['raw_message']
        # 判断是否被@，如果被@才进行回复
        if f'[CQ:at,qq={QQ_NO}]' in message:
            message = message.replace(f'[CQ:at,qq={QQ_NO}]', '')
            logger.info(f"收到群聊消息：\n{message}")
            process_message(message, 'group', uid, gid)

        # 处理请求消息
    elif data['post_type'] == 'request':
        request_type = data['request_type']
        uid = data['user_id']
        flag = data['flag']
        comment = data.get('comment', '')
        logger.info(f"收到请求消息：\n{data}")
        # 处理好友请求
        if request_type == 'friend':
            logger.info(f"收到好友请求，请求者：{uid}，验证信息：{comment}")
            # 自动通过好友请求
            if QQ_AUTO_CONFIRM or str(uid) == QQ_ADMIN_QQ:
                set_friend_add_request(flag, 'true')
            else:
                logger.info('未配置自动通过好友请求或请求者非管理员，拒绝好友请求')
                set_friend_add_request(flag, 'false')

        # 处理群请求
        elif request_type == 'group':
            sub_type = data['sub_type']
            gid = data['group_id']
            logger.info(f"收到群请求，请求类型：{sub_type}，群号：{gid}")
            # 处理加群请求
            if sub_type == 'add':
                logger.info('收到加群请求，不进行处理')
            # 处理邀请入群请求
            elif sub_type == 'invite':
                # 自动通过入群邀请
                if QQ_AUTO_CONFIRM or uid == QQ_ADMIN_QQ:
                    set_group_invite_request(flag, 'true')
                else:
                    logger.info('未配置自动通过入群邀请或请求者非管理员，拒绝入群邀请')
                    set_group_invite_request(flag, 'false')
    return "ok"


# GPT重置会话接口, 直接用GPT逻辑
@server.route('/reset_chat', methods=['post'])
def reset_chat():
    requestJson = request.get_data()
    if requestJson is None or requestJson == "" or requestJson == {}:
        resu = {'code': 1, 'msg': '请求内容不能为空'}
        return json.dumps(resu, ensure_ascii=False)
    data = json.loads(requestJson)
    if data['id'] is None or data['id'] == "":
        resu = {'code': 1, 'msg': '会话id不能为空'}
        return json.dumps(resu, ensure_ascii=False)
    # 获得对话session
    session = get_chat_session(data['id'])
    # 清除对话内容但保留人设
    session.chatgpt.reset_chat()
    resu = {'code': 0, 'msg': '重置成功'}
    return json.dumps(resu, ensure_ascii=False)


# 处理消息包括群组消息和私聊消息
def process_message(message, chat_type, uid=None, gid=None):
    ms = MessageSender(config_data)
    if chat_type == 'private':
        chatSession = get_chat_session(uid, chat_type)
        send_message = ms.send_private_message
    elif chat_type == 'group':
        chatSession = get_chat_session(gid, chat_type)
        send_message = ms.send_group_message
    else:
        raise ValueError("Unknown chat_type: {}".format(chat_type))

    msg_text = ''
    send_voice = None
    pic_path = None

    message = str(message).strip()
    if message.startswith('生成图像'):
        message = message.replace('生成图像', '')
        msg_text = chatSession.request_chatgpt(message)  # 将消息转发给ChatGPT处理
        # 将ChatGPT的描述转换为图画
        logger.info('开始生成图像')
        pic_path = chatSession.generate_image(msg_text)
    elif message.startswith('直接生成图像'):
        message = message.replace('直接生成图像', '')
        logger.info('开始直接生成图像')
        pic_path = chatSession.generate_image()
    elif message.startswith('/sd'):
        logger.info("开始stable-diffusion生成")
        try:
            pic_path = sd_img(message.replace("/sd", "").strip())
        except Exception as e:
            errorMsgText = "stable-diffusion 接口报错: {}".format(str(e))
            logger.error(errorMsgText)
            send_message(gid=gid, uid=uid, msg_text=errorMsgText) if chat_type == 'group' else send_message(
                uid=uid, msg=errorMsgText)
        logger.info("stable-diffusion 生成图像: {}".format(pic_path))
    else:
        # 下面你可以执行更多逻辑，这里只演示与ChatGPT对话
        # 获得对话session
        send_voice = chatSession.session['send_voice']
        msg_text = chatSession.request(message)
    send_message(gid, uid, msg_text, send_voice, pic_path) if chat_type == 'group' else send_message(
        uid, msg_text, send_voice, pic_path)


# 获取对话session
def get_chat_session(session_id, chat_type=None) -> ChatSession:
    """
        Get a ChatSession object for the given session ID.
        If the session ID doesn't exist in global_sessions, create a new ChatSession object and add it to global_sessions.
    """
    id_prefix = 'P' if chat_type == 'private' else 'G'
    session_id = id_prefix + str(session_id)
    # Check if the session already exists in global_sessions
    if session_id in global_sessions:
        return global_sessions[session_id]

    # If the session doesn't exist, create a new ChatSession object and add it to global_sessions
    # The default is use GPT
    session = ChatSession({
        'id': session_id,
        'msg': "",
        'send_voice': False,
        'new_bing': False
    }, config_data)
    global_sessions[session_id] = session
    return session


# 处理好友请求
def set_friend_add_request(flag, approve):
    try:
        requests.post(url=QQ_CQHTTP_URL + "/set_friend_add_request",
                      params={'flag': flag, 'approve': approve})
        logger.info("处理好友申请成功")
    except:
        logger.info("处理好友申请失败")


# 处理邀请加群请求
def set_group_invite_request(flag, approve):
    try:
        requests.post(url=QQ_CQHTTP_URL + "/set_group_add_request",
                      params={'flag': flag, 'sub_type': 'invite', 'approve': approve})
        logger.info("处理群申请成功")
    except:
        logger.info("处理群申请失败")


# sd生成图片,这里只做了正向提示词，其他参数自己加
def sd_img(msg):
    res = get_stable_diffusion_img({
        "prompt": msg,
        "image_dimensions": "768x768",
        "negative_prompt": "",
        "scheduler": "K_EULER"
    }, REPLICATE_API_TOKEN)
    return res[0]


if __name__ == '__main__':
    server.run(port=5701, host='0.0.0.0', use_reloader=False)
