from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import asyncio
import time
from typing import List, Optional
from urllib.parse import urljoin

app = FastAPI(title="Redirect Checker API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class URLRequest(BaseModel):
    url: str
    max_redirects: int = 20
    timeout: float = 15.0
    user_agent: str = "Mozilla/5.0 (compatible; RedirectChecker/1.0)"


class BulkURLRequest(BaseModel):
    urls: List[str]
    max_redirects: int = 20
    timeout: float = 15.0
    user_agent: str = "Mozilla/5.0 (compatible; RedirectChecker/1.0)"


class RedirectHop(BaseModel):
    step: int
    url: str
    status_code: int
    status_text: str
    response_time_ms: float
    content_type: Optional[str] = None
    server: Optional[str] = None
    location: Optional[str] = None


class CheckResult(BaseModel):
    original_url: str
    final_url: str
    total_redirects: int
    total_time_ms: float
    hops: List[RedirectHop]
    error: Optional[str] = None
    is_loop: bool = False


HTTP_STATUS_TEXTS = {
    200: "OK", 201: "Created", 204: "No Content",
    301: "Moved Permanently", 302: "Found", 303: "See Other",
    307: "Temporary Redirect", 308: "Permanent Redirect",
    400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
    404: "Not Found", 405: "Method Not Allowed",
    500: "Internal Server Error", 502: "Bad Gateway",
    503: "Service Unavailable", 504: "Gateway Timeout",
}


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


async def check_url(
    url: str,
    max_redirects: int = 20,
    timeout: float = 15.0,
    user_agent: str = "Mozilla/5.0 (compatible; RedirectChecker/1.0)",
) -> CheckResult:
    original_url = normalize_url(url)
    current_url = original_url
    hops: List[RedirectHop] = []
    visited_urls = set()
    start_total = time.perf_counter()
    is_loop = False

    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=timeout,
            verify=False,
            headers=headers,
        ) as client:
            step = 1
            while step <= max_redirects + 1:
                if current_url in visited_urls:
                    is_loop = True
                    break
                visited_urls.add(current_url)

                hop_start = time.perf_counter()
                try:
                    response = await client.get(current_url)
                except httpx.TimeoutException:
                    hops.append(
                        RedirectHop(
                            step=step,
                            url=current_url,
                            status_code=0,
                            status_text="Timeout",
                            response_time_ms=round((time.perf_counter() - hop_start) * 1000, 2),
                        )
                    )
                    break
                except httpx.ConnectError as e:
                    hops.append(
                        RedirectHop(
                            step=step,
                            url=current_url,
                            status_code=0,
                            status_text=f"Connection Error",
                            response_time_ms=round((time.perf_counter() - hop_start) * 1000, 2),
                        )
                    )
                    break

                hop_time = round((time.perf_counter() - hop_start) * 1000, 2)
                location = response.headers.get("location")
                content_type = response.headers.get("content-type", "").split(";")[0].strip()
                server = response.headers.get("server")
                status_text = HTTP_STATUS_TEXTS.get(response.status_code, response.reason_phrase or "")

                hop = RedirectHop(
                    step=step,
                    url=str(response.url),
                    status_code=response.status_code,
                    status_text=status_text,
                    response_time_ms=hop_time,
                    content_type=content_type or None,
                    server=server,
                    location=location,
                )
                hops.append(hop)

                if response.is_redirect and location:
                    # Resolve relative redirects
                    if not location.startswith(("http://", "https://")):
                        location = urljoin(current_url, location)
                    current_url = location
                    step += 1
                else:
                    break
            else:
                # Hit max_redirects
                pass

    except Exception as e:
        return CheckResult(
            original_url=original_url,
            final_url=original_url,
            total_redirects=0,
            total_time_ms=round((time.perf_counter() - start_total) * 1000, 2),
            hops=hops,
            error=str(e),
        )

    total_time = round((time.perf_counter() - start_total) * 1000, 2)
    final_url = hops[-1].url if hops else original_url
    redirect_count = len([h for h in hops if 300 <= h.status_code < 400])

    return CheckResult(
        original_url=original_url,
        final_url=final_url,
        total_redirects=redirect_count,
        total_time_ms=total_time,
        hops=hops,
        is_loop=is_loop,
    )


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/api/check", response_model=CheckResult)
async def check_single(request: URLRequest):
    return await check_url(
        request.url,
        request.max_redirects,
        request.timeout,
        request.user_agent,
    )


@app.post("/api/check/bulk")
async def check_bulk(request: BulkURLRequest):
    tasks = [
        check_url(url, request.max_redirects, request.timeout, request.user_agent)
        for url in request.urls
        if url.strip()
    ]
    results = await asyncio.gather(*tasks)
    return {
        "results": results,
        "total": len(results),
        "errors": sum(1 for r in results if r.error),
    }
