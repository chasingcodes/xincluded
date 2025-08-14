import sqlite3
from werkzeug.security import generate_password_hash

def create_tables():
    conn = sqlite3.connect("races.db")
    db = conn.cursor()

    # Create ADMIN table
    db.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            hash TEXT NOT NULL
        );
    """)

    # Create RACES table
    db.execute("""
        CREATE TABLE IF NOT EXISTS races (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            event_type TEXT NOT NULL,
            location TEXT NOT NULL,
            distance TEXT NOT NULL,  
            description TEXT,
            nb_registration TEXT,    
            nb_awards TEXT,          
            bathrooms TEXT,                
            chosen_name TEXT,           
            pronouns TEXT,             
            trans_policy TEXT,
            registration_link TEXT
        );
    """)

    # Create FEEDBACK table
    db.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            race_id INTEGER NOT NULL,
            name_of_race TEXT NOT NULL,
            name_of_user TEXT,
            feedback_raw TEXT NOT NULL,
            feedback_public TEXT,
            approved BOOLEAN NOT NULL DEFAULT 0,
            FOREIGN KEY(race_id) REFERENCES races(id)
        );
    """)

    # Create SUGGESTIONS table
    db.execute("""
        CREATE TABLE IF NOT EXISTS suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            race_name TEXT NOT NULL,             
            race_link TEXT NOT NULL,                     
            comment TEXT NOT NULL,                        
            archived BOOLEAN DEFAULT 0
        );
    """)

    conn.commit()
    conn.close()

def create_admin_user():
    """Create a hardcoded admin user"""
    conn = sqlite3.connect("races.db")
    db = conn.cursor()
    
    # Hardcoded admin credentials
    admin_email = "test@example.com"
    admin_password = "admin123"  # Change this to your desired password
    
    # Hash the password
    password_hash = generate_password_hash(admin_password)
    
    # Check if admin already exists
    existing_admin = db.execute("SELECT * FROM admin WHERE email = ?", (admin_email,)).fetchone()
    
    if not existing_admin:
        # Insert the admin user
        db.execute("INSERT INTO admin (email, hash) VALUES (?, ?)", (admin_email, password_hash))
        conn.commit()
        print(f"Admin user created: {admin_email}")
    else:
        print(f"Admin user already exists: {admin_email}")
    
    conn.close()

if __name__ == "__main__":
    create_tables()
    create_admin_user()
    print("Database and tables created!")

