from flask import Flask, render_template, jsonify
from fetch_data import get_airplane_data

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/data")
def data():
    planes = get_airplane_data()
    return jsonify(planes)

if __name__ == "__main__":
    app.run(debug=True)
