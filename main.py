from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_cors import CORS
import os
import random
from datetime import datetime

app = Flask(__name__)
app.config['MYSQL_HOST'] = "localhost"
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
    print(category, "---------------------")
    if limit != "" and offset != "":
        cur = mysql.connection.cursor()
        format = "%d/%m/%Y %H:%i"
        if not category:
            cur.execute('''SELECT *, DATE_FORMAT(date, %s) AS formattedDate FROM posts ORDER BY date DESC LIMIT %s OFFSET %s''',
                        (format, limit, offset))
        else:
            cur.execute(
                '''SELECT parentId FROM categories WHERE category = %s''', (category, ))
            parentIdData = cur.fetchall()
            parentIdList = []
            for p in parentIdData:
                parentIdList.append(str(p['parentId']))

            cur.execute('''SELECT *, DATE_FORMAT(date, %s) AS formattedDate FROM posts WHERE id IN (%s) ORDER BY date DESC LIMIT %s OFFSET %s''',
                        (format, ", ".join(parentIdList), limit, offset))

        result = cur.fetchall()
        if result:
            return jsonify(result)
        else:
            return "ERROR"


if __name__ == '__main__':
    app.run(debug=True)
