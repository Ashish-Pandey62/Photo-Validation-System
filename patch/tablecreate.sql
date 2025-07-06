CREATE TABLE api_config (
id INT(6) UNSIGNED AUTO_INCREMENT PRIMARY KEY,
min_height FLOAT,
max_height FLOAT,
min_width FLOAT,
max_width FLOAT,
min_size FLOAT,
max_size FLOAT,
is_jpg   BOOLEAN,
is_png   BOOLEAN,
allowed_formats varchar(2555)
)