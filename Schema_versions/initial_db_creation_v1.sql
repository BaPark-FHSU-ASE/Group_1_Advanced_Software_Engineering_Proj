CREATE DATABASE inventory_management

USE inventory_management

CREATE TABLE owners (
  owner_id int AUTO_INCREMENT PRIMARY KEY,
  first_name varchar(100) NOT NULL,
  last_name varchar(100) NOT NULL,
  date_added DATETIME DEFAULT CURRENT_TIMESTAMP
)

INSERT INTO owners (first_name, last_name)
VALUES ('Bens_Test_FirstNm2', 'Bens_Test_LastNm2')

CREATE TABLE BUSINESS (
  business_id int AUTO_INCREMENT PRIMARY KEY,
  name varchar(100) NOT NULL,
  owner_name varchar(200) NOT NULL,
  owner_id int, 
  FOREIGN KEY (owner_id)
  REFERENCES owners(owner_id)

)

DELIMITER //

CREATE TRIGGER before_business_insert
BEFORE INSERT ON BUSINESS
FOR EACH ROW
BEGIN
  DECLARE fname VARCHAR(100);
  DECLARE lname VARCHAR(100);

  SELECT first_name, last_name
    INTO fname, lname
    FROM owners
    WHERE owner_id = NEW.owner_id;

  SET NEW.owner_name = CONCAT(fname, ' ', lname);
END//

DELIMITER ;

INSERT INTO BUSINESS (name, owner_id)
VALUES ('Bens_Test_Business2', 1);

SELECT * FROM BUSINESS;

DELETE FROM BUSINESS 
WHERE business_id = 3
and owner_id = 1

CREATE TABLE BUILDING (
  building_id int AUTO_INCREMENT PRIMARY KEY NOT NULL,
  business_id INT NOT NULL,
  business_name VARCHAR(100) NOT NULL,
  owner_id INT NOT NULL,
  state VARCHAR(100),
  city VARCHAR(100),
  street_address VARCHAR(100),
  owner_name VARCHAR(100),
  FOREIGN KEY (business_id) REFERENCES BUSINESS(business_id),
  FOREIGN KEY (owner_id) REFERENCES business(owner_id)
);

INSERT INTO BUILDING (business_id, business_name , owner_id, state, city, street_address, owner_name)
VALUES (2, 'Bens_Test_Business2', 1 ,'Kansas', 'Salina', '458 test street',  'Bens_Test_FirstNm Bens_Test_LastNm');

CREATE TABLE ROOM (
	room_id INT AUTO_INCREMENT PRIMARY KEY NOT NULL,
    building_id INT NOT NULL,
    LOCATION VARCHAR(100),
    FOREIGN KEY (building_id) REFERENCES BUILDING(building_id)
)

INSERT INTO ROOM (building_id, location)
VALUES (1, 'South storage closet')

SELECT * 
FROM 

CREATE TABLE STORAGE (
	storage_id INT AUTO_INCREMENT PRIMARY KEY NOT NULL,
    room_id INT NOT NULL,
    item_cnt INT NOT NULL,
    storage_type VARCHAR(100),
    FOREIGN KEY (room_id) REFERENCES ROOM(room_id)
)

INSERT INTO STORAGE (room_id, item_cnt, storage_type)
VALUES (1, 0, 'Locker')

SELECT *
FROM STORAGE



CREATE TABLE ITEM (
	item_id INT AUTO_INCREMENT PRIMARY KEY NOT NULL,
    storage_id INT NOT NULL,
    item_name VARCHAR(100),
    item_type VARCHAR (100),
    item_status VARCHAR (100),
    date_added DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (storage_id) 	REFERENCES STORAGE(storage_id)
)

DELIMITER //

CREATE TRIGGER after_item_insert
AFTER INSERT ON ITEM
FOR EACH ROW
BEGIN
  UPDATE STORAGE
  SET item_cnt = item_cnt + 1
  WHERE storage_id = NEW.storage_id;
END//

DELIMITER ;

DELIMITER //

CREATE TRIGGER after_item_delete
AFTER DELETE ON ITEM
FOR EACH ROW
BEGIN
  UPDATE STORAGE
  SET item_cnt = item_cnt - 1
  WHERE storage_id = OLD.storage_id;
END//

DELIMITER ;


DELIMITER //

CREATE TRIGGER after_item_update
AFTER UPDATE ON ITEM
FOR EACH ROW
BEGIN
  IF OLD.storage_id <> NEW.storage_id THEN
    UPDATE STORAGE SET item_cnt = item_cnt - 1 WHERE storage_id = OLD.storage_id;
    UPDATE STORAGE SET item_cnt = item_cnt + 1 WHERE storage_id = NEW.storage_id;
  END IF;
END//

DELIMITER ;


INSERT INTO ITEM (storage_id, item_name, item_type, item_status)
VALUES (1, 'Hammer', 'Tool', 'In storage')

Select *
FROM ITEM


