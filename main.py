from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_cors import CORS
import os
import random
from datetime import datetime

app = Flask(__name__)
app.config['MYSQL_HOST'] = "127.0.0.1"
app.config['MYSQL_USER'] = "root"
app.config['MYSQL_PASSWORD'] = ""
app.config['MYSQL_DB'] = "kodsuzyazilim"
app.config['UPLOAD_FOLDER'] = "files/"
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)
CORS(app)


def userChecker(mail, password, method) -> bool:
    cur = mysql.connection.cursor()
    cur.execute('''SELECT * FROM users WHERE mail = %s''', (mail, ))
    data = cur.fetchone()
    if data:
        if method == "register":
            cur.close()
            return "Bu mail adresiyle daha önceden bir kayıt oluşturulmuş."
        elif method == "login":
            if data['password'] == password:
                cur.close()
                return "OK"
            else:
                cur.close()
                return "Hatalı şifre girdiniz"
    else:
        if method == "register":
            cur.close()
            return "REGISTER"
        elif method == "login":
            cur.close()
            return "Giriş yapmak istediğiniz hesap bulunamadı."


@app.route("/auth", methods=['GET', 'POST'])
def auth():
    if request.method == "POST":
        mail = request.args.get("mail")
        password = request.args.get("password")
        method = request.args.get("method")

        if (mail and password and method):
            result = userChecker(mail, password, method)
            if result == "REGISTER":
                cur = mysql.connection.cursor()
                cur.execute(
                    '''INSERT INTO users (mail, password) VALUES (%s, %s)''', (mail, password))
                mysql.connection.commit()

                cur.close()
                return "OK"
            else:
                return result
        else:
            return "Eksik bilgi girdiniz"


@app.route("/post", methods=['GET', 'POST'])
def publishPost():
    if request.method == "POST":
        userMail = request.args.get("userMail")
        body = request.args.get("body")
        title = request.args.get("title")
        categories = request.args.get("categories")
        type = request.args.get("type")
        if (userMail and body and title and type):
            cur = mysql.connection.cursor()
            cur.execute(
                '''INSERT INTO posts (userMail, body, title, type, date) VALUES (%s, %s, %s, %s, %s)''', (userMail, body, title, type, datetime.now()))
            categoryList = []
            lastId = cur.lastrowid
            if "," in categories:
                categoryList = categories.split(",")
            elif categories:
                categoryList = [categories]
            for category in categoryList:
                cur.execute(
                    '''INSERT INTO categories (parentId, category) VALUES (%s, %s)''', (lastId, category))
            mysql.connection.commit()
            cur.close()
            return "OK"

        else:
            return "Eksik bilgi"


@app.route("/uploadFile", methods=['GET', 'POST'])
def uploadFile():
    if request.method == "POST":
        file = request.files['file']
        filePath = f"{random.randint(0,99999)}_{file.filename}"
        file.save(os.path.join(app.config["UPLOAD_FOLDER"],
                  filePath))

        fileSize = str(os.stat(os.path.join(app.config["UPLOAD_FOLDER"],
                                            filePath)).st_size / 1024).split(".")[0]

        return jsonify({
            "path": app.config["UPLOAD_FOLDER"]+filePath,
            "size": fileSize
        })


@app.route("/uploadImage", methods=['GET', 'POST'])
def uploadImage():
    if request.method == "POST":
        file = request.files['image']
        fileExtension = file.filename.split(".")[-1]
        filePath = f"kodsuzyazilim_image_{random.randint(0,9999999999)}.{fileExtension}"

        file.save(os.path.join("images/",
                  filePath))

        return f"images/{filePath}"


