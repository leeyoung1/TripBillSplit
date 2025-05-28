FROM python:3.9-slim

WORKDIR /app

# 设置Python环境
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# 安装系统依赖
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE $PORT

# 启动命令
CMD gunicorn main:app -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:$PORT --timeout 120 