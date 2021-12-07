import asyncio
from pathlib import Path
from urllib import parse

import aiofiles
from aiohttp import web
import json
import urllib
import os.path
import sqlite3

from config import port, timeout, admin
import base64


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
    if(len(path_and_extension) == 1):
        return ""
    else:
        return path_and_extension[1]  # return extension


async def find_content_type(extension):
    for mime in mimes_list:
        if (extension == mime['extension']):
            return mime['mime-type']
    return "not found"


async def parse_content(content):
    parameters = content.split('&')
    user = ''
    password = ''
    for parameter in parameters:
        if (parameter.find('username') != -1):
            user = parameter
        if (parameter.find('password') != -1):
            password = parameter
    if (user != ''):
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
    return status, content, content_length, content_type


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
    return status, content, content_length, content_type


async def unauthorized():
    status = 401
    text = '''
    <html>
    <head>
    <title>401 Unauthorized</title>
    </head>
    <body>
    <h1>Unauthorized</h1>

    <p> You aren't authorized to do this action</p>
    <hr/>
    </body>
    </html>
    '''
    content = text.encode()
    content_length = str(len(content))
    content_type = "text/html"
    return status, content, content_length, content_type

async def forbidden():
    status = 403
    text = '''
    <html>
    <head>
    <title>403 forbbiden</title>
    </head>
    <body>
    <h1>Forbidden</h1>

    <p> The access to this resource is forbidden</p>
    <hr/>
    </body>
    </html>
    '''
    content = text.encode()
    content_length = str(len(content))
    content_type = "text/html"
    return status, content, content_length, content_type

async def bad_request():
    status = 400
    text = '''
    <html>
    <head>
    <title>400 Bad Request</title>
    </head>
    <body>
    <h1>Bad Request</h1>

    <p> You aren't asking for a file</p>
    <hr/>
    </body>
    </html>
    '''
    content = text.encode()
    content_length = str(len(content))
    content_type = "text/html"
    return status, content, content_length, content_type


def response(status, content, content_length, content_type, connection, autentication_flag, realm):
    if (autentication_flag == 0):
        return web.Response(body=content, status=status,
                            headers={'Content-Length': content_length, 'Connection': connection,
                                     "Content-Type": content_type,
                                     "charset": "utf-8"})
    else:
        return web.Response(body=content, status=status,
                            headers={'Content-Length': content_length, 'Connection': connection,
                                     "Content-Type": content_type,
                                     "charset": "utf-8", "WWW-Authenticate": 'Basic ' + 'realm=' + realm})


