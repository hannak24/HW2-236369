import asyncio
from aiohttp import web
import json
import urllib
from urllib.parse import urlparse
from urllib.parse import unquote
import os.path
import sqlite3
from config import port, timeout, admin

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

async def parse_content(content):
    print("the content is: ", content)
    parameters = content.split('&')
    print("the parameters are: ", parameters)
    user = ''
    password = ''
    for parameter in parameters:
        if(parameter.find('username') != -1):
            user = parameter
        if(parameter.find('password') != -1):
            password = parameter
    if(user != ''):
        user = user.split('=')[1]
    if (password != ''):
        password = password.split('=')[1]
    return user, password


async def resource_not_found(url_path):
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
    return status,content, content_length, content_type

async def conflict(username):
    status = 409
    text = '''
    <html>
    <head>
    <title>409 Conflict</title>
    </head>
    <body>
    <h1>Conflict</h1>

    <p> The requested username ''' + username + ''' already exists in the database</p>
    <hr/>
    </body>
    </html>
    '''
    content = text.encode()
    content_length = str(len(content))
    content_type = "text/html"
    return status,content, content_length, content_type


async def handler(request):
    print("request headers: ", request.headers)
    print("request url path: ", request.url.path)
    print("request url scheme: ", request.url.scheme)
    print("request method: ", request.method)
    body = await request.content.readany()
    print("request content: ", body)
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
                status, content, content_length, content_type = await resource_not_found(url_path)

    if(request.method == 'POST'):
        if(url_path == "users"):
            curr_user, curr_password = await parse_content(body.decode("utf-8"))
            print("username and password are: ", curr_user, curr_password)
            status = 200
            content = ('user ' + curr_user + ' was added to the db').encode()
            content_length = str(len(content))
            conn = sqlite3.connect('users.db')
            cur = conn.cursor()

            try:
            # Insert a row of data
                print("INSERT INTO Users (username,password) VALUES ('" + curr_user + "','" + curr_password + "')")
                cur.execute("INSERT INTO Users (username,password) VALUES ('" + curr_user + "','" + curr_password + "')")
                conn.commit()
            except:
                print("error! user already defined")
                status, content, content_length, content_type = await conflict(curr_user)
            conn.close()
        else:
            status, content, content_length, content_type = await resource_not_found(url_path)

    if (request.method == 'DELETE'):
        parsed_url = url_path.split('/')
        if (parsed_url[0] == "users"):
            if url_path.find("/") != -1:
                user = parsed_url[1]
            else:
                user = ""
            print("username to delete is: ", user)
            status = 200
            content = ('user ' + user + ' was deleted from the db').encode()
            content_length = str(len(content))
            conn = sqlite3.connect('users.db')
            cur = conn.cursor()
            try:
                # Delete a row of data
                print("DELETE FROM Users WHERE username =" + "'" + user + "'")
                cur.execute("DELETE FROM Users WHERE username =" + "'" + user + "'")
                conn.commit()
            except:
                print("error!")
            conn.close()
        else:
            status, content, content_length, content_type = await resource_not_found(url_path)


    return web.Response(body=content, status=status,
                        headers ={'Content-Length': content_length, 'Connection': connection,"Content-Type" : content_type,  "charset" : "utf-8"})


async def main():
    server = web.Server(handler)
    runner = web.ServerRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', port,shutdown_timeout=timeout)
    await site.start()

    print("======= Serving on http://127.0.0.1:" + str(port) + "/ ======")

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
