#!/usr/bin/env python3
"""
Simple Database Editor for Race Directory
Usage: python simple_db_editor.py
"""

import sqlite3
import sys

def connect_db():
    """Connect to the races database"""
    try:
        conn = sqlite3.connect("races.db")
        conn.row_factory = sqlite3.Row  # Access columns by name
        return conn
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)

def show_race(race_id):
    """Display a specific race"""
    conn = connect_db()
    cursor = conn.cursor()
    
    race = cursor.execute("SELECT * FROM races WHERE id = ?", (race_id,)).fetchone()
    
    if not race:
        print(f"Race with ID {race_id} not found.")
        conn.close()
        return
    
    print(f"\n--- Race ID: {race['id']} ---")
    print(f"Name: {race['name']}")
    print(f"Location: {race['location']}")
    print(f"NB Registration: {race['nb_registration']}")
    print(f"NB Awards: {race['nb_awards']}")
    print(f"Bathrooms: {race['bathrooms']}")
    print(f"Chosen Name: {race['chosen_name']}")
    print(f"Pronouns: {race['pronouns']}")
    print(f"Trans Policy: {race['trans_policy']}")
    
    conn.close()

def update_race_field(race_id, field, new_value):
    """Update a specific field for a race"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Valid fields that can be updated
    valid_fields = ['name', 'event_type', 'location', 'distance', 'description', 
                   'nb_registration', 'nb_awards', 'bathrooms', 'chosen_name', 
                   'pronouns', 'trans_policy', 'registration_link']
    
    if field not in valid_fields:
        print(f"Invalid field: {field}")
        print(f"Valid fields: {', '.join(valid_fields)}")
        conn.close()
        return
    
    try:
        cursor.execute(f"UPDATE races SET {field} = ? WHERE id = ?", (new_value, race_id))
        
        if cursor.rowcount == 0:
            print(f"Race with ID {race_id} not found.")
        else:
            print(f"Updated race {race_id}: {field} = '{new_value}'")
            conn.commit()
            
    except sqlite3.Error as e:
        print(f"Error updating race: {e}")
    
    conn.close()

def delete_race(race_id):
    """Delete a race (with confirmation)"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Show the race first
    race = cursor.execute("SELECT name FROM races WHERE id = ?", (race_id,)).fetchone()
    
    if not race:
        print(f"Race with ID {race_id} not found.")
        conn.close()
        return
    
    print(f"Are you sure you want to delete race {race_id}: '{race['name']}'?")
    confirm = input("Type 'yes' to confirm: ").strip().lower()
    
    if confirm == 'yes':
        try:
            cursor.execute("DELETE FROM races WHERE id = ?", (race_id,))
            print(f"Deleted race {race_id}: '{race['name']}'")
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error deleting race: {e}")
    else:
        print("Deletion cancelled.")
    
    conn.close()

def list_races():
    """List all races with their IDs"""
    conn = connect_db()
    cursor = conn.cursor()
    
    races = cursor.execute("SELECT id, name, location FROM races ORDER BY id").fetchall()
    
    if not races:
        print("No races found.")
    else:
        print("\n--- All Races ---")
        for race in races:
            print(f"ID: {race['id']} | {race['name']} | {race['location']}")
    
    conn.close()

def main():
    """Main interactive menu"""
    while True:
        print("\n=== Race Database Editor ===")
        print("1. List all races")
        print("2. Show specific race")
        print("3. Update race field")
        print("4. Delete race")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == '1':
            list_races()
            
        elif choice == '2':
            try:
                race_id = int(input("Enter race ID: ").strip())
                show_race(race_id)
            except ValueError:
                print("Invalid race ID. Please enter a number.")
                
        elif choice == '3':
            try:
                race_id = int(input("Enter race ID: ").strip())
                field = input("Enter field name (e.g., nb_registration): ").strip()
                new_value = input("Enter new value: ").strip()
                update_race_field(race_id, field, new_value)
            except ValueError:
                print("Invalid race ID. Please enter a number.")
                
        elif choice == '4':
            try:
                race_id = int(input("Enter race ID to delete: ").strip())
                delete_race(race_id)
            except ValueError:
                print("Invalid race ID. Please enter a number.")
                
        elif choice == '5':
            print("Goodbye!")
            break
            
        else:
            print("Invalid choice. Please enter 1-5.")

if __name__ == "__main__":
    main()
