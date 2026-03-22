import os
import traceback
from rich.console import Console
console = Console(highlight = False)
from pathlib import Path
PATH = Path(__file__).resolve().parent # Path.cwd()

import socket
def reserve_socket(host = "0.0.0.0"):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, 54448))
    return s, s.getsockname()[1] # Возврат сокета - предотвращение закрытия. Не менять.

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80)) # Настоящего соединения к 8.8.8.8:80 не открывается. Не менять.
            return s.getsockname()[0]
    except:
        return "127.0.0.1"

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response, JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
app = FastAPI()

from pydantic import BaseModel
from pydantic.dataclasses import dataclass
from dataclasses import fields
from typing import Optional

app.mount("/static", StaticFiles(directory = f"{PATH}/static"), name = "static")

def page(name):
    return FileResponse(f"{PATH}/pages/{name}")
