from util.logs import create_logger
import traceback
import json
import asyncio
from EdgeGPT import ConversationStyle, Chatbot


# from util.logs import create_logger

class NewBing:
    # 一个session 对应一个 newbing

    def __init__(self, session: dict, config: str):
        """
        session: {'id':str, 'bot':ChatBot, 'new_bing':bool,'send_voice':bool}
        config: config.json
        """
        self.config = config
        self.session = session
        self.bot = session['bot']  # ChatBot
        self.logger = create_logger(__class__.__name__, config)

    # 重置会话
    def reset_chat(self):
        self.bot.reset()

    def chat(self, msg: str):
        try:
            self.logger.info(f"问: {msg}")
            replay = asyncio.run(self.__ask_newbing(msg))
            self.logger.info(f"New Bing 返回: {replay}")
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
                self.config['conversation_style'], ConversationStyle.precise)
            obj = await self.bot.ask(prompt=msg, conversation_style=conversation_style)
            self.logger.info(f"NewBing 接口返回:{obj} ")
            return obj["item"]["messages"][1]["adaptiveCards"][0]["body"][0]["text"]
        except Exception as e:
            return self.__up_log(e)

    # 上报日志
    def __up_log(self, e: Exception):
        self.logger.error(f"New Bing接口报错: {str(e)}")
        self.logger.error(f"traceback: {traceback.format_exc()}")
        return "New Bing接口报错: " + str(e)


# 根据session_id 返回 一个NewBing对象
def create_new_bing_instance(session_id: str, config: any) -> NewBing:
    session = {'id': session_id, 'bot': Chatbot(
        cookiePath=config['new_bing']['cookie_path'])}
    return NewBing(session, config)


if __name__ == "__main__":
    config_data = None
    with open("../config/config.json", "r", encoding="utf-8") as jsonfile:
        config_data = json.load(jsonfile)
    newBing = create_new_bing_instance("123", config_data)
    print(newBing.chat("你好"))
