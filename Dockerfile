FROM python:3.12-slim

RUN pip config set global.extra-index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip config set global.index-url http://nexus.tech.skytech.io/repository/pypi-public/simple/ \
    && pip config set global.trusted-host "nexus.tech.skytech.io pypi.tuna.tsinghua.edu.cn"

# 设置工作目录
WORKDIR ./app

# 将文件全部放进指定目录
ADD . .

# 升级pip并安装依赖
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip cache purge

EXPOSE 7777

CMD ["python", "service.py"]