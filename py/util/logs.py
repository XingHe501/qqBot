import logging
import logging.handlers
from config.config import config


# 创建logger对象
def create_logger():
    # 创建Logger对象
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] @%(module)s:%(funcName)s:%(lineno)d  %(message)s')

    # 创建info文件处理器
    info_handler = logging.handlers.RotatingFileHandler(
        filename=config.get_config('info.log'), maxBytes=1024*1024, backupCount=3, encoding='utf-8')
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)

    # 创建error文件处理器
    error_handler = logging.handlers.RotatingFileHandler(
        filename=config.get_config('error.log'), maxBytes=1024*1024, backupCount=3, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # 创建屏幕输出处理器
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    # 添加处理器到Logger对象
    logger.addHandler(info_handler)
    logger.addHandler(error_handler)
    logger.addHandler(stream_handler)

    return logger


if __name__ == "__main__":
    log = create_logger()
    msg = "!23"
    log.info(f"msg:{msg}")
    log.error(f"发生错误： Error")
