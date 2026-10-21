#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""食物图片提供者：Pexels / Pixabay / Wikimedia Commons 三方搜索的统一接口。

为什么节流放在这一层：三方都要打远端搜索 API，Wikimedia 与 Pexels 对高频请求会直接
429。把「最小间隔 + 429 退避」下沉到唯一的 _http_get_json，所有 provider 都必须走它，
杜绝某个实现漏掉限速。

为什么 Key 只从环境变量读：仓库会被提交，任何写进代码或配置文件的 Key 都等于泄露。
本模块只认 PEXELS_API_KEY / PIXABAY_API_KEY，缺失时抛 MissingKeyError，由调用方决定
是报错还是改用其他 provider —— 绝不静默降级、更不伪造结果。
"""

import html
import os
import re
import threading
import time
from dataclasses import dataclass

import requests

# Wikimedia 要求客户端带可识别的 User-Agent；实测 UA 太笼统时 upload.wikimedia.org 会直接 429，
# 必须写成「客户端/版本 (说明) 库/版本」这种带联系信息的形态，这里统一自报家门。
DEFAULT_HEADERS = {
    "User-Agent": "values-food-images/1.0 (https://localhost/values; food-image enrichment script) requests/2.31.0",
}
# 下载二进制（upload.wikimedia.org）用的同一 UA，避免两处不一致又被限速
DOWNLOAD_HEADERS = DEFAULT_HEADERS

# 搜索 API 之间的最小间隔（秒）。Wikimedia 官方建议不超过 1 req/s，留一点余量取 1.2。
SEARCH_MIN_INTERVAL = 1.2
_search_last_ts = 0.0
_throttle_lock = threading.Lock()

# 单次请求超时：连接 10s / 读取 20s
HTTP_TIMEOUT = (10, 20)


class MissingKeyError(RuntimeError):
    """显式指定了需要 Key 的 provider，但对应环境变量为空时抛出。"""


@dataclass
class Candidate:
    """三方搜索结果归一化后的候选图片，字段含义与三方差异无关。"""

    provider: str
    title: str          # 用于过滤与打分的文本（alt / tags / 描述）
    download_url: str   # 可直接下载的图片二进制地址
    source_url: str     # 来源落地页，便于人工核对
    photographer: str
    license: str
    license_url: str
    width: int
    height: int
    mime: str


def _throttle():
    """全局节流：保证任意两次搜索请求之间至少间隔 SEARCH_MIN_INTERVAL 秒。"""
    global _search_last_ts
    with _throttle_lock:
        now = time.monotonic()
        wait = SEARCH_MIN_INTERVAL - (now - _search_last_ts)
        if wait > 0:
            time.sleep(wait)
        _search_last_ts = time.monotonic()


def _http_get_json(url, params=None, headers=None, max_retries=2):
    """带节流与退避重试的 JSON GET；429 用更长退避，5xx/网络错误短退避。"""
    attempt = 0
    merged_headers = dict(DEFAULT_HEADERS)
    if headers:
        merged_headers.update(headers)
    while True:
        _throttle()
        try:
            resp = requests.get(url, params=params, headers=merged_headers, timeout=HTTP_TIMEOUT)
        except requests.RequestException:
            if attempt >= max_retries:
                raise
            attempt += 1
            time.sleep(1.5 * attempt)
            continue

        if resp.status_code == 429:
            if attempt >= max_retries:
                resp.raise_for_status()
            attempt += 1
            time.sleep(5 * attempt)  # 被限速时拉长间隔，避免继续撞墙
            continue
        if resp.status_code >= 500:
            if attempt >= max_retries:
                resp.raise_for_status()
            attempt += 1
            time.sleep(1.5 * attempt)
            continue

        resp.raise_for_status()
        return resp.json()


_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(value):
    """extmetadata 里的 Artist / 描述常带 HTML 标签，去掉并还原实体。"""
    if not value:
        return ""
    text = _TAG_RE.sub("", str(value))
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


class ImageProvider:
    """所有 provider 的基类，子类只需实现 search()。"""

    name = "base"
    requires_key = False
    key_env = ""

    def key_available(self):
        return bool(os.environ.get(self.key_env, "").strip()) if self.key_env else True

    def _require_key(self):
        key = os.environ.get(self.key_env, "").strip()
        if not key:
            raise MissingKeyError(
                "provider=%s 需要环境变量 %s，但当前为空。" % (self.name, self.key_env)
            )
        return key

    def search(self, term, limit):
        raise NotImplementedError


class PexelsProvider(ImageProvider):
    name = "pexels"
    requires_key = True
    key_env = "PEXELS_API_KEY"
    API = "https://api.pexels.com/v1/search"

    def search(self, term, limit):
        key = self._require_key()
        data = _http_get_json(
            self.API,
            params={"query": term, "per_page": limit},
            headers={"Authorization": key},
        )
        out = []
        for photo in data.get("photos", []):
            src = photo.get("src") or {}
            # large(约 940px 宽) 足够，original 体积大，按 large → original 顺序回退
            download = src.get("large") or src.get("original")
            if not download:
                continue
            out.append(Candidate(
                provider=self.name,
                title=(photo.get("alt") or "").strip(),
                download_url=download,
                source_url=photo.get("url") or "",
                photographer=(photo.get("photographer") or "").strip(),
                license="Pexels License",
                license_url="https://www.pexels.com/license/",
                width=int(photo.get("width") or 0),
                height=int(photo.get("height") or 0),
                mime="image/jpeg",
            ))
        return out


class PixabayProvider(ImageProvider):
    name = "pixabay"
    requires_key = True
    key_env = "PIXABAY_API_KEY"
    API = "https://pixabay.com/api/"

    def search(self, term, limit):
        key = self._require_key()
        data = _http_get_json(self.API, params={
            "key": key,
            "q": term,
            "image_type": "photo",
            "safesearch": "true",
            "per_page": limit,
        })
        out = []
        for hit in data.get("hits", []):
            download = hit.get("largeImageURL")
            if not download:
                continue
            out.append(Candidate(
                provider=self.name,
                # Pixabay 没有独立标题，用 tags 作为可过滤文本
                title=(hit.get("tags") or "").strip(),
                download_url=download,
                source_url=hit.get("pageURL") or "",
                photographer=(hit.get("user") or "").strip(),
                license="Pixabay Content License",
                license_url="https://pixabay.com/service/license-summary/",
                width=int(hit.get("imageWidth") or 0),
                height=int(hit.get("imageHeight") or 0),
                mime="image/jpeg",
            ))
        return out


class WikimediaCommonsProvider(ImageProvider):
    name = "commons"
    requires_key = False
    key_env = ""  # Commons 公开 API，无需 Key
    API = "https://commons.wikimedia.org/w/api.php"

    def search(self, term, limit):
        data = _http_get_json(self.API, params={
            "action": "query",
            "format": "json",
            "generator": "search",
            # 限定只搜位图文件，避免返回 SVG/PDF/音频等无关结果
            "gsrsearch": "filetype:bitmap %s" % term,
            "gsrnamespace": 6,  # File: 命名空间
            "gsrlimit": limit,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|size|mime",
            "iiextmetadatafilter": "LicenseShortName|Artist|LicenseUrl|ImageDescription|ObjectName|UsageTerms",
            # 要 800px 缩略图：Commons 原图常见十几 MB，直接下原图既慢又容易撞 8MB 上限；
            # 反正最终只进 512 盒，下 800px 缩略图足够且体积可控。width/height 仍取原图尺寸用于打分。
            "iiurlwidth": 800,
        })
        pages = ((data.get("query") or {}).get("pages") or {})
        out = []
        for page in pages.values():
            info_list = page.get("imageinfo") or []
            if not info_list:
                continue
            info = info_list[0]
            meta = info.get("extmetadata") or {}

            def _meta(key):
                return strip_html((meta.get(key) or {}).get("value"))

            file_title = strip_html(page.get("title") or "").replace("File:", "")
            title = _meta("ObjectName") or _meta("ImageDescription")[:160] or file_title
            license_name = _meta("LicenseShortName") or _meta("UsageTerms") or "unknown"
            out.append(Candidate(
                provider=self.name,
                title=title,
                download_url=info.get("thumburl") or info.get("url") or "",
                source_url=info.get("descriptionurl")
                or ("https://commons.wikimedia.org/wiki/" + (page.get("title") or "")),
                photographer=_meta("Artist"),
                license=license_name,
                license_url=_meta("LicenseUrl"),
                width=int(info.get("width") or 0),
                height=int(info.get("height") or 0),
                mime=info.get("mime") or "",
            ))
        return out


PROVIDERS = {
    "pexels": PexelsProvider,
    "pixabay": PixabayProvider,
    "commons": WikimediaCommonsProvider,
}

# 自动挑选 provider 的优先级：有 Key 的先用，都没有就用无需 Key 的 Commons
AUTO_ORDER = ("pexels", "pixabay", "commons")


def select_provider(requested=None):
    """返回 provider 实例。

    requested 为 None 时按 AUTO_ORDER 自动挑选；显式指定需要 Key 的 provider 而 Key
    缺失时抛 MissingKeyError，由调用方给出「改用 commons 或 --manual-urls」的提示。
    """
    if requested:
        cls = PROVIDERS.get(requested)
        if cls is None:
            raise ValueError("未知 provider: %s（可选 %s）" % (requested, ", ".join(PROVIDERS)))
        provider = cls()
        if provider.requires_key and not provider.key_available():
            raise MissingKeyError(
                "provider=%s 需要环境变量 %s，但当前未设置。" % (requested, provider.key_env)
            )
        return provider

    for name in AUTO_ORDER:
        provider = PROVIDERS[name]()
        if provider.key_available():
            return provider
    return WikimediaCommonsProvider()