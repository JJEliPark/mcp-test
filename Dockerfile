# Python 3.10 슬림 이미지를 사용합니다.
FROM python:3.10-slim

# 작업 디렉터리를 설정합니다.
WORKDIR /app

# 시스템 라이브러리 업데이트 및 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 종속성 파일을 복사하고 설치합니다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드를 복사합니다.
COPY search_mcp.py .

# 포트 8000번 노출
EXPOSE 8000

# FastMCP가 내장 uvicorn 서버를 사용하므로 직접 Python으로 실행합니다.
CMD python search_mcp.py
