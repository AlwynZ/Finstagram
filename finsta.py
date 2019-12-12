#Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect
import os
import time
import hashlib
import pymysql.cursors

#Mandatory Features: View photos, view further photo info etc., post photos, Manage Follows (1, 2, 3, 4)
#extra features: search by tag, search by poster (11 & 12)

#Initialize the app from Flask
app = Flask(__name__)
IMAGES_DIR = os.path.join(os.getcwd(), "images")
salt = 'cs3083'

#Configure MySQL
conn = pymysql.connect(host='localhost',
                       port = 3306,
                       user='root',
                       password='',
                       db='finsta',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)

#Define a route to hello function
@app.route('/')
def hello():
    return render_template('index.html')

#Define route for login
@app.route('/login')
def login():
    return render_template('login.html')

#Define route for register
@app.route('/register')
def register():
    return render_template('register.html')

#Authenticates the login
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    #grabs information from the forms
    username = request.form['username']
    password = request.form['password'] + salt
    hashWord = hashlib.sha256(password.encode('utf-8')).hexdigest()


    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM person WHERE username = %s and password = %s'
    cursor.execute(query, (username, hashWord))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    cursor.close()
    error = None
    if(data):
        #creates a session for the the user
        #session is a built in
        session['username'] = username
        return redirect(url_for('home'))
    else:
        #returns an error message to the html page
        error = 'Invalid login or username'
        return render_template('login.html', error=error)

#Authenticates the register
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    #grabs information from the forms
    username = request.form['username']
    password = request.form['password'] + salt
    hashWord = hashlib.sha256(password.encode('utf-8')).hexdigest()
    firstname = request.form['firstname']
    lastname = request.form['lastname']
    bio = request.form['bio']

    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM person WHERE username = %s'
    cursor.execute(query, (username))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    error = None
    if(data):
        #If the previous query returns data, then user exists
        error = "This user already exists"
        return render_template('register.html', error = error)
    else:
        ins = 'INSERT INTO Person VALUES(%s, %s, %s, %s, %s)'
        cursor.execute(ins, (username, hashWord, firstname, lastname, bio))
        conn.commit()
        cursor.close()
        return render_template('index.html')

@app.route('/home')
def home():
    user = session['username']
    return render_template('home.html', username=user)

#feature 1
@app.route("/feed", methods=["GET", "POST"])
def images():
    current_username = session['username']
    cursor = conn.cursor()
    #show images by users who have accepted follow requests and set AllFollowers = 1 on their image
    query = "SELECT photoID, photoPoster, filepath FROM photo JOIN person ON (username = photoPoster) WHERE photoPoster = %s OR photoID IN (SELECT DISTINCT photoID FROM photo JOIN follow ON (photoPoster = username_followed) WHERE (allFollowers = 1 AND username_follower = %s AND followStatus = 1)) ORDER BY postingdate DESC"    
    cursor.execute(query, (current_username, current_username))
    data = cursor.fetchall()
    cursor.close()
    return render_template("feed.html", photos=data)



#feature 2
@app.route("/image/<photoID>", methods=["GET", "POST"])
def image(photoID):
    
    #select photo 
    cursor = conn.cursor()
    query = "SELECT * FROM photo JOIN person WHERE photoID = %s AND photo.photoPoster = person.username"
    cursor.execute(query, photoID)
    photoData = cursor.fetchall()
    cursor.close()
    
    #get tagged users
    cursor = conn.cursor()
    query = "SELECT Tagged.username, Person.firstName, Person.lastName FROM Tagged NATURAL JOIN Person WHERE photoID = %s  AND Tagged.tagstatus = 1"
    cursor.execute(query, photoID)
    tag = cursor.fetchall()
    
    return render_template("image.html", photo=photoData, tags = tag)


@app.route('/upload_image', methods=['GET'])
def upload():
    return render_template("upload.html")


#feature 3
@app.route("/upload", methods=["POST"])
def upload_image():
    if request.files:
        image_file = request.files.get("imageToUpload", "")
        image_name = image_file.filename
        filepath = os.path.join(IMAGES_DIR, image_name)
        if request.form:
            requestData = request.form
            caption = requestData["caption"]
            allFollowers = 1
            if requestData.getlist('allFollowers') != []:
                allFollowers = 1
            image_file.save(filepath)
            query1 = "INSERT INTO Photo (postingdate, filepath, allFollowers, caption, photoPoster) VALUES (%s, %s, %s, %s, %s)"
            query2 = "SELECT photoID FROM Photo WHERE filepath = %s AND postingdate = %s"
            with conn.cursor() as cursor:
                cursor.execute(query1, (time.strftime('%Y-%m-%d %H:%M:%S'), image_name, allFollowers, caption, session["username"], ))
                cursor.execute(query2, (image_name, time.strftime('%Y-%m-%d %H:%M:%S')))
                data = cursor.fetchall()
                conn.commit()
            message = "Image successfully uploaded."
            #goes straight to tagging page
            return render_template("tag.html", photo = data, message=message)
    else:
        message = "Failed to upload image."
        return render_template("uploadphotos.html", message=message)

