import aiohttp
import json
from aiohttp import web



def create_gui(page_coro):
    #Create gui
    gui = web.Application()
    #
    gui.router.add_get('/', page_coro)
    return gui

web.run_app(gui)