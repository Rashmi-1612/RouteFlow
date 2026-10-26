
from db import get_connection


def load_locations_and_matrix():
    connection = get_connection()

    if connection is None:
        raise ConnectionError("Could not connect to MySQL.")

    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT location_id, location_name "
            "FROM locations ORDER BY location_id"
        )
        locations = cursor.fetchall()

        cursor.execute(
            "SELECT source_id, destination_id, distance_km "
            "FROM distances"
        )
        distance_rows = cursor.fetchall()

        if not locations:
            raise ValueError("No locations found in the database.")

        names = [name for _, name in locations]
        id_to_index = {
            location_id: index
            for index, (location_id, _) in enumerate(locations)
        }

        n = len(locations)
        matrix = [[0.0] * n for _ in range(n)]

        for source_id, destination_id, distance in distance_rows:
            if source_id in id_to_index and destination_id in id_to_index:
                i = id_to_index[source_id]
                j = id_to_index[destination_id]
                matrix[i][j] = float(distance)

        return names, matrix

    finally:
        connection.close()


if __name__ == "__main__":
    names, matrix = load_locations_and_matrix()

    print("Locations:", names)
    print("\nDistance matrix:")
    for row in matrix:
        print(row)
