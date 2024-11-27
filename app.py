from flask import Flask, render_template, url_for
import os

app = Flask(__name__)

REPORTS_FOLDER = os.path.join(app.static_folder, 'reports')


@app.route("/")
def index():
    reports = [
        file for file in os.listdir(REPORTS_FOLDER) if file.endswith('.pdf')
    ]
    return render_template("index.html", reports=reports)


if __name__ == "__main__":
    app.run(debug=True)
