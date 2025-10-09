from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Flask is running successfully! Your project is set up."

if __name__ == '__main__':
    app.run(debug=True)
