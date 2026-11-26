# -*- coding: utf-8 -*-
"""Fixes from the automated security scans (Bandit, see docs/SECURITY_SCANS.md) stay fixed. Offline, no network."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "scripts")
sys.path.insert(0, S)
import news_slice  # noqa: E402
import registry_lv  # noqa: E402
import supply_watch  # noqa: E402


@pytest.mark.parametrize("fetch", [news_slice.fetch, supply_watch.fetch])
@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/feed.xml", "C:/Users/x/feed.xml"])
def test_web_readers_refuse_local_and_odd_links(fetch, url):
    with pytest.raises(ValueError):
        fetch(url)


def test_register_reader_refuses_file_links():
    with pytest.raises(ValueError):
        list(registry_lv.lines("file:///etc/passwd"))


def test_feed_with_entities_is_skipped():
    bomb = (b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;">]>'
            b"<rss><channel><item><title>&b;</title><link>https://x.example/</link></item></channel></rss>")
    with pytest.raises(ValueError):
        news_slice.parse_feed(bomb)


def test_plain_feed_still_reads():
    ok = (b'<?xml version="1.0"?><rss><channel><item><title>Steel price up</title>'
          b"<link>https://x.example/a</link><pubDate>Thu, 19 Nov 2026 10:00:00 GMT</pubDate></item></channel></rss>")
    items = news_slice.parse_feed(ok)
    assert items and items[0][1] == "Steel price up"