async def handler(request):
    body = await request.content.readany()
    url_path = request.url.path[1:]
    admin_username = admin['username']
    admin_password = admin['password']
    adminCardentials = base64.b64encode(bytes((admin_username + ":" + admin_password), 'utf-8'))
    content = ''
    status = 500
    content_type = 'text\html'
    content_length = 0
    connection = 'close'
    autentication_flag = 0
    realm = 'admin'
    if (request.method == 'GET'):
        extension = await parse_requst(url_path)
        content_type = await find_content_type(extension)
        if url_path is not None:
            if (os.path.exists(url_path)):
                if(url_path == "users.db" or url_path == "config.py"):
                    status, content, content_length, content_type = await forbidden()
                    autentication_flag = 0;
                    realm = 'admin'
                else:
                    if(os.path.isfile(url_path) == 0):
                        status, content, content_length, content_type = await bad_request()
                    else:
                        async with aiofiles.open(url_path,"rb") as f:
                            content = await f.read()
                        content_length = str(os.path.getsize(url_path))
                        status = 200
                        get_params = parse.urlsplit(str(request.url)).query
                        params = dict(parse.parse_qsl(get_params))
                        if url_path.endswith('.dp'):
                            if 'Authorization' in request.headers:
                                author_request = request.headers['Authorization'].split(' ')
                                if author_request[0] == "Basic":
                                    details = base64.b64decode(author_request[1]).decode().split(":")
                                    username = details[0]
                                    password = details[1]
                                    conn = sqlite3.connect('users.db')
                                    cur = conn.cursor()
                                    is_admin = (username == admin_username and password == admin_password)
                                    try:
                                        cur.execute(" SELECT * FROM Users WHERE username=? AND password=?",
                                                    (username, password))
                                        check = cur.fetchone()
                                        conn.commit()
                                    except:
                                        print("error!")
                                    conn.close()
                                    if check is None and not is_admin:
                                        status = 401
                                        content = await dp_parser(request, params, "None", False)
                                        content = content.encode()
                                        content_length = str(len(content))
                                        autentication_flag = 1
                                        realm = 'admin'
                                    else:
                                        content = await dp_parser(request, params, username)
                                        content = content.encode()
                                        content_length = str(len(content))
                                        content_type = "text/html"
                            else:
                                content = await dp_parser(request, params, "None", False)
                                content = content.encode()
                                content_length = str(len(content))
            else:
                status, content, content_length, content_type = await resource_not_found(url_path)

    if (request.method == 'POST'):
        if 'Authorization' in request.headers:
            author_request = request.headers['Authorization'].split(' ')
            if author_request[0] == "Basic" and author_request[1] == adminCardentials.decode("utf-8"):
                if (url_path == "users"):
                    curr_user, curr_password = await parse_content(body.decode("utf-8"))
                    status = 200
                    curr_user = urllib.parse.unquote(curr_user)
                    content = ('user ' + curr_user + ' was added to the db').encode()
                    content_length = str(len(content))
                    conn = sqlite3.connect('users.db')
                    cur = conn.cursor()


                    try:
                        # Insert a row of data
                        cur.execute(
                            "INSERT INTO Users (username,password) VALUES ('" + curr_user + "','" + curr_password + "')")
                        conn.commit()
                    except:
                        status, content, content_length, content_type = await conflict(curr_user)
                    conn.close()
                else:
                    status, content, content_length, content_type = await resource_not_found(url_path)
            else:
                status, content, content_length, content_type = await unauthorized()
                autentication_flag = 1
                realm = 'admin'
        else:
            status, content, content_length, content_type = await unauthorized()
            autentication_flag = 1
            realm = 'admin'

    if (request.method == 'DELETE'):
        if 'Authorization' in request.headers:
            author_request = request.headers['Authorization'].split(' ')
            if author_request[0] == "Basic" and author_request[1] == adminCardentials.decode("utf-8"):
                parsed_url = url_path.split('/')
                if (parsed_url[0] == "users"):
                    if url_path.find("/") != -1:
                        user = parsed_url[1]
                    else:
                        user = ""
                    status = 200
                    content = ('user ' + user + ' was deleted from the db').encode()
                    content_length = str(len(content))
                    conn = sqlite3.connect('users.db')
                    cur = conn.cursor()
                    try:
                        # Delete a row of data
                        cur.execute("DELETE FROM Users WHERE username =" + "'" + user + "'")
                        conn.commit()
                    except:
                        print("error!")
                    conn.close()
                else:
                    status, content, content_length, content_type = await resource_not_found(url_path)
            else:
                status, content, content_length, content_type = await unauthorized()
                autentication_flag = 1
                realm = 'admin'
        else:
            status, content, content_length, content_type = await unauthorized()
            autentication_flag = 1
            realm = 'admin'

    # return web.Response(body=content, status=status,
    # headers ={'Content-Length': content_length, 'Connection': connection,"Content-Type" : content_type,  "charset" : "utf-8"})
    return response(status, content, content_length, content_type, connection, autentication_flag, realm)


async def dp_parser(request, params, username, auth_flag=True):
    file_path = Path(f".{request.path}")
    if not file_path.is_file():
        return resource_not_found(file_path)
    content = ''
    async with aiofiles.open(f".{request.path}") as op_file:
        file = await op_file.read()
    sp = file.split('%')

    for index, str in enumerate(sp):
        to_add = ''
        if index % 2 == 0:
            to_add += str
        else:
            res = {}
            exec(f"to_add={str}", {"user": {"authenticated": auth_flag, "username": username}, "params": params}, res)
            to_add = res['to_add']
        if to_add.endswith('{'):
            to_add = to_add[:-1]
        if to_add.startswith('}'):
            to_add = to_add[1:]
        content += to_add

    return content


async def main():
    server = web.Server(handler)
    runner = web.ServerRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', port, shutdown_timeout=timeout)
    await site.start()

    print("======= Serving on http://127.0.0.1:" + str(port) + "/ ======")

    # pause here for very long time by serving HTTP requests and
    # waiting for keyboard interruption
    await asyncio.sleep(100 * 3600)


mimes_list = []
parse_json_file(mimes_list)
loop = asyncio.get_event_loop()
future = asyncio.ensure_future(main())

try:
    loop.run_forever()
except KeyboardInterrupt:
    pass
loop.close()
