import psycopg

def get_connection():
    # set search_path = data
    conn = psycopg.connect(
        host="ok-db-1.cmqzhxowhqdn.ap-southeast-1.rds.amazonaws.com",
        database="datacrawl",
        user="app_user",
        password="")
    return conn
