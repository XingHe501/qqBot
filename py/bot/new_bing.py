from util.logs import logger
import traceback
import asyncio
from EdgeGPT import ConversationStyle, Chatbot
from config.config import config


class NewBing:
    # 一个session 对应一个 newbing

    def __init__(self, session: dict):
        """
        session: {'id':str, 'bot':ChatBot, 'new_bing':bool,'send_voice':bool}
        """
        self.session = session
        self.bot: Chatbot = session['bot']  # ChatBot

    # 重置会话
    def reset_chat(self):
        self.bot.reset()

    async def chat(self, msg: str):
        try:
            logger.info(f"问: {msg}")
            replay = self.__ask_newbing(msg)
            logger.info(f"New Bing 返回: {replay}")
            return replay
        except Exception as e:
            return self.__up_log(e)

    # 和New Bing交互的方法
    async def __ask_newbing(self, msg):
        style_map = {
            "h3relaxedimg": ConversationStyle.creative,
            "galileo": ConversationStyle.balanced
        }
        try:
            conversation_style = style_map.get(
                config.NEW_BING.CONVERSATION_STYLE, ConversationStyle.precise)
            obj = await self.bot.ask(prompt=msg, conversation_style=conversation_style)
            logger.info(f"NewBing 接口返回:{obj} ")
            return obj["item"]["messages"][1]["adaptiveCards"][0]["body"][0]["text"]
        except Exception as e:
            return self.__up_log(e)

    # 上报日志
    def __up_log(self, e: Exception):
        logger.error(f"New Bing接口报错: {str(e)}")
        logger.error(f"traceback: {traceback.format_exc()}")
        return "New Bing接口报错: " + str(e)


# 根据session_id 返回 一个NewBing对象
def create_new_bing_instance(session_id: str) -> NewBing:
    session = {'id': session_id, 'bot': Chatbot(
        cookiePath=config.NEW_BING.COOKIE_PATH)}
    return NewBing(session)


if __name__ == "__main__":
    newBing = create_new_bing_instance("123")
    print(newBing.chat("你好"))
