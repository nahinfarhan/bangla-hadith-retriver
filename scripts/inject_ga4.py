"""Inject the GA4 gtag.js snippet into Streamlit's static/index.html.

Run once at Docker build time, after streamlit is installed. Traffic and
pageviews only: no custom events, queries or answers are ever sent to GA4.
"""
import os
import sys

import streamlit

MEASUREMENT_ID = "G-SCRQ5RE3VF"
MARKER = f"googletagmanager.com/gtag/js?id={MEASUREMENT_ID}"

SNIPPET = (
    f'<script async src="https://www.googletagmanager.com/gtag/js?id={MEASUREMENT_ID}"></script>'
    "<script>"
    "window.dataLayer = window.dataLayer || [];"
    "function gtag(){dataLayer.push(arguments);}"
    "gtag('js', new Date());"
    f"gtag('config', '{MEASUREMENT_ID}', {{ anonymize_ip: true }});"
    "</script>"
)

path = os.path.join(os.path.dirname(streamlit.__file__), "static", "index.html")
html = open(path, encoding="utf-8").read()

if MARKER in html:
    print("GA4 snippet already present")
    sys.exit(0)
if html.count("<head>") != 1:
    sys.exit(f"expected exactly one <head> in {path}, found {html.count('<head>')}")

open(path, "w", encoding="utf-8").write(html.replace("<head>", "<head>" + SNIPPET, 1))
print(f"GA4 snippet injected into {path}")
