from flask import Flask, render_template, redirect, url_for, session, g
from functools import wraps
from config import settings
from db import db, ping
from auth import auth_bp

app = Flask(__name__)
app.config.from_object(settings)

# register blueprint AFTER app is created
print(">>> registering auth blueprint")
app.register_blueprint(auth_bp)
print(">>> auth blueprint registered")

@app.get("/routes")
def routes():
    return {"routes": [rule.rule for rule in app.url_map.iter_rules()]}


# Global mock data
sample_user = {'username': 'JohnDoe'}

sample_categories = [
    {'id': 1, 'name': 'School'},
    {'id': 2, 'name': 'Personal'},
    {'id': 3, 'name': 'Shopping'}
]

sample_tasks = [
    {'id': 1, 'title': 'Complete project report', 'category': 'Work', 'status': 'In Progress', 'priority': 'High'},
    {'id': 2, 'title': 'Buy groceries', 'category': 'Shopping', 'status': 'Pending', 'priority': 'Medium'},
    {'id': 3, 'title': 'Call dentist', 'category': 'Personal', 'status': 'Pending', 'priority': 'Low'}
]

@app.route('/')
def home():
    return render_template('landing.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/add-task')
def add_task():
    return render_template('add_task.html', categories=sample_categories)

@app.route('/history')
def history():
    return render_template('todo_history.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', 
                         user=sample_user, 
                         categories=sample_categories, 
                         tasks=sample_tasks)

@app.get("/test")
def health():
    from db import ping
    return {"status": "ok", "db": "ok" if ping() else "down"}, 200

if __name__ == '__main__':
    app.run(debug=True, port=3000)