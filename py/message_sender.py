import uuid
import os
import requests
import asyncio
import config.export_class

from config.config import config
from text_to_image import text_to_image
from text_to_speech import gen_speech
from util.logs import logger


class MessageData:
    def __init__(self, url, success_msg) -> None:
        self.url = url
        self.success_mg = success_msg


class MessageSender:
    def __init__(self) -> None:
        self.private = self.__create_message_data(
            "/send_private_msg", "私聊消息发送成功")
        self.group = self.__create_message_data("/send_group_msg", "群消息发送成功")

    def __create_message_data(self, req, msg):
        return MessageData(config.QQ_BOT.CQHTTP_URL + req, msg)

    def __generate_image(self, message):
        """生成图片并返回图片文件名"""
        img = text_to_image(message)
        filename = str(uuid.uuid1()) + ".png"
        filepath = os.path.join(config.QQ_BOT.IMAGE_PATH, filename)
        img.save(filepath)
        logger.info("图片生成完毕: " + filepath)
        return filename

    def __send_message(self, chat_type, params, send_voice=None):
        """发送信息"""
        messageData = self.private if chat_type == 'private' else self.group
        try:
            message = params['message']
            if send_voice:  # 如果开启了语音发送
                voice_path = asyncio.run(
                    gen_speech(message, config.QQ_BOT.VOICE, config.QQ_BOT.VOICE_PATH))
                message = "[CQ:record,file=file://" + voice_path + "]"
            if len(message) >= config.QQ_BOT.MAX_LENGTH and not send_voice:
                pic_path = self.__generate_image(message)
                message = "[CQ:image,file=" + pic_path + "]"
            params['message'] = message
            res = requests.post(url=messageData.url, params=params).json()
            if res["status"] == "ok":
                logger.info(messageData.url)
            else:
                logger.error("消息发送失败，错误信息：" + str(res['wording']))
        except Exception as error:
            logger.error("消息发送失败")
            logger.exception(error)

    def send_private_message(self, uid, msg=None, send_voice=None, pic_path=None):
        message = msg or ""
        if pic_path:
            message = msg + "\n[CQ:image,file=" + pic_path + "]"
        params = {'user_id': int(uid), 'message': message}
        self.__send_message('private', params, send_voice)

    def send_group_message(self, gid, uid, msg=None, send_voice=None, pic_path=None):
        message = msg or ""
        if not send_voice:
            if pic_path:
                message = message + "\n[CQ:image,file=" + pic_path + "]"
            message = str('[CQ:at,qq=%s]\n' % uid) + message  # @发言人
        params = {'group_id': int(gid), 'message': msg}
        self.__send_message('group', params, send_voice)
