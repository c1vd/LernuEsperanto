import json
import sqlite3
import time
from flask import session
import flask
from werkzeug.security import generate_password_hash, check_password_hash

connection = sqlite3.connect("database.db", check_same_thread=False)
cursor = connection.cursor()

app = flask.Flask("esperanto_app")

app.config["SECRET_KEY"] = generate_password_hash(f"{time.perf_counter()}")


# Error handlers
@app.errorhandler(404)
def error_404(error):
    return flask.render_template("404.html"), 404


@app.errorhandler(500)
def error_500(error):
    return flask.render_template("500.html"), 500


# Utilities
def is_authenticated():
    return flask.session.get("is_authenticated")


def post(key):
    return flask.request.form.get(key)


def get(key):
    return flask.request.args.get(key)


def is_admin():
    if not is_authenticated():
        return False
    data = cursor.execute(f"SELECT is_admin FROM users WHERE id='{session.get('id')}'").fetchone()
    if not data:
        return False
    return bool(data[0])


# Decorators
def admin_required(func):
    def decorated_function(*args, **kwargs):
        if not is_admin():
            return flask.redirect("/")
        return func(*args, **kwargs)

    decorated_function.__name__ = func.__name__
    return decorated_function


def authentication_required(func):
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return flask.redirect("/")
        return func(*args, **kwargs)

    decorated_function.__name__ = func.__name__
    return decorated_function


# Main page
@app.route("/")
def index():
    return flask.render_template("index.html")


# Pages with text about us and Esperanto
@app.route("/history")
def history():
    return flask.render_template("history.html")


@app.route("/grammar")
def grammar():
    return flask.render_template("grammar.html")


@app.route("/help_us")
def help_us():
    return flask.render_template("help_us.html")


# UI for finding of words
@app.route("/dictionary")
def dictionary_page():
    return flask.render_template("dictionary.html")


# Words and Books pages
@app.route("/dictionary/<id>")
def word_page(id):
    cursor.execute(f"SELECT id, word, translations FROM words WHERE id={id}")
    word_data = cursor.fetchone()
    if not word_data:
        return flask.redirect("/dictionary")
    return flask.render_template("word.html", word_data=word_data)


@app.route("/book/<id>")
def read_book(id):
    try:
        return flask.send_file(f"./books/{id}.pdf")
    except:
        return flask.redirect("/")


# Editing and adding of words
@app.route("/edit_word", methods=["POST"])
def edit_word():
    if is_authenticated():
        print(post("translations"), post("id"))
        cursor.execute(f"UPDATE words SET translations=LOWER('{post('translations')}') WHERE id={post('id')}")
        connection.commit()
    return json.dumps({"status": "OK"})


@app.route("/add_word", methods=["POST"])
def add_word():
    if not is_authenticated():
        return json.dumps({"status": "OK"})
    word = post("word")
    translations = post("translations")
    cursor.execute(f"SELECT id FROM words WHERE LOWER(word)=LOWER('{word}')")
    if cursor.fetchone():
        return json.dumps({"status": "OK"})
    cursor.execute(f"INSERT INTO words(word, translations) VALUES(LOWER('{word}'), LOWER('{translations}'))")
    connection.commit()
    return json.dumps({"status": "OK"})


# Login system
@app.route("/register", methods=["GET", "POST"])
def register():
    if is_authenticated():
        return flask.redirect("/")
    if flask.request.method == "POST":
        if "username" in flask.request.form and "password" in flask.request.form:
            data = cursor.execute(
                f"SELECT name FROM users WHERE name = '{post('username')}'").fetchone()
            if data:
                return flask.redirect("/register")

            cursor.execute(
                f"INSERT INTO users(name, password, is_admin) VALUES ('{post('username')}', '{generate_password_hash(post('password'))}', false)")
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
                f"SELECT id, name, password FROM users WHERE name = '{post('username')}'").fetchone()
            if not data:
                pass
            elif check_password_hash(data[2], post("password")):
                session["username"] = data[1]
                session["id"] = data[0]
                session["is_authenticated"] = True
                return flask.redirect("/")
    return flask.render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return json.dumps({"status": 'OK'})


# Finding words and books
@app.route("/find_words", methods=["POST"])
def find_words():
    word = str(post("word_to_find"))
    cursor.execute(
        f"SELECT id, word, translations FROM words WHERE LOWER(word) LIKE LOWER('%{word}%') OR LOWER(translations) LIKE LOWER('%{word}%')")

    return json.dumps({"status": 'OK', "words": cursor.fetchall()})


@app.route("/find_books", methods=["GET"])
def find_books():
    name_of_book = get("book_name")
    data = cursor.execute(
        f"SELECT id, name_of_book, description, author, user FROM books WHERE LOWER(name_of_book) LIKE '%{name_of_book}%' AND is_verified").fetchall()
    return flask.render_template("find_books.html", books=data)


# Uploading and deleting books by users
@app.route("/upload_book", methods=["GET", "POST"])
@authentication_required
def upload_book():
    if flask.request.method == "POST":
        if "file" not in flask.request.files:
            return flask.redirect("/upload_book")
        file = flask.request.files["file"]
        cursor.execute(
            f"INSERT INTO books(name_of_book, description, author, user, is_verified) VALUES ('{post("name_of_book")}', '{post("description")}', '{post("author")}', '{session['username']}', 0)")
        connection.commit()
        cursor.execute("SELECT id FROM books ORDER BY id DESC LIMIT 1")
        file.save(f"C:/Users/Anarchy/PycharmProjects/IndividualProject_application/books/{cursor.fetchone()[0]}.pdf")
    return flask.render_template("upload_book.html")


@app.route("/delete_book", methods=["POST"])
@authentication_required
def delete_book():
    cursor.execute(
        f"DELETE FROM books WHERE id = {post('id')} AND user='{session.get('username')}'")
    connection.commit()
    return json.dumps({"status": 'OK'})


# Users and admins panels
@app.route("/admin")
@admin_required
def admin_panel():
    return flask.render_template("admin.html")


@app.route("/user_panel")
@authentication_required
def user_panel():
    books = cursor.execute(f"SELECT id, name_of_book, author FROM books WHERE user = '{session['username']}'")
    return flask.render_template("user_panel.html", books=books)


# Functions that used by admins
@app.route("/approve_book", methods=["POST"])
@admin_required
def approve_book():
    cursor.execute(f"UPDATE books SET is_verified=1 WHERE id='{post("id")}'")
    connection.commit()
    return json.dumps({"status": "OK"})


@app.route("/admin_delete_book", methods=["POST"])
@admin_required
def admin_delete_book():
    cursor.execute(
        f"DELETE FROM books WHERE id='{post('id')}'")
    connection.commit()
    return json.dumps({"status": 'OK'})


@app.route("/get_unverified_books", methods=["POST"])
@admin_required
def get_unverified_books():
    cursor.execute("SELECT id, name_of_book, description, author FROM books WHERE NOT is_verified")
    books = cursor.fetchall()
    return json.dumps({"status": 'OK', "books": books})


if __name__ == "__main__":
    app.jinja_env.globals.update(is_admin=is_admin)
    app.run(host="0.0.0.0", debug=True)
    cursor.close()
    connection.close()
