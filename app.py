from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('landing.html')

@app.route('/login')
def login():
    return render_template('todo_login.html')

@app.route('/add-task')
def add_task():
    return render_template('todo_add_task.html')

@app.route('/history')
def history():
    return render_template('todo_history.html')

if __name__ == '__main__':
    app.run(debug=True, port=3000)
