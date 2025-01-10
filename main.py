import matplotlib
matplotlib.use('Agg')  # Gunakan backend non-interaktif
from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io
import base64


# 1. Database Setup
def setup_database():
    conn = sqlite3.connect('uploads.db')
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS uploads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        admin_id TEXT,
                        timestamp DATETIME,
                        num_images INTEGER
                     )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS interactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        admin_id TEXT,
                        timestamp DATETIME,
                        num_comments INTEGER,
                        num_reactions INTEGER
                     )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS behaviors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        admin_id TEXT,
                        timestamp DATETIME,
                        activity_type TEXT,
                        details TEXT
                     )''')

    conn.commit()
    conn.close()

setup_database()

# 2. Flask App Setup
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_upload', methods=['POST'])
def add_upload():
    admin_id = request.form['admin_id']
    num_images = request.form['num_images']
    if admin_id and num_images:
        conn = sqlite3.connect('uploads.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO uploads (admin_id, timestamp, num_images) 
                          VALUES (?, ?, ?)''', (admin_id, datetime.now(), int(num_images)))
        cursor.execute('''INSERT INTO behaviors (admin_id, timestamp, activity_type, details) 
                          VALUES (?, ?, ?, ?)''', (admin_id, datetime.now(), "upload", f"Uploaded {num_images} images"))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/add_interaction', methods=['POST'])
def add_interaction():
    admin_id = request.form['admin_id']
    num_comments = request.form['num_comments']
    num_reactions = request.form['num_reactions']
    if admin_id and num_comments and num_reactions:
        conn = sqlite3.connect('uploads.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO interactions (admin_id, timestamp, num_comments, num_reactions) 
                          VALUES (?, ?, ?, ?)''', (admin_id, datetime.now(), int(num_comments), int(num_reactions)))
        cursor.execute('''INSERT INTO behaviors (admin_id, timestamp, activity_type, details) 
                          VALUES (?, ?, ?, ?)''', (admin_id, datetime.now(), "interaction", f"{num_comments} comments and {num_reactions} reactions"))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/add_behavior', methods=['POST'])
def add_behavior():
    admin_id = request.form['admin_id']
    activity_type = request.form['activity_type']
    details = request.form['details']
    if admin_id and activity_type and details:
        conn = sqlite3.connect('uploads.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO behaviors (admin_id, timestamp, activity_type, details) 
                          VALUES (?, ?, ?, ?)''', (admin_id, datetime.now(), activity_type, details))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/summary')
def summary():
    conn = sqlite3.connect('uploads.db')
    cursor = conn.cursor()

    # Calculate the date 7 days ago
    seven_days_ago = (datetime.now() - timedelta(days=6)).strftime('%Y-%m-%d')

    # Fetch data from the last 7 days, ordered by date
    cursor.execute('''SELECT admin_id, COUNT(*), SUM(num_images), strftime('%Y-%m-%d', timestamp) 
                      FROM uploads 
                      WHERE timestamp >= ? 
                      GROUP BY admin_id, strftime('%Y-%m-%d', timestamp) 
                      ORDER BY strftime('%Y-%m-%d', timestamp) ASC''', (seven_days_ago,))
    reports = cursor.fetchall()

    dates = []
    total_uploads_list = []
    total_images_list = []

    for report in reports:
        admin_id, total_uploads, total_images, upload_date = report
        dates.append(upload_date)
        total_uploads_list.append(total_uploads)
        total_images_list.append(total_images)

    # Sort data by date
    sorted_data = sorted(zip(dates, total_uploads_list, total_images_list), key=lambda x: x[0])
    dates, total_uploads_list, total_images_list = zip(*sorted_data) if sorted_data else ([], [], [])

    # Generate graph
    img = io.BytesIO()
    if dates:
        plt.figure(figsize=(10, 5))
        plt.bar(dates, total_images_list, color='blue', alpha=0.7, label='Total Images')
        plt.bar(dates, total_uploads_list, color='orange', alpha=0.7, label='Total Uploads')
        plt.xlabel('Upload Date')
        plt.ylabel('Count')
        plt.title('Last 7 Days Upload Summary')
        plt.xticks(rotation=45, ha='right')
        plt.legend()
        plt.tight_layout()
        plt.savefig(img, format='png')
        plt.close()
    img.seek(0)
    graph_url = base64.b64encode(img.getvalue()).decode()
    graph_url = f"data:image/png;base64,{graph_url}"

    # Fetch all data from behaviors
    cursor.execute('''SELECT admin_id, activity_type, details, timestamp 
                      FROM behaviors 
                      WHERE timestamp >= ? 
                      ORDER BY timestamp''', (seven_days_ago,))
    behaviors = cursor.fetchall()

    conn.close()

    return render_template('summary.html', reports=reports, graph_url=graph_url, behaviors=behaviors)

if __name__ == '__main__':
    app.run(debug=True, threaded=True, port=5001)
