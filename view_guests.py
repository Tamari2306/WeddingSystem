import sqlite3

def view_guests():
    conn = sqlite3.connect('guests.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM guests")
    guests = cursor.fetchall()
    
    for guest in guests:
        print(guest)

    conn.close()

view_guests()
