import sqlite3
from urllib.parse import urlparse

class DatabaseHandler:
    def __init__(self, db_path='job_data.db'):
        self.db_path = db_path
        self.connection = sqlite3.connect(self.db_path)
        self.create_tables()

    def create_tables(self):
        with self.connection:
            # Create the job_data table with a scraped_at timestamp
            self.connection.execute('''
                CREATE TABLE IF NOT EXISTS job_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    host TEXT NOT NULL,
                    css_selectors_json TEXT NOT NULL,
                    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Create the urls table with a foreign key to job_data
            self.connection.execute('''
                CREATE TABLE IF NOT EXISTS urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    job_data_id INTEGER,
                    html TEXT,
                    FOREIGN KEY (job_data_id) REFERENCES job_data(id)
                )
            ''')

            # Create the job table with a created_at timestamp
            self.connection.execute('''
                CREATE TABLE IF NOT EXISTS job (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url_id INTEGER NOT NULL,
                    job_data_id INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    description TEXT,
                    title TEXT,
                    company TEXT,
                    FOREIGN KEY (job_data_id) REFERENCES job_data(id),
                    FOREIGN KEY (url_id) REFERENCES urls(id)
                )
            ''')
    def save_data(self, url, css_selectors_json, html):
        # Extract host from URL
        parsed_url = urlparse(url)
        host = parsed_url.netloc

        with self.connection:
            # Check if the host already exists in job_data
            cursor = self.connection.cursor()
            cursor.execute('SELECT id FROM job_data WHERE host = ?', (host,))
            job_data_id = cursor.fetchone()

            if job_data_id:
                # Update the css_selectors_json if necessary
                cursor.execute('''
                    UPDATE job_data SET css_selectors_json = ?
                    WHERE id = ? AND css_selectors_json IS NULL
                ''', (css_selectors_json, job_data_id[0]))
                job_data_id = job_data_id[0]
            else:
                # Insert the job data
                cursor.execute('''
                    INSERT INTO job_data (host, css_selectors_json)
                    VALUES (?, ?)
                ''', (host, css_selectors_json))
                job_data_id = cursor.lastrowid

            # Check if the URL already exists in urls
            cursor.execute('SELECT id FROM urls WHERE url = ?', (url,))
            url_id = cursor.fetchone()

            if url_id:
                # Update the html if necessary
                cursor.execute('''
                    UPDATE urls SET html = ?
                    WHERE id = ? AND html IS NULL
                ''', (html, url_id[0]))
            else:
                # Insert the URL with the job_data ID
                cursor.execute('''
                    INSERT INTO urls (url, job_data_id, html) VALUES (?, ?, ?)
                ''', (url, job_data_id, html))

    def save_job_description(self, job, job_data_id, url_id):
        title = job["title"]
        description = job["description"]
        company = job["company"]

        with self.connection:
            cursor = self.connection.cursor()
            
            # Check if the job title and company already exist
            cursor.execute('''
                SELECT id FROM job WHERE title = ? AND company = ?
            ''', (title, company))
            existing_job = cursor.fetchone()

            if existing_job:
                # Optionally, update the existing job description if needed
                cursor.execute('''
                    UPDATE job SET description = ?, url_id = ?, job_data_id = ?
                    WHERE id = ?
                ''', (description, url_id, job_data_id, existing_job[0]))
            else:
                # Insert the new job description
                cursor.execute('''
                    INSERT INTO job (job_data_id, url_id, title, description, company)
                    VALUES (?, ?, ?, ?, ?)
                ''', (job_data_id, url_id, title, description, company))

    def fetch_parser_from_url(self, url):
        # Extract host from URL
        parsed_url = urlparse(url)
        host = parsed_url.netloc

        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT jd.id as job_data_id, jd.css_selectors_json, u.id as url_id, u.url, u.html FROM job_data jd
            JOIN urls u ON jd.id = u.job_data_id
            WHERE u.url = ? AND jd.host = ?
        ''', (url, host))
        result = cursor.fetchone()
        return result if result else None

    def close(self):
        self.connection.close()
