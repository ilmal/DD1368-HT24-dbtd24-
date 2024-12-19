import psycopg2

"""
Note: It's essential never to include database credentials in code pushed to GitHub. 
Instead, sensitive information should be stored securely and accessed through environment variables or similar. 
However, in this particular exercise, we are allowing it for simplicity, as the focus is on a different aspect.
Remember to follow best practices for secure coding in production environments.
"""

# Acquire a connection to the database by specifying the credentials.
conn = psycopg2.connect(
    host="localhost", 
    database="dbas",
    user="dbas",
    password="pass123")
print(conn)

# Create a cursor. The cursor allows you to execute database queries.
cur = conn.cursor()

def search_airports():
    airport = input("Please enter an airport (iata code or name): ")
    query = f"SELECT name, iatacode, country FROM airport WHERE name ILIKE %s OR iatacode ILIKE %s"
    try: 
        cur.execute(query, (f"%{airport}%", f"%{airport}%"))
        result = cur.fetchall()
        print("\n")
        print(result, end="\n")
    except: 
        print("No results found.")

def find_speakers_of_language():
    language = input("Please enter a language: ").lower().title()
    query = f"""
    WITH speakers AS (
        SELECT 
            s.language,
            c.name AS country_name,
            CAST(SUM(c.population * (s.percentage/100)) AS INTEGER) AS speakers
        FROM 
            spoken s
        JOIN 
            country c ON c.code = s.country
        WHERE 
            c.population IS NOT NULL 
            AND s.percentage IS NOT NULL 
        GROUP BY
            s.language, c.name
        ORDER BY
            s.language ASC
    )

    SELECT
        sp.country_name,
        sp.speakers
    FROM 
        speakers sp
    WHERE 
        sp.language = %s
    ORDER BY
        sp.country_name ASC
    ;
    """
    try:
        cur.execute(query, (language, ))
        results = cur.fetchall()
        print("\n")
        for result in results:
            print("NAME: ", result[0], end="  |  ")
            print("SPEAKERS: ", result[1]) 
    except:
        print("No results found.")

def create_desert():
    desert_country = input("Please enter the country: ").lower().title()
    desert_province = input("\nPlease enter a province: ").lower().title()

    # query to find if location is valid
    find_location = f"""
    SELECT 
        p.name 
    FROM 
        province p
    JOIN
        country c ON c.code = p.country
    WHERE 
        p.name= %s 
        AND c.name= %s;    
    """
    cur.execute(find_location, (desert_province, desert_country))
    location_exists = cur.fetchall()

    # if location doesnt exist
    if len(location_exists) == 0:
        print("\nLocation not found")
        return
    
    # more user inputs
    desert_area = input("\nPlease enter area size of desert: ")
    desert_latitude = input("\nPlease enter X-coordinate of geocoords: ")
    desert_longitude = input("\nPlease enter Y-coordinate of geocoords: ")
    desert_name = input("\nPlease state the name of your desert: ")
    desert_country_code = convert_countryname_to_code(desert_country)

     # Check constraints
    try:
        check_desert_constraints(desert_name, desert_country, desert_province, desert_area)
    except ValueError as e:
        print(f"Constraint violation: {e}")
        return

    # Ensure the result is properly handled (e.g., it returns a list of tuples)
    if desert_country_code:
        desert_country_code = desert_country_code[0][0]  # Extract the code from the first tuple
    else:
        raise ValueError(f"Country '{desert_country}' not found in the database.")

    find_geodesert = """
    SELECT desert, province 
    FROM geo_desert 
    WHERE desert = %s;
    """
    cur.execute(find_geodesert, (desert_name, ))
    existing_geodesert = cur.fetchall()
    # print(existing_geodesert)
    if (len(existing_geodesert) != 0 and desert_province in [desert[1] for desert in existing_geodesert]):
        print(f"Geodesert '{existing_geodesert}' already exists for the specified name in the table 'geo_desert'.")
    else: 
        # Construct the INSERT query
        insert_geodesert = """
            INSERT INTO geo_desert (desert, country, province)
            VALUES (%s, %s, %s)
            ON CONFLICT (province, country, desert) DO NOTHING;
        """
        cur.execute(insert_geodesert, (desert_name, desert_country_code, desert_province))
        print(f"\nDesert '{desert_name}' created successfully in table 'geo_desert'\n")

    find_desert = """
    SELECT name 
    FROM desert 
    WHERE name = %s;
    """
    cur.execute(find_desert, (desert_name, ))
    existing_desert = cur.fetchone()
    if existing_desert:
        print(f"Desert '{existing_desert}' already exists at the specified name in the table 'desert'.")
        return
    if existing_desert is None:
        insert_desert = f"""
        INSERT INTO desert (name, area, coordinates)
        VALUES (%s, %s, ROW(%s, %s)::geocoord);
        """
        cur.execute(insert_desert, (desert_name, desert_area, desert_latitude, desert_longitude))
        conn.commit()
        print(f"Desert '{desert_name}' created successfully in table 'desert'.\n")

    # delete queries: 
    # DELETE FROM desert WHERE name='name'
    # DELETE FROM geo_desert WHERE desert='name'


