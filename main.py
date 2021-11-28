import asyncio
from aiohttp import web
import json
import urllib
from urllib.parse import urlparse
from urllib.parse import unquote
import os.path
import sqlite3

def parse_json_file(mimes_list):
    # Opening JSON file
    f = open('mime.json')

    # returns JSON object as
    # a dictionary
    data = json.load(f)

    # Iterating through the json
    # list
    for i in data['mime-mapping']:
        mimes_list.append(i)

    # Closing file
    f.close()

async def parse_requst(request):
    parsed_request = request
    words = parsed_request.replace(" ", "").split('HTTP')
    path_and_extension = words[0].split('.')
    return path_and_extension[1] #return extension

async def find_content_type(extension):
    for mime in mimes_list:
        if(extension == mime['extension']):
            return mime['mime-type']
    return "not found"

async def handler(request):
    print("request headers: ", request.headers)
    print("request url path: ", request.url.path)
    print("request url scheme: ", request.url.scheme)
    print("request method: ", request.method)
    print("request content: ", await request.content.readany())
    #request_content = await request.content.readany()
    url_path = request.url.path[1:]
    print('url_path: ', url_path)
    content = ''
    status = 500
    content_type = 'text\html'
    content_length = 0
    connection = 'close'
    if(request.method == 'GET'):
        extension = await parse_requst(url_path)
        print('extension: ', extension)
        content_type = await find_content_type(extension)
        print("content_type: ", content_type)
        if url_path is not None:
            if(os.path.exists(url_path)):
                with open(url_path, "rb") as f:
                    content = f.read()
                content_length = str(os.path.getsize(url_path))
                status = 200
            else:
                status = 404
                text = '''
                <html>
                <head>
                <title>404 Not Found</title>
                </head>
                <body>
                <h1>Not Found</h1>
                
                <p> The requested URL ''' + url_path + ''' was not found on this server</p>
                <hr/>
                </body>
                </html>
                '''
                content = text.encode()
                content_length = str(len(content))
                content_type = "text/html"

    if(request.method == 'POST'):
        if(url_path == "users"):
            status = 200
            content = 'user added to db'.encode()
            content_length = str(len(content))
            username = 'user1'
            password = '1234'
            conn = sqlite3.connect('users.db')
            cur = conn.cursor()
            # Insert a row of data
            cur.execute("INSERT INTO Users VALUES (username,password)")
            # Save (commit) the changes
            conn.commit()
            # We can also close the connection if we are done with it.
            # Just be sure any changes have been committed or they will be lost.
            conn.close()
            pass
            # #print("data: " , await request.text())
            # body = unquote(request_content)
            # print(body)
            # #parsed = urlparse(await request.content.readany())
            # #print("password: ", parsed.password)

    return web.Response(body=content, status=status,
                        headers ={'Content-Length': content_length, 'Connection': connection,"Content-Type" : content_type,  "charset" : "utf-8"})


async def main():
    server = web.Server(handler)
    runner = web.ServerRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()

    print("======= Serving on http://127.0.0.1:8080/ ======")

    # pause here for very long time by serving HTTP requests and
    # waiting for keyboard interruption
    await asyncio.sleep(100*3600)


mimes_list = []
parse_json_file(mimes_list)
loop = asyncio.get_event_loop()
future = asyncio.ensure_future(main())

try:
    loop.run_forever()
except KeyboardInterrupt:
    pass
loop.close()
