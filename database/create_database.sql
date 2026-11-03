-- Run once as the MySQL root user (MySQL Workbench or: mysql -u root -p < database/create_database.sql)
CREATE DATABASE IF NOT EXISTS kitroom CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS 'kitroom'@'localhost' IDENTIFIED BY 'kitroom_dev';
CREATE USER IF NOT EXISTS 'kitroom'@'127.0.0.1' IDENTIFIED BY 'kitroom_dev';
GRANT ALL PRIVILEGES ON kitroom.* TO 'kitroom'@'localhost';
GRANT ALL PRIVILEGES ON kitroom.* TO 'kitroom'@'127.0.0.1';
-- Separate database for the automated tests
CREATE DATABASE IF NOT EXISTS kitroom_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
GRANT ALL PRIVILEGES ON kitroom_test.* TO 'kitroom'@'localhost';
GRANT ALL PRIVILEGES ON kitroom_test.* TO 'kitroom'@'127.0.0.1';
