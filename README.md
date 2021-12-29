# ssr-test

Simple server side rendering prototype

Uses FastAPI and ModernGL

Adapted from https://moderngl.readthedocs.io/en/latest/the_guide/rendering.html

## Setup

Get Python and Poetry

Run `poetry install`

## Run

Run `poetry run uvicorn ssr:app`

Docs http://localhost:8000/docs

Open http://localhost:8000/render

Pass query arguments (x, y, z, rx, ry, rz, width, height) for a different render

Example http://localhost:8000/render?x=-1&z=1&rx=0.2&ry=-0.2&rz=-0.2