@app.route("/tag/<photoID>", methods=["GET", "POST"])
def tag(photoID):
    cursor = conn.cursor() 
    query = "INSERT INTO Tagged(username, photoID, tagstatus) VALUES(%s, %s, %s)"
    taggedUserString = request.form['username']
    taggedUserList = taggedUserString.split(" ")
    for username in taggedUserList:
        cursor.execute(query,(username, photoID, 1))
    conn.commit()
    cursor.close()
    return home()

#fEATURE 4 (follow management)


#go to page to enter username of person you wish to follow
@app.route("/followUser", methods=["GET", "POST"])
def follow():
    return render_template("follow.html")

    
#updates follow table with an entry with status = 0 when a request is made
@app.route("/sendFollowRequest", methods=["GET", "POST"])
def updateFollow():
    username_followed = request.form["username"]
    username_follower = session["username"]
    cursor = conn.cursor()
    
    query1 = "SELECT username_followed FROM follow WHERE username_follower = %s"
    cursor.execute(query1, username_follower)
    data = cursor.fetchall()
    
    if(data):
        for dict in data:
            username = dict["username_followed"]
            # checks if user_follower is already following user_followed
            if(username == username_followed):
                return render_template("follow.html", message="You are already following this user")

    # if the user hasn't followed then this code will execute
    query2 = "INSERT INTO Follow (username_followed, username_follower, followstatus) VALUES(%s, %s, %s)"
    cursor.execute(query2, (username_followed, username_follower, 0))
    conn.commit()
    cursor.close()
    return render_template("follow.html", message = "Follow request sent to " + username_followed)


#show unresolved follow requests the user has received
@app.route("/followRequest", methods=["GET", "POST"])
def followRequests():
    current_username = session["username"]
    cursor = conn.cursor()
    query = "SELECT username_follower FROM Follow WHERE username_followed = %s AND followstatus = 0"
    cursor.execute(query, current_username)
    data = cursor.fetchall()
    cursor.close()
    return render_template("followRequest.html", requests = data)   

    
#Update follow depending on whether followed user accepted or declined the follow request
@app.route("/followRequest/<username>/<status>", methods=["GET", "POST"])
def followRequestResolve(username, status):
    my_username = session["username"] 
    cursor = conn.cursor()
    if(status == "accept"):
        query = "UPDATE follow SET followstatus = 1 WHERE username_followed = %s AND username_follower = %s"
    else:
        query = "DELETE FROM follow WHERE username_followed = %s AND username_follower = %s"
    cursor.execute(query, (my_username, username))
    conn.commit()
    cursor.close()
    return redirect("/home")


#extra feature 11 (search by poster)
@app.route("/username", methods=["GET", "POST"])
def username():
    return render_template("searchByUser.html")

@app.route("/searchByUser", methods=["GET", "POST"])
def findUsername():
    poster = request.form['username']
    cursor = conn.cursor()
    query = "SELECT * FROM Photo WHERE photoPoster = %s"
    cursor.execute(query, poster)
    data = cursor.fetchall()
    cursor.close()
    if (data):
        return render_template("foundByUser.html", photos = data)
    else:
        return render_template("searchByUser.html", message = ("No images found posted by " + poster))




#extra feature 10 (search by tag)    
@app.route("/tagged", methods=["GET", "POST"])
def tagged():
    return render_template("searchByTag.html")

@app.route("/searchByTag", methods=["GET", "POST"])
def findTag():
    tagged = request.form['username']
    cursor = conn.cursor()
    query = "SELECT photoID FROM Tagged WHERE username = %s  AND tagstatus = 1"
    cursor.execute(query, tagged)
    data = cursor.fetchall()
    cursor.close()
    if (data):
        return render_template("foundByTag.html", photos = data)
    else:
        return render_template("searchByTag.html", message = ("No images found tagged with " + tagged))
    




@app.route('/logout')
def logout():
    session.pop('username')
    return redirect('/')
        

app.secret_key = 'some key that you will never guess'
#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug = True)
