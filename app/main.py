from flask import Flask

app = Flask(__name__)

if __name__ == "__main__":
    # Use 0.0.0.0 to make the server accessible from outside the container
    app.run(host="0.0.0.0", port=8080, debug=True)
