import logging.handlers

# 创建logger对象
def create_logger(name, config):
    """
        name: logger Name
        config: config.json
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 创建文件处理器并设置日志级别为 INFO
    info_handler = logging.handlers.RotatingFileHandler(
        config['info.log'], maxBytes=1024*1024, backupCount=3, encoding='utf-8')
    info_handler.setLevel(logging.INFO)

    # 创建文件处理器并设置日志级别为 CRITICAL
    error_handler = logging.handlers.RotatingFileHandler(
        config['error.log'], maxBytes=1024*1024, backupCount=3, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    # 将格式化器添加到处理器中
    info_handler.setFormatter(formatter)
    error_handler.setFormatter(formatter)

    # 将处理器添加到日志记录器中
    logger.addHandler(info_handler)
    logger.addHandler(error_handler)
    return logger