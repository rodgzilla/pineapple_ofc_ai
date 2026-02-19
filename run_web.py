"""Launch the Pineapple OFC web interface."""
from src.web.app import app

if __name__ == '__main__':
    print("Starting Pineapple OFC at http://localhost:5000")
    app.run(debug=False, host='0.0.0.0', port=5000)
