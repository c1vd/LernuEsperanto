import json
import sqlite3
import time

import flask
from werkzeug.security import generate_password_hash, check_password_hash

connection = sqlite3.connect("database.db", check_same_thread=False)
cursor = connection.cursor()

app = flask.Flask("esperanto_app")

app.config["SECRET_KEY"] = generate_password_hash(f"{time.perf_counter()}")


def is_authenticated():
    return flask.session.get("is_autenticated")


@app.route("/")
def index():
    return flask.render_template("index.html")


@app.route("/history")
def history():
    return flask.render_template("history.html")


@app.route("/grammar")
def grammar():
    return flask.render_template("grammar.html")


@app.route("/help_us")
def help_us():
    return flask.render_template("help_us.html")


@app.route("/dictionary")
def dictionary_page():
    return flask.render_template("dictionary.html")


@app.route("/dictionary/<id>")
def word_page(id):
    cursor.execute(f"SELECT word, translations FROM words WHERE id={id}")
    word_data = cursor.fetchone()
    return flask.render_template("word.html", word_data=word_data)


@app.route("/book/<id>")
def read_book(id):
    try:
        return flask.send_file(f"./books/{id}.pdf")
    except:
        return flask.redirect("/")


@app.route("/find_books", methods=["GET"])
def find_books():
    name_of_book = flask.request.values.get("book_name")
    data = cursor.execute(
        f"SELECT id, name_of_book, description, author, user FROM books WHERE LOWER(name_of_book) LIKE '%{name_of_book}%' AND is_verified").fetchall()
    return flask.render_template("find_books.html", books=data)


@app.route("/register", methods=["GET", "POST"])
def register():
    if is_authenticated():
        return flask.redirect("/")
    if flask.request.method == "POST":
        if "username" in flask.request.form and "password" in flask.request.form:
            data = cursor.execute(
                f"SELECT name FROM users WHERE name = '{flask.request.form.get('username')}'").fetchone()
            if data:
                return flask.redirect("/register")
            cursor.execute(
                f"INSERT INTO users(name, password, is_admin) VALUES ('{flask.request.form.get('username')}', '{generate_password_hash(flask.request.form.get('password'))}', false)")
            connection.commit()
            return flask.redirect("/login")
    return flask.render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if is_authenticated():
        return flask.redirect("/")
    if flask.request.method == "POST":
        if "username" in flask.request.form and "password" in flask.request.form:
            data = cursor.execute(
                f"SELECT id, name, password FROM users WHERE name = '{flask.request.form.get('username')}'").fetchone()
            if not data:
                pass
            elif check_password_hash(data[2], flask.request.form.get("password")):
                flask.session["username"] = data[1]
                flask.session["id"] = data[0]
                flask.session["is_authenticated"] = True
                return flask.redirect("/")
    return flask.render_template("login.html")


@app.route("/logout")
def logout():
    flask.session["username"] = None
    flask.session["id"] = None
    flask.session["is_authenticated"] = False
    return json.dumps({"status": 'OK'})


@app.route("/find_words", methods=["POST"])
def find_words():
    word = str(flask.request.values.get("word_to_find"))
    print(word)
    cursor.execute(
        f"SELECT id, word, translations FROM words WHERE LOWER(word) LIKE LOWER('%{word}%') OR LOWER(translations) LIKE LOWER('%{word}%')")

    return json.dumps({"status": 'OK', "words": cursor.fetchall()})


@app.route("/upload_book", methods=["GET", "POST"])
def upload_book():
    if not is_authenticated():
        return flask.redirect("/")
    if flask.request.method == "POST":
        if "file" not in flask.request.files:
            return flask.redirect("/upload_book")
        file = flask.request.files["file"]
        cursor.execute(
            f"INSERT INTO books(name_of_book, description, author, user, is_verified) VALUES ('{flask.request.form.get("name_of_book")}', '{flask.request.form.get("description")}', '{flask.request.form.get("author")}', '{flask.session['username']}', false)")
        connection.commit()
        cursor.execute("SELECT id FROM books ORDER BY id DESC LIMIT 1")
        file.save(f"C:/Users/Anarchy/PycharmProjects/IndividualProject_application/books/{cursor.fetchone()[0]}.pdf")
    return flask.render_template("upload_book.html")


@app.route("/my_books")
def my_books():
    if not is_authenticated():
        return flask.redirect("/")
    books = cursor.execute(f"SELECT id, name_of_book, author FROM books WHERE user = '{flask.session['username']}'")
    return flask.render_template("my_books.html", books=books)


@app.route("/delete_book", methods=["POST"])
def delete_book():
    if not is_authenticated():
        return flask.redirect("/")
    cursor.execute(
        f"DELETE FROM books WHERE user='{flask.session.get('username')}' AND id = '{flask.request.form.get('id')}'")
    connection.commit()
    return json.dumps({"status": 'OK'})


@app.route("/admin_delete_book", methods=["POST"])
def admin_delete_book():
    if not is_authenticated():
        return flask.redirect("/")
    is_admin = cursor.execute(f"SELECT is_admin FROM users WHERE name='{flask.session.get('username')}'").fetchone()[0]
    if not is_admin:
        return flask.redirect("/")
    cursor.execute(
        f"DELETE FROM books WHERE id='{flask.request.form.get('id')}'")
    connection.commit()
    return json.dumps({"status": 'OK'})


@app.route("/admin")
def admin_panel():
    if not is_authenticated():
        return flask.redirect("/")
    is_admin = cursor.execute(f"SELECT is_admin FROM users WHERE name='{flask.session.get('username')}'").fetchone()[0]
    if not is_admin:
        return flask.redirect("/")
    return flask.render_template("admin.html")


@app.route("/get_unverified_books", methods=["POST"])
def get_unverified_books():
    cursor.execute("SELECT id, name_of_book, description, author FROM books WHERE NOT is_verified")
    books = cursor.fetchall()
    return json.dumps({"status": 'OK', "books": books})


@app.route("/approve_book", methods=["POST"])
def approve_book():
    if not is_authenticated():
        return flask.redirect("/")
    is_admin = cursor.execute(f"SELECT is_admin FROM users WHERE name='{flask.session.get('username')}'").fetchone()[0]
    if not is_admin:
        return flask.redirect("/")
    cursor.execute(f"UPDATE books SET is_verified=1 WHERE id='{flask.request.form.get("id")}'")
    connection.commit()
    return json.dumps({"status": "OK"})


if __name__ == "__main__":
    app.run(debug=True)
    cursor.close()
    connection.close()
