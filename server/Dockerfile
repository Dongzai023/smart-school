FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

EXPOSE 8000

# 启动命令：先等待数据库就绪，再初始化数据库，最后启动服务
CMD ["sh", "-c", "python wait_for_db.py && python upgrade_db.py && python upgrade_db_rules.py && python init_db.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