@app.route("/getPosts/<int:limit>/<int:offset>")
def getPosts(limit, offset):
    category = request.args.get('category')
    mail = request.args.get('mail')
    if not mail:
        mail = ""
    if limit != "" and offset != "":
        cur = mysql.connection.cursor()
        format = "%d/%m/%Y %H:%i"
        if category == "null":
            cur.execute('''SELECT id, userMail, body, title, type, DATE_FORMAT(date, %s) AS date, (SELECT COUNT(mail) FROM likes WHERE likes.id = posts.id) as likeCount, (SELECT 1 FROM likes WHERE id = posts.id AND mail=%s) as liked FROM posts ORDER BY id DESC LIMIT %s OFFSET %s''',
                        [format, mail, limit, offset])
        else:
            if "search" in category:
                filter = f'%{category.split("-")[-1]}%'

                cur.execute('''SELECT id, userMail, body, title, type, DATE_FORMAT(date, %s) AS date, (SELECT COUNT(mail) FROM likes WHERE likes.id = posts.id) as likeCount, (SELECT 1 FROM likes WHERE id = posts.id AND mail=%s) as liked FROM posts WHERE title LIKE %s ORDER BY id DESC LIMIT %s OFFSET %s''',
                            [format, mail, filter, limit, offset])
            else:
                cur.execute(
                    '''SELECT parentId FROM categories WHERE category = %s''', [category])
                parentIdData = cur.fetchall()
                parentIdList = []

                for p in parentIdData:
                    parentIdList.append(p['parentId'])

                cur.execute('''SELECT id, userMail, body, title, type, DATE_FORMAT(date, %s) AS date, (SELECT COUNT(mail) FROM likes WHERE likes.id = posts.id) as likeCount, (SELECT 1 FROM likes WHERE id = posts.id AND mail=%s) as liked FROM posts WHERE posts.id IN %s ORDER BY id DESC LIMIT %s OFFSET %s''',
                            [format, mail, tuple(parentIdList), limit, offset])

        result = cur.fetchall()
        cur.close()
        if result:
            return jsonify(result)
        else:
            return "ERROR"


@app.route("/getPost")
def getPost():
    id = request.args.get('id')
    mail = request.args.get('mail')
    if id:
        cur = mysql.connection.cursor()
        format = "%d/%m/%Y %H:%i"

        cur.execute('''SELECT id, userMail, body, title, type, DATE_FORMAT(date, %s) AS date, (SELECT COUNT(mail) FROM likes WHERE likes.id = posts.id) as likeCount, (SELECT 1 FROM likes WHERE id = posts.id AND mail=%s) as liked FROM posts WHERE id=%s''',
                    [format, mail, id])

        data = cur.fetchone()

        if data:
            return jsonify(data)
        else:
            return "ERROR"


@app.route("/likePost/<int:id>", methods=['GET', 'POST'])
def likePost(id):
    mail = request.args.get('mail')
    if id and mail and request.method == "POST":
        cur = mysql.connection.cursor()
        cur.execute('''SELECT mail FROM likes WHERE id = %s''', [id])
        data = cur.fetchone()
        if (not data):
            cur.execute(
                '''INSERT INTO likes (id, mail) VALUES (%s, %s)''', [id, mail])
        else:
            # remove
            cur.execute(
                '''DELETE FROM likes WHERE id=%s AND mail=%s''', [id, mail])
        mysql.connection.commit()
        cur.close()
    return "OK"


@app.route("/getNotifications")
def getNotifications():
    mail = request.args.get('mail')
    if mail:
        cur = mysql.connection.cursor()
        cur.execute('''SELECT id, content, (SELECT 1 FROM seenNotifications WHERE notificationId=notifications.id AND seen=%s) as seen FROM notifications WHERE target=%s OR target="public" ORDER BY id DESC LIMIT 15''',
                    [mail, mail])
        data = cur.fetchall()
        if data:
            return jsonify(data)
        else:
            return jsonify({})


@app.route("/setSeenNotifications", methods=['GET', 'POST'])
def setSeenNotifications():
    mail = request.args.get('mail')
    idList = request.args.get('idList')
    if mail and idList:
        list = []
        if "," in idList:
            list = idList.split(",")
        else:
            list = [idList]
        cur = mysql.connection.cursor()

        for l in list:
            cur.execute('''INSERT INTO seenNotifications (notificationId, seen) VALUES (%s, %s)''',
                        [int(l), mail])
        mysql.connection.commit()

        # remove old notifications
        cur.execute(
            '''SELECT id FROM notifications WHERE target=%s ORDER BY id ASC''', [mail])
        data = cur.fetchall()
        if len(data) > 15:
            decrement = len(data) - 15
            for i in range(decrement):
                cur.execute('''DELETE FROM notifications WHERE target=%s AND id=%s''', [
                            mail, data[i]['id']])
                cur.execute('''DELETE FROM seenNotifications WHERE seen=%s AND notificationId=%s''', [
                            mail, data[i]['id']])
            mysql.connection.commit()
        return "OK"


@app.route("/getAdmins")
def getAdmins():
    cur = mysql.connection.cursor()
    cur.execute('''SELECT mail FROM adminList''')
    admins = cur.fetchall()
    return jsonify(admins)


if __name__ == '__main__':
    app.run(debug=True, port=3222)
