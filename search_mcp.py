import os
import logging
import uvicorn
from fastmcp import FastMCP
from duckduckgo_search import DDGS
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("internet-search-mcp")

# FastMCP 서버 초기화
mcp = FastMCP(name="internet-search")

@mcp.tool
def search_internet(query: str, max_results: int = 5) -> str:
    """
    인터넷 실시간 검색을 통해 최신 정보를 가져옵니다.
    광고 법령, 시장 트렌드, 뉴스 등 실시간 조사가 필요한 경우에 사용합니다.

    Args:
        query: 검색하고자 하는 핵심 키워드나 질문 문장
        max_results: 가져올 검색 결과의 개수 (최대 10개, 기본값 5)
    
    Returns:
        검색 결과 (제목, 요약, URL 포함)
    """
    logger.info(f"Searching for: {query} (max_results={max_results})")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

            if not results:
                logger.warning(f"No results found for query: {query}")
                return "검색 결과가 없습니다."

            # 검색 결과를 Markdown 포맷으로 구성
            formatted_text = f"'{query}' 검색 결과:\n\n"
            for r in results:
                title = r.get("title", "No Title")
                body = r.get("body", "No Description")
                href = r.get("href", "")
                formatted_text += f"### {title}\n"
                formatted_text += f"{body}\n"
                formatted_text += f"**URL**: {href}\n\n"

            logger.info(f"Successfully retrieved {len(results)} results.")
            return formatted_text

    except Exception as e:
        logger.error(f"Search failed: {str(e)}", exc_info=True)
        return f"검색 중 오류 발생: {str(e)}"


async def health_check(request: Request) -> JSONResponse:
    """Render 헬스체크용 엔드포인트 (HEAD/GET 모두 허용)"""
    return JSONResponse({"status": "ok"})


def create_app() -> Starlette:
    """Starlette 앱에 헬스체크 + FastMCP를 마운트하여 반환"""
    mcp_asgi = mcp.http_app(path="/")

    app = Starlette(
        routes=[
            Route("/health", health_check, methods=["GET", "HEAD"]),
            Route("/", health_check, methods=["GET", "HEAD"]),
            Mount("/mcp", app=mcp_asgi),
        ],
        lifespan=mcp_asgi.router.lifespan_context,
    )
    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting MCP server on port {port}...")
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=port)

