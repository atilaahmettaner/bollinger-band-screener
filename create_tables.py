import os
from flask import Flask
from models import db, Subscriber
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create a minimal Flask app
app = Flask(__name__)

# Configure the PostgreSQL connection
db_url = os.environ.get('DATABASE_URL', 'postgresql://localhost/crypto_scanner')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db.init_app(app)

if __name__ == "__main__":
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully")
        
        # Check if the subscriber table exists
        result = db.session.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='subscriber')")
        table_exists = next(result)[0]
        
        if table_exists:
            print("Subscriber table exists")
            
            # Count subscribers
            result = db.session.execute("SELECT COUNT(*) FROM subscriber")
            count = next(result)[0]
            print(f"Total subscribers: {count}")
        else:
            print("Subscriber table does not exist") 