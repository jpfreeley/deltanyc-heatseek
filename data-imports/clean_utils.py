from utils import connect

def clean_addresses(table, column):
    """ Returns a SQL statement cleaning an address column.
        |table| and |column| are both strings.
    """
    # One line missing:
    #    UPDATE {table} SET {column} = array_to_string(regexp_matches('(.*)(\d+)(?:TH|RD|ND|ST)( .+)'), '', {column} ) WHERE {column} ~ '.*(\d+)(?:TH|RD|ND|ST)( .+).*';
    # No idea where regexp_matches is defined? Looks like it's a Postgresql command?
    return '''
    UPDATE {table} SET {column} = TRIM({column});
    UPDATE {table} SET {column} = preg_replace( '/\\\./', '', {column} );
    UPDATE {table} SET {column} = preg_replace( '/, MANHATTAN|, BROOKLYN|, STATEN ISLAND|, QUEENS|, BRONX/i', '', {column} );
    UPDATE {table} SET {column} = preg_replace( '/ AVE$|-AVE$| -AVE$/', ' AVENUE', {column} );
    UPDATE {table} SET {column} = preg_replace( '/ LA$/', ' LANE', {column} );
    UPDATE {table} SET {column} = preg_replace( '/ LN$/', ' LANE', {column} );
    UPDATE {table} SET {column} = preg_replace( '/ PL$/', ' PLACE', {column} );
    UPDATE {table} SET {column} = preg_replace( '/ ST$| STR$/', ' {column}', {column} );
    UPDATE {table} SET {column} = preg_replace( '/ RD$/', ' ROAD', {column} );
    UPDATE {table} SET {column} = preg_replace( '/ PKWY$/', 'PARKWAY', {column} );
    UPDATE {table} SET {column} = preg_replace( '/ PKWY /', ' PARKWAY ', {column} );
    UPDATE {table} SET {column} = preg_replace( '/ BLVD$/', ' BOULEVARD', {column} );
    UPDATE {table} SET {column} = preg_replace( '/ BLVD /', ' BOULEVARD ', {column} );
    UPDATE {table} SET {column} = preg_replace( '/ BLVD/', ' BOULEVARD ', {column} );
    UPDATE {table} SET {column} = preg_replace( '/^BCH /', 'BEACH ', {column} );
    UPDATE {table} SET {column} = preg_replace( '/^E /', 'EAST ', {column} );
    UPDATE {table} SET {column} = preg_replace( '/^W /', 'WEST ', {column} );
    UPDATE {table} SET {column} = preg_replace( '/^N /', 'NORTH ', {column} );
    UPDATE {table} SET {column} = preg_replace( '/^S /', 'SOUTH ', {column} );
    '''.format(table=table, column=column)


def full_name_boro_replacements():
    """ Standard replacement dict for use in clean_boro.
    """
    return {"mn": "MANHATTAN", "bk": "BROOKLYN", "si": "STATEN ISLAND",
            "qn": "QUEENS", "bx": "BRONX"}

def bbl_code_boro_replacements():
    """ Replacement dict for use in clean_boro modifying borough codes used in BBL.
    """
    return {"mn": "1", "bk": "3", "si": "5",
            "qn": "4", "bx": "2"}


def clean_boro(table, column, replacements):
    """ Retuns an SQL statement that cleans up borough columns.
        |replacements| is a dict mapping the cleaned borough codes (mn, bk, si, qn, bx)
        to the unclean borough codes. The case of the unclean codes does not matter.
        Cleaned codes match those used in PLUTO.
    """
    return '''
    UPDATE {table} SET {column} = preg_replace('/{mn}/i', 'MN', {column});
    UPDATE {table} SET {column} = preg_replace('/{bk}/i', 'BK', {column});
    UPDATE {table} SET {column} = preg_replace('/{si}/i', 'SI', {column});
    UPDATE {table} SET {column} = preg_replace('/{qn}/i', 'QN', {column});
    UPDATE {table} SET {column} = preg_replace('/{bx}/i', 'BX', {column});
    '''.format(table=table, column=column, mn=replacements["mn"], bk=replacements["bk"],
            si=replacements["si"], qn=replacements["qn"], bx=replacements["bx"])

def make_primary(table, column, data_type="INT"):
    """ Returns an SQL statement that makes a given column the primary key.
    """
    return "ALTER TABLE {} MODIFY {} {} PRIMARY KEY;".format(table, column, data_type)

def make_index(table, column):
    """ Returns an SQL statement that makes an index on the given column.
    """
    return "ALTER TABLE {} ADD INDEX {};".format(table, column)

def column_exists(table, column, schema='deltanyc'):

    sql = """
        SELECT column_name FROM information_schema.columns WHERE
            table_schema = '{schema}'
            AND table_name = '{table}'
            AND column_name = '{column}'
        """.format(schema=schema, table=table, column=column)

    result = connect().execute(sql)

    return (result.rowcount == 1)

def clean_bbl(table, boro, block, lot):
    sql = '''
    UPDATE {table} SET {block} = REPLACE({block}, ' ', 0);
    UPDATE {table} SET {block} = REPLACE({block}, '`', '');
    UPDATE {table} SET {lot} = REPLACE({lot}, ' ', 0);
    UPDATE {table} SET bbl =
            concat(trim({boro}), trim(LPAD({block}, 5, '0')), trim(LPAD({lot}, 4, '0')))
            WHERE {boro} REGEXP '^[0-9]+$' AND {block} REGEXP '^[0-9]+$' AND {lot} REGEXP '^[0-9]+$';
    ALTER TABLE {table} ADD INDEX (bbl);
    '''.format(table=table, boro=boro, block=block, lot=lot)

    if not column_exists(table, 'bbl'):
        sql = "ALTER TABLE {table} ADD COLUMN bbl bigint(13) NULL DEFAULT NULL;".format(table=table, boro=boro, block=block, lot=lot) + sql

    return sql

def run_sql(sql, test_mode, debug=True):
    """ Runs SQL commands given in the provided string.
        The string can contain multiple statements.
    """
    if debug:
        print(sql)

    engine = connect(test_mode)
    connection = engine.raw_connection()
    cursor = connection.cursor()

    for result in cursor.execute(sql, multi=True):
        pass

    cursor.close()
    connection.connection.commit()
    connection.close()