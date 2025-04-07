FROM python:3.9-slim

COPY deploy.py /app/deploy.py

RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple requests pyyaml

WORKDIR /app

CMD ["python", "/app/deploy.py"]