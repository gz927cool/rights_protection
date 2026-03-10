FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 仅依赖变化时重新安装
COPY requirements.txt requirements.txt

# 配置 pip 源并安装依赖
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple \
    && pip config set global.trusted-host "mirrors.aliyun.com" \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple -r requirements.txt

# 拷贝项目
COPY . /app

# 暴露 API 端口
EXPOSE 7777

# 启动 FastAPI 服务
CMD ["python", "service.py"]