def convert_countryname_to_code(countryName):
    query = f"SELECT code FROM country WHERE name = %s"
    cur.execute(query, (countryName, ))
    country_code = cur.fetchall()
    return country_code

def check_desert_constraints(desert_name, desert_country, desert_province, desert_area):
    # Check 1: A desert can only span a maximum of 9 provinces
    # print("Start check1...")
    query_count_provinces = f"""
        SELECT COUNT(*)
        FROM geo_desert
        WHERE desert = %s;
    """
    # print("query_count_provinces: " + query_count_provinces)
    cur.execute(query_count_provinces, (desert_name, ))
    provinces_count = cur.fetchall()
    # print(provinces_count[0][0])
    if int(provinces_count[0][0]) > 9:
        raise ValueError(f"\nDesert '{desert_name}' cannot span more than 9 provinces.")
    # print("No error raised check1\n")

    # Check 2: A country can only contain a maximum of 20 separate deserts
    # print("Start check2...")
    query_count_country_deserts = f"""
        SELECT COUNT(DISTINCT desert)
        FROM geo_desert
        WHERE country = %s;
    """
    country_code = convert_countryname_to_code(desert_country)[0][0]    # [0][0] -> first element of first tuple         
    # print("query_count_country_desert: " + query_count_country_deserts)
    cur.execute(query_count_country_deserts, (country_code, ))
    deserts_count = cur.fetchone()[0]
    # print("deserts_count: " + str(deserts_count))
    if deserts_count >= 20:
        raise ValueError(f"\nCountry '{desert_country}' cannot have more than 20 deserts.")
    # print("No error raised check2\n")

    # Check 3: The area of a desert can be at most 30 times larger 
    # than the area of any province it occupies
    # print("Start check3...")
    query_province_area = f"""
        SELECT area
        FROM province
        WHERE name = '{desert_province}'
    """
    # print("query_province_area: " + query_province_area)
    cur.execute(query_province_area)
    province_area = cur.fetchone()
    # print("province_area: " + str(province_area))
    if province_area is None:
        raise ValueError(f"\nProvince '{desert_province}' not found.")
    province_area = province_area[0]
    # print("province_area 2: " + str(province_area))
    
    if int(desert_area) > 30 * int(province_area):
        raise ValueError(
            f"\nDesert '{desert_name}' cannot have an area more than 30 times larger than province '{desert_province}'."
        )
    # print("Province area x30: " + str(int(province_area)*30))
    # print("Desert area: " + str(desert_area))

if __name__ == "__main__": 
    while True: 
        print("\nMenu:")
        print("1. Search for airports")
        print("2. Find amount of speakers of a language")
        print("3. Create desert")
        print("4. Exit")
        print("-----------------------------------------------------------------")

        choice = input("Pick a number: ")

        if choice == '1':
            print("\n")
            search_airports()
            print("\n-----------------------------------------------------------------")
        if choice == '2':
            find_speakers_of_language()
            print("\n-----------------------------------------------------------------")
        if choice == '3':
            create_desert()
            print("\n-----------------------------------------------------------------")
        if choice == '4':
            print("\n")
            exit()
    # Close the connection to the database.
    # conn.close()