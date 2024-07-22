from flask import Flask, redirect, render_template, request, session, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms, send

app = Flask(__name__)
app.config['SECRET_KEY'] = 'abcd'
socketio = SocketIO(app)

groups = {}

@app.route('/', methods=['POST', 'GET'])
def login():
    session.clear()
    if request.method == 'POST':
        session['email'] = request.form.get('email')
        session['userName'] = request.form.get('userName')
        session['city'] = request.form.get('city')

        return redirect(url_for('lobby'))

    return render_template('login.html')

@app.route('/lobby', methods=['POST', 'GET'])
def lobby():
    if request.method == 'POST':
        groupName = request.form.get('groupName')
        session['groupName'] = groupName

        if groupName in groups:
            return render_template('lobby.html', userName=session['userName'], error='Uma sala com este nome já existe')

        groups[session['groupName']] = {"members": 0, "messages": []}

        return redirect(url_for('grupo'))

    return render_template('lobby.html', userName=session['userName'], chats = groups.keys)

@app.route('/grupo')
def grupo():
    if session is None:
        return redirect(url_for("login"))
    
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
        "message": data["data"]
    }
    send(content, to=groupName)
    groups[groupName]["messages"].append(content)
    print(f"{session.get('userName')} said: {data['data']} [chat = {groupName}]")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0',  port=5000)