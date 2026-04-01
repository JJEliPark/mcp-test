import uvicorn
from fastapi import FastAPI
from starlette.requests import Request
from duckduckgo_search import DDGS
import json
import os
from fastapi.middleware.cors import CORSMiddleware

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

# FastAPI 및 MCP 서버 초기화
app = FastAPI(title="Internet Search MCP (SSE)")

# CORS 설정: Render 등 외부 웹 클라이언트의 접근을 허용합니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인에서의 접근을 허용 (보안 필요 시 도메인 제한 가능)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mcp = Server("search-mcp")

# SSE 전송 계층 초기화: 클라이언트가 메시지를 보낼 엔드포인트를 동일한 "/mcp"로 지정합니다.
sse = SseServerTransport("/mcp")

@mcp.list_tools()
async def handle_list_tools() -> list[Tool]:
    """클라이언트에게 제공할 도구(Tool) 목록을 반환합니다."""
    return [
        Tool(
            name="search_internet",
            description="인터넷 실시간 검색을 통해 최신 정보를 가져옵니다. 광고 법령, 시장 트렌드, 뉴스 등 실시간 조사가 필요한 경우에 사용합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "검색하고자 하는 핵심 키워드나 질문 문장"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "가져올 검색 결과의 개수 (최대 10개, 기본값 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        )
    ]

@mcp.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent]:
    """클라이언트가 도구 실행을 요청했을 때의 로직을 처리합니다."""
    if name != "search_internet":
        raise ValueError(f"Unknown tool: {name}")

    if not arguments or "query" not in arguments:
        raise ValueError("Missing 'query' parameter")

    query = arguments["query"]
    max_results = arguments.get("max_results", 5)

    try:
        # DDGS를 사용하여 검색 수행
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            
            if not results:
                return [TextContent(type="text", text="검색 결과가 없습니다.")]
            
            # 검색 결과를 Markdown 포맷으로 구성
            formatted_text = f"'{query}' 검색 결과:\n\n"
            for r in results:
                title = r.get("title", "No Title")
                body = r.get("body", "No Description")
                href = r.get("href", "")
                formatted_text += f"### {title}\n"
                formatted_text += f"{body}\n"
                formatted_text += f"**URL**: {href}\n\n"
                
            return [TextContent(type="text", text=formatted_text)]
            
    except Exception as e:
        return [TextContent(type="text", text=f"검색 중 오류 발생: {str(e)}")]

# Streamable HTTP / MCP 단일 엔드포인트 설정
@app.api_route("/mcp", methods=["GET", "POST"])
async def handle_mcp(request: Request):
    """
    단일 /mcp 엔드포인트에서 GET(SSE 스트림)과 POST(메시지 전송)를 모두 처리합니다.
    (March 2025 Streamable HTTP 표준 적용)
    """
    if request.method == "GET":
        # 서버에서 클라이언트로의 이벤트 스트림(SSE) 개방
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as (read_stream, write_stream):
            await mcp.run(
                read_stream,
                write_stream,
                mcp.create_initialization_options()
            )
    elif request.method == "POST":
        # 클라이언트에서 서버로의 JSON-RPC 메시지 처리
        await sse.handle_post_message(request.scope, request.receive, request._send)


if __name__ == "__main__":
    # Render 등 클라우드 환경에서는 'PORT' 환경 변수를 사용합니다.
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting MCP Server with SSE on http://0.0.0.0:{port}/sse")
    uvicorn.run(app, host="0.0.0.0", port=port)
