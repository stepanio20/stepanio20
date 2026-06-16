"""External-service connectors. Each subpackage holds:
- client.py     — minimal REST client (stdlib urllib only)
- authorize.py  — one-time OAuth dance to obtain a refresh token
- sync.py       — pull data and write into the Health Graph

Connectors read all credentials from os.environ. Source secrets.env first.
"""
