-- VersCafe DB schema
-- Note: We intentionally avoid DROP TABLE to keep existing data safe.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS user
(
    ID        INTEGER PRIMARY KEY AUTOINCREMENT,
    FirstName VARCHAR NOT NULL,
    LastName  VARCHAR NOT NULL,
    Phone     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS menu
(
    ID         INTEGER PRIMARY KEY AUTOINCREMENT,
    Name       VARCHAR NOT NULL,
    Price      INTEGER
);

CREATE TABLE IF NOT EXISTS checkout
(
    ID         INTEGER PRIMARY KEY AUTOINCREMENT,
    UserID     INT NOT NULL,
    quantity   INT NOT NULL DEFAULT 1,
    ItemID     INT NOT NULL,
    ItemPrice  INT NOT NULL,
    TotalPrice INT NOT NULL,
    FOREIGN KEY (UserID) REFERENCES user (ID),
    FOREIGN KEY (ItemID) REFERENCES menu (ID)
);
