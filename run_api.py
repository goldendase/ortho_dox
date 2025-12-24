#!/usr/bin/env python3
"""Convenience script to run the API server."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="127.0.0.1", port=8080, reload=True)
