"""
modules/news/web.py

Busca as principais notícias do dia via Google News RSS.
Não precisa de API key — usa feed público com locale configurável.

Configuração via <SIAA_DATA_DIR>/contexts/cron-jobs/news.json:
    "settings": {
        "locale": "pt-BR",
        "country": "BR",
        "max_items": 10
    }

A localidade (cidade/região) é inferida a partir do config.json do bot
via campo location.latitude/longitude — não precisa de config extra.
"""

import xml.etree.ElementTree as ET
from datetime import datetime

import requests

from framework.base_web import BaseWeb


class NewsWeb(BaseWeb):

    GOOGLE_NEWS_RSS = "https://news.google.com/rss"

    def __init__(self, settings: dict = None):
        s = settings or {}
        self.locale    = s.get("locale", "pt-BR")
        self.country   = s.get("country", "BR")
        self.max_items = int(s.get("max_items", 10))

    def fetch(self, **kwargs) -> list[dict] | None:
        """
        Retorna lista de dicts com as principais notícias do Google News.
        Cada item: {"title": str, "source": str, "url": str, "published": str}
        """
        url    = self.GOOGLE_NEWS_RSS
        params = {
            "hl":   self.locale,
            "gl":   self.country,
            "ceid": f"{self.country}:{self.locale}",
        }

        try:
            print(f"📰 [NewsWeb] Buscando notícias... locale={self.locale} country={self.country}")

            if self._use_proxy():
                client = self._proxy_client()
                if client:
                    query  = "&".join(f"{k}={v}" for k, v in params.items())
                    raw    = client.browse(url=f"{url}?{query}", extract="text")
                    if raw:
                        return self._parse_rss(raw)
                print("⚠️  [NewsWeb] Proxy indisponível → conexão direta")

            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            return self._parse_rss(r.text)

        except requests.exceptions.RequestException as e:
            print(f"❌ [NewsWeb] Erro ao buscar notícias: {e}")
            return None
        except Exception as e:
            print(f"❌ [NewsWeb] Erro inesperado: {e}")
            return None

    def _parse_rss(self, xml_text: str) -> list[dict]:
        """Parseia o XML do RSS e retorna lista de notícias."""
        items = []
        try:
            root    = ET.fromstring(xml_text)
            channel = root.find("channel")
            if channel is None:
                return []

            for item in channel.findall("item")[: self.max_items]:
                title_el   = item.find("title")
                link_el    = item.find("link")
                source_el  = item.find("source")
                pubdate_el = item.find("pubDate")

                title   = title_el.text   if title_el   is not None else "Sem título"
                url     = link_el.text    if link_el    is not None else ""
                source  = source_el.text  if source_el  is not None else "Fonte desconhecida"
                pub_raw = pubdate_el.text if pubdate_el is not None else ""

                # "Mon, 24 Feb 2025 10:00:00 GMT" → "10:00"
                try:
                    pub_dt   = datetime.strptime(pub_raw, "%a, %d %b %Y %H:%M:%S %Z")
                    pub_time = pub_dt.strftime("%H:%M")
                except Exception:
                    pub_time = ""

                # Remove sufixo " - Fonte" que o Google News adiciona
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0].strip()

                items.append({
                    "title":     title,
                    "source":    source,
                    "url":       url,
                    "published": pub_time,
                })

        except ET.ParseError as e:
            print(f"❌ [NewsWeb] Erro ao parsear XML: {e}")

        return items

    def format_digest(self, items: list[dict]) -> str:
        """Formata as notícias para envio no Telegram (MarkdownV2)."""
        if not items:
            return "📭 Não foi possível buscar as notícias agora\\."

        today = datetime.now().strftime("%d/%m/%Y")
        lines = [f"📰 *Notícias do dia — {today}*\n"]

        for i, item in enumerate(items, 1):
            # Escapa caracteres especiais do MarkdownV2
            title  = _escape_md(item["title"])
            source = _escape_md(item["source"])
            time_str = f" _{item['published']}_" if item["published"] else ""

            lines.append(f"{i}\\. {title}{time_str}")
            lines.append(f"   📌 _{source}_\n")

        return "\n".join(lines)


def _escape_md(text: str) -> str:
    """Escapa caracteres reservados do MarkdownV2 do Telegram."""
    reserved = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in reserved else c for c in text)
