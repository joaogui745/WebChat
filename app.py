import os
import pathlib

from flask import (Flask, flash, redirect, render_template, request, send_file,
                   session, url_for)
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms, send
from werkzeug.utils import secure_filename

path = pathlib.Path(__file__).parent.resolve()
UPLOAD_FOLDER = path / "files"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp3'}

app = Flask(__name__)
app.config['SECRET_KEY'] = 'abcd'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

socketio = SocketIO(app)

groups = {}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['POST', 'GET'])
def login():
    session.clear()
    if request.method == 'POST':
        session['email'] = request.form.get('email')
        session['userName'] = request.form.get('userName')
        session['city'] = request.form.get('city')

        return redirect(url_for('lobby'))

    return render_template('login.html')

@app.route('/downloads')
def downloadFile():
    fileName = request.args.get('fileName')
    path = pathlib.Path(__file__).parent.resolve()
    print(path / "files" / fileName)
    return send_file(path / "files" / fileName, as_attachment=True)

@app.route('/lobby', methods=['POST', 'GET'])
def lobby():
    if request.method == 'POST':
        groupName = request.form.get('groupName')
        session['groupName'] = groupName

        if groupName in groups:
            return render_template('lobby.html', userName=session['userName'], error='Uma sala com este nome já existe')

        groups[session['groupName']] = {"members": 0, "messages": []}

        return redirect(url_for('grupo'))

    return render_template('lobby.html', userName=session['userName'], chats = list(groups.keys()))

@app.route('/grupo', methods=['GET', 'POST'])
def grupo():
    if session is None:
        return redirect(url_for("login"))
    
    if request.method == 'POST':
            if 'file' not in request.files:
                flash('No file part')
                return redirect(request.url)
            file = request.files['file']
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    else:
        return render_template('grupo.html', groupName = session['groupName'])

@socketio.on("connect")
def connect():
    groupName = session.get("groupName")
    userName = session.get("userName")
    if not groupName or not userName:
        return
    if groupName not in groups:
        leave_room(groupName)
        return
    
    join_room(groupName)
    send({"userName": userName, "message": "entrou no grupo"}, to=groupName)
    groups[groupName]["members"] += 1
    print(f"{userName} entrou no grupo {groupName}")

@socketio.on("disconnect")
def disconnect():
    groupName = session.get("groupName")
    userName = session.get("userName")
    leave_room(groupName)

    if groupName in groups:
        groups[groupName]["members"] -= 1
        if groups[groupName]["members"] <= 0:
            del groups[groupName]
    
    send({"userName": userName, "message": "saiu do grupo"}, to=groupName)
    print(f"{userName} saiu do grupo {groupName}")

@socketio.on("message")
def message(data):
    
    groupName = session.get("groupName")
    
    if groupName not in groups:
        return 
    
    content = {
        "userName": session.get("userName"),
        "message": data["data"][0],
        "isFile": data["data"][1]
    }
    send(content, to=groupName)
    groups[groupName]["messages"].append(content)
    print(f"{session.get('userName')} said: {data['data']} [chat = {groupName}]")

if __name__ == '__main__':
    socketio.run(app, debug=True)