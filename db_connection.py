import psycopg2

def get_connection():
    # set search_path = data
    conn = psycopg2.connect(
        host="ok-db-1.cmqzhxowhqdn.ap-southeast-1.rds.amazonaws.com",
        database="datacrawl",
        user="postgres",
        password=">QyNVw6&")
    return conn
