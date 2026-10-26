
CREATE DATABASE IF NOT EXISTS courier_optimizer;

USE courier_optimizer;

CREATE TABLE IF NOT EXISTS locations (
    location_id INT AUTO_INCREMENT PRIMARY KEY,
    location_name VARCHAR(100) NOT NULL,
    location_type ENUM('Hub', 'Delivery') NOT NULL
);

CREATE TABLE IF NOT EXISTS distances (
    source_id INT NOT NULL,
    destination_id INT NOT NULL,
    distance_km DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (source_id, destination_id),
    FOREIGN KEY (source_id) REFERENCES locations(location_id),
    FOREIGN KEY (destination_id) REFERENCES locations(location_id),
    CHECK (distance_km >= 0)
);

CREATE TABLE IF NOT EXISTS optimization_runs (
    run_id INT AUTO_INCREMENT PRIMARY KEY,
    algorithm_name VARCHAR(50) NOT NULL,
    total_distance_km DECIMAL(10, 2) NOT NULL,
    route_sequence TEXT NOT NULL,
    execution_time_ms DECIMAL(12, 4) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
