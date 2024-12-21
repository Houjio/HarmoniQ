from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return "Bienvenue à HarmoniQ"

if __name__ == '__main__':
    app.run()
