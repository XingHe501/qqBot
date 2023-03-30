import asyncio
import config.export_class
from config.config import config
from flask import request, Flask
from stable_diffusion import get_stable_diffusion_img
from message_sender import MessageSender
from bot.new_bing import create_new_bing_instance
from bot.gpt import create_chatgpt_instance
from util.logs import logger
import json
import requests
import openai

# 全局的所有session都在这里
global_sessions = {}
# OpenAI API Base
openai.api_base = config.OPENAI.API_BASE


class ChatSession:
    def __init__(self, session) -> None:
        """
        session: {'id': str, 'msg':"", 'send_voice':bool, 'new_bing':bool}
        """
        self.session = session
        self.chatgpt = create_chatgpt_instance(session['id'])
        self.newbing = None

    async def request(self, msg: str):
        """
          向GPT or NewBing发送请求
        """
        msg = msg.strip()
        if msg in config.config_manager:
            if msg == '重置会话':
                if self.session['new_bing']:
                    self.newbing.reset_chat()
                else:
                    self.chatgpt.reset_chat()
            elif msg == '/gpt':
                self.session['new_bing'] = False
            elif msg == '/newbing':
                self.session['new_bing'] = True
                self.__check_newbing()
            elif msg == '语音开启':
                self.session['send_voice'] = True
            elif msg == '语音关闭':
                self.session['send_voice'] = False
            return config.get_config(msg)
        if msg.startswith("newbing ") or self.session['new_bing']:
            return await self.request_newbing(msg.replace('newbing ', ''))
        return await self.request_chatgpt(msg.replace('chat ', ''))

    def request_chatgpt(self, msg):
        return self.chatgpt.chat(msg)

    def generate_image(self, msg):
        return self.chatgpt.generate_img(msg)

    def request_newbing(self, msg):
        self.__check_newbing()
        return self.newbing.chat(msg)

    def __check_newbing(self):
        if self.newbing == None:
            self.newbing = create_new_bing_instance(self.session['id'])


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
    print(config.OPENAI.get_curren_key())
    res = requests.get(url, headers={
        "Authorization": f"Bearer " + config.OPENAI.get_curren_key()
    }, timeout=60).json()
    return res


# qq消息上报接口，qq机器人监听到的消息内容将被上报到这里
@server.route('/', methods=["POST"])
def get_message():
    request_data = request.get_json()
    if request_data.get('post_type') == 'meta_event' and request_data.get('meta_event_type') == 'heartbeat':
        # 心跳包，直接返回
        return "ok"

    logger.info(f"request data: {request_data}")
    message_type = request_data.get('message_type')
    post_type = request_data.get('post_type')

    # 处理私聊消息
    if message_type == 'private':
        uid = request_data.get('sender').get('user_id')
        message = request_data.get('raw_message')
        logger.info(f"收到私聊消息：\n{message}")
        process_message(message, 'private', uid, None)

    # 处理群消息
    elif message_type == 'group':
        QQ_NO = config.QQ_BOT.QQ_NO
        gid = request_data.get('group_id')
        uid = request_data.get('sender').get('user_id')
        message = str(request_data.get('raw_message'))
        # 判断是否被@，如果被@才进行回复
        if f'[CQ:at,qq={QQ_NO}]' in message:
            message = message.replace(f'[CQ:at,qq={QQ_NO}]', '')
            logger.info(f"收到群聊消息：\n{message}")
            process_message(message, 'group', uid, gid)
        elif message.startswith("chat ") or message.startswith("newbing "):
            # 向newbing or chat 发消息
            process_message(message, 'group', uid, gid)

        # 处理请求消息
    elif post_type == 'request':
        QQ_AUTO_CONFIRM = config.QQ_BOT.AUTO_CONFIRM
        QQ_ADMIN_QQ = config.QQ_BOT.ADMIN_QQ
        request_type = request_data.get('request_type')
        uid = request_data.get('user_id')
        flag = request_data.get('flag')
        comment = request_data.get('comment')
        logger.info(f"收到请求消息：\n{request_data}")
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
            sub_type = request_data.get('sub_type')
            gid = request_data.get('group_id')
            logger.info(f"收到群请求，请求类型：{sub_type}，群号：{gid}")
            # # 处理加群请求
            # if sub_type == 'add':
            #     logger.info('收到加群请求，不进行处理')
            # 处理邀请入群请求
            if sub_type == 'invite':
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
    ms = MessageSender()
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
        send_voice = chatSession.session['send_voice']
        msg_text = asyncio.run(chatSession.request(message))
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
    })
    global_sessions[session_id] = session
    return session


# 处理好友请求
def set_friend_add_request(flag, approve):
    try:
        requests.post(url=config.QQ_BOT.CQHTTP_URL + "/set_friend_add_request",
                      params={'flag': flag, 'approve': approve})
        logger.info("处理好友申请成功")
    except:
        logger.info("处理好友申请失败")


# 处理邀请加群请求
def set_group_invite_request(flag, approve):
    try:
        requests.post(url=config.QQ_BOT.CQHTTP_URL + "/set_group_add_request",
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
    }, config.REPLICATE.API_TOKEN)
    return res[0]


if __name__ == '__main__':
    server.run(port=5701, host='0.0.0.0', use_reloader=False)
