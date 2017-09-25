from sqlite3 import dbapi2 as sqlite

_ALBUMS_SQL = """\
CREATE TABLE ALBUMS (
  IDALBUM INTEGER NOT NULL PRIMARY KEY,
  ALBUM TEXT NOT NULL UNIQUE
)
"""

_SUBJECTS_SQL = """\
CREATE TABLE CATEGORIES (
  IDCATEGORY INTEGER NOT NULL PRIMARY KEY,
  SUBJECT TEXT NOT NULL 
)
"""

_PICTURES_SQL = """\
CREATE TABLE PICTURES (
  PATH TEXT NOT NULL PRIMARY KEY,
  NAME TEXT,
  AUTHOR TEXT,
  COMMENT TEXT,
  DATE INTEGER
)
"""

_PICTURES_ALBUMS_SQL = """\
CREATE TABLE PICTURES_ALBUMS (
  PICTURE TEXT NOT NULL,
  IDALBUM INTEGER NOT NULL
)
"""

connection = None

def init_collection(dbpath=None):
    if dbpath is None:
        import common, os
        dbpath = os.path.join(common.confdir, 'collection.db')
    con = sqlite.connect(dbpath)
    cur = con.cursor()
    try:
        cur.execute(_ALBUMS_SQL)
        cur.execute(_SUBJECTS_SQL)
        cur.execute(_PICTURES_SQL)
        cur.execute(_PICTURES_ALBUMS_SQL)
        con.commit()
    except sqlite.Error:
        import traceback; traceback.print_exc()
        pass
    return con


def get_connection():
    global connection
    if connection is None:
        connection = init_collection()
    return connection

def _quote(str):
    return str.replace("'", r"\'")


def query(parameters):
    allowed = set(['author', 'name', 'album'])

    print('query', parameters)
    try:
        connection = get_connection()
        cur = connection.cursor()
        condition = ''
        for key, val in parameters.items():
            if key.lower() not in allowed:
                continue
            if condition:
                condition += " AND %s = '%s' " % (key, _quote(val))
            else:
                condition = " WHERE %s = '%s' " % (key, _quote(val))
        sql = """SELECT PATH, NAME FROM PICTURES LEFT JOIN (PICTURES_ALBUMS
        INNER JOIN ALBUMS ON PICTURES_ALBUMS.IDALBUM = ALBUMS.IDALBUM) AS PA
        ON PICTURES.PATH = PA.PICTURE 
        %s ORDER BY NAME""" % condition
        print('executing query:', sql)
        cur.execute(sql)
        res = cur.fetchall()
        cur.close()
        return res
    except:
        import traceback
        traceback.print_exc()


def get_albums():
    con = get_connection()
    sql = "SELECT * FROM ALBUMS ORDER BY ALBUM"
    cur = con.cursor()
    cur.execute(sql)
    res = cur.fetchall()
    cur.close()
    return res


def add_album(album):
    con = get_connection()
    cur = con.cursor()
    try:
        sql = "SELECT MAX(IDALBUM) FROM ALBUMS"
        cur.execute(sql)
        res = cur.fetchone()
        if res is None or res[0] is None:
            albumid = 1
        else:
            albumid = res[0]+1
        sql = "INSERT INTO ALBUMS VALUES (%s, '%s')" % (albumid, _quote(album))
        cur.execute(sql)
        con.commit()
        cur.close()
        return albumid
    except:
        cur.close()
        import traceback; traceback.print_exc()
        return 0


def add_to_album(pictures, albumid):
    con = get_connection()
    cur = con.cursor()
    sql = "INSERT INTO PICTURES_ALBUMS VALUES('%s', %s)"
    for path in pictures:
        cur.execute("SELECT * FROM PICTURES WHERE PATH='%s'" % _quote(path))
        res = cur.fetchone()
        if res is None:
            import fileops
            cur.execute("""INSERT INTO PICTURES(PATH, NAME) VALUES
            ('%s', '%s')""" % (_quote(path), _quote(fileops.basename(path))))
        cur.execute(sql % (_quote(path), albumid))
    con.commit()


def remove_from_album(pictures, albumid):
    con = get_connection()
    cur = con.cursor()
    sql = "DELETE FROM PICTURES_ALBUMS WHERE PICTURE='%s' AND IDALBUM=%s"
    for path in pictures:
        cur.execute(sql % (_quote(path), albumid))
    con.commit()


def remove_from(params, pictures):
    assert 'album' in params and len(params) == 1, \
           "sorry, at the moment only removal from album implemented..."
    con = get_connection()
    cur = con.cursor()
    sql = "SELECT IDALBUM FROM ALBUMS WHERE ALBUM='%s'" % \
          _quote(params['album'])
    cur.execute(sql)
    res = cur.fetchone()
    assert res is not None, "No album with name '%s'" % params['album']
    remove_from_album(pictures, res[0])


def remove_album(albumid):
    con = get_connection()
    cur = con.cursor()
    sql = "DELETE FROM PICTURES_ALBUMS WHERE IDALBUM=%s" % albumid
    cur.execute(sql)
    sql = "DELETE FROM ALBUMS WHERE IDALBUM=%s" % albumid
    cur.execute(sql)
    con.commit()


def rename_album(albumid, newname):
    try:
        con = get_connection()
        cur = con.cursor()
        sql = "UPDATE ALBUMS SET ALBUM='%s' WHERE IDALBUM=%s" % \
              (newname, albumid)
        cur.execute(sql)
        con.commit()
        cur.close()
        return True
    except:
        cur.close()
        import traceback; traceback.print_exc()
        return False
