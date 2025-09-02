# MIT License


from flask import Blueprint, request, render_template, redirect, session, abort
from src.auth import login_required
from src.helpers import error, UserInfo
from cs50 import SQL
from flask import abort
from tensorflow.keras.models import load_model
from src import reddy_tech
import cv2
import pytesseract
# Mention the installed location of Tesseract-OCR in your system
pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe'

# Import required packages
##from googletrans import Translator
##translator = Translator()
import socket

def get_system_ip():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    return ip_address

home = Blueprint("home", __name__, static_folder="static", template_folder="templates")
blocked_ips = set()

db = SQL("sqlite:///src/main.db")
# Load the ML model and initiate Mindhunters
model = load_model('src/nagesh.h5')
word_to_index, max_len = reddy_tech.init()

@home.route('/unblock_my_ip')
def unblock_my_ip():
    my_ip_address = get_system_ip()
    blocked_ips.discard(my_ip_address)
    return f"IP address {my_ip_address} unblocked successfully"

@home.route("/detect", methods=["GET", "POST"])
@login_required
def detect():
    userInfo, dp = UserInfo(db)
    img = request.form["file"]
    print(img)
    path = "images/"+img
    # Convert the image to gray scale
    img = cv2.imread(path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    text1=pytesseract.image_to_string(gray)
    print('\n--------------Recognized Text------------\n')
    print(text1)     
    post_text = text1
    if not post_text:
        return redirect("/")
    text = [reddy_tech.clean_text(post_text)]
    text = reddy_tech.sentences_to_indices(text, word_to_index, max_len)
    ans = model.predict(text)[0][0]
    db.execute("INSERT INTO :tablename ('text', 'nature') VALUES (:post_text, :score)", tablename=userInfo['username'], post_text=post_text, score=str(ans))
    if (ans < 0.4):
        score = (0.4 - ans)
        total = "{:.2f}".format(userInfo['total'] + score)
        good_score = "{:.2f}".format(userInfo['score'] + score)
        db.execute("UPDATE users SET score=:score, total=:total WHERE id=:user_id", score = good_score, total = total, user_id = session["user_id"])
        return redirect("/")
    else:
        score = (ans - 0.4)
        total = "{:.2f}".format((userInfo['total'] + score))
        db.execute("UPDATE users SET total=:total WHERE id=:user_id", total = total, user_id = session["user_id"])
        return redirect("/")


@home.route("/", methods=["GET", "POST"])
@login_required
def index():
    userInfo, dp = UserInfo(db)
    if request.method == "GET":
        get_posts = db.execute("SELECT * FROM :tablename", tablename=userInfo['username'])
        get_posts = add_publisher(get_posts, userInfo['username'])
        follow_metadata = db.execute("SELECT following FROM :tablename", tablename=userInfo["username"]+'Social')
        posts_metadata = {userInfo['username']:dp}
        for following in follow_metadata:
            following_posts = db.execute("SELECT * FROM :tablename", tablename=following['following'])
            following_posts = add_publisher(following_posts, following['following'])
            other_user_info, other_user_dp = UserInfo(db, following['following'])
            posts_metadata[following['following']] = other_user_dp
            get_posts.extend(following_posts)
        get_posts.sort(key=get_timestamp, reverse=True)
        if get_posts:
            print('score is ', ((userInfo['score']/userInfo['total'])*10))
            if ((userInfo['score']/userInfo['total'])*10) < 5:
                blocked_ips.add(get_system_ip())
                print('blocked')
##                abort(403, "ip blocked due to score is les than 5")
                return render_template("index.html", msg = "ip blocked due to score is less than 5")
            else:
                return render_template('index.html', posts=get_posts, posts_metadata=posts_metadata, dp=dp, user=userInfo, reputation = ((userInfo['score']/userInfo['total'])*10))
        else:
            return render_template("index.html")
    else:
        post_text = request.form.get("post")
        #post_text = translator.translate(post_text1, dest='en').text
        if not post_text:
            return redirect("/")
        text = [reddy_tech.clean_text(post_text)]
        text = reddy_tech.sentences_to_indices(text, word_to_index, max_len)
        ans = model.predict(text)[0][0]
        db.execute("INSERT INTO :tablename ('text', 'nature') VALUES (:post_text, :score)", tablename=userInfo['username'], post_text=post_text, score=str(ans))
        if (ans < 0.4):
            score = (0.4 - ans)
            total = "{:.2f}".format(userInfo['total'] + score)
            good_score = "{:.2f}".format(userInfo['score'] + score)
            db.execute("UPDATE users SET score=:score, total=:total WHERE id=:user_id", score = good_score, total = total, user_id = session["user_id"])
            return redirect("/")
        else:
            score = (ans - 0.4)
            total = "{:.2f}".format((userInfo['total'] + score))
            db.execute("UPDATE users SET total=:total WHERE id=:user_id", total = total, user_id = session["user_id"])
            return redirect("/")
        


@home.route("/about", methods=["GET"])
@login_required
def about():
    return render_template("about.html")

def get_timestamp(post):
    return post.get('timestamp')

def add_publisher(posts, publisher):
    for item in posts:
        item["publisher"] = publisher
    return posts
