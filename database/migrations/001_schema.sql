-- The Kit Room: relational schema (MySQL 8, InnoDB, 3NF)
-- SQL owns everything that must stay strictly consistent: accounts, catalogue,
-- stock, orders. Volatile and flexible data lives in MongoDB.

CREATE TABLE users (
  user_id       INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  email         VARCHAR(190) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  full_name     VARCHAR(120) NOT NULL,
  role          ENUM('customer','admin') NOT NULL DEFAULT 'customer',
  avatar_path   VARCHAR(255) NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE categories (
  category_id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  name        VARCHAR(80)  NOT NULL UNIQUE,
  description VARCHAR(255) NULL
) ENGINE=InnoDB;

CREATE TABLE products (
  product_id     INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  category_id    INT UNSIGNED NOT NULL,
  title          VARCHAR(160) NOT NULL,
  club           VARCHAR(100) NOT NULL,
  season         VARCHAR(9)   NOT NULL,
  description    TEXT NULL,
  price          DECIMAL(10,2) NOT NULL,
  stock_quantity INT NOT NULL DEFAULT 0,
  status         ENUM('active','archived') NOT NULL DEFAULT 'active',
  image_path     VARCHAR(255) NULL,
  created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_products_category FOREIGN KEY (category_id)
    REFERENCES categories(category_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  -- Last line of defence: stock can never go negative, even if application code is wrong.
  CONSTRAINT ck_products_stock CHECK (stock_quantity >= 0),
  CONSTRAINT ck_products_price CHECK (price > 0),
  INDEX idx_products_status_category (status, category_id),
  INDEX idx_products_club (club)
) ENGINE=InnoDB;

CREATE TABLE orders (
  order_id         INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  user_id          INT UNSIGNED NOT NULL,
  total_amount     DECIMAL(10,2) NOT NULL,
  order_status     ENUM('pending','shipped','delivered','cancelled') NOT NULL DEFAULT 'pending',
  shipping_address VARCHAR(255) NOT NULL,
  created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_orders_user FOREIGN KEY (user_id)
    REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT ck_orders_total CHECK (total_amount >= 0),
  INDEX idx_orders_user_created (user_id, created_at)
) ENGINE=InnoDB;

CREATE TABLE order_items (
  item_id    INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  order_id   INT UNSIGNED NOT NULL,
  product_id INT UNSIGNED NOT NULL,
  unit_price DECIMAL(10,2) NOT NULL,   -- price at purchase time, not the current price
  quantity   INT NOT NULL,
  CONSTRAINT fk_items_order FOREIGN KEY (order_id)
    REFERENCES orders(order_id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_items_product FOREIGN KEY (product_id)
    REFERENCES products(product_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT uq_items_order_product UNIQUE (order_id, product_id),
  CONSTRAINT ck_items_quantity CHECK (quantity > 0),
  CONSTRAINT ck_items_price CHECK (unit_price >= 0)
) ENGINE=InnoDB;

-- Transactional outbox: written in the SAME SQL transaction as the order, so a
-- committed order can never lose its MongoDB follow-up (cart, log, notification).
CREATE TABLE sync_outbox (
  outbox_id    INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  order_id     INT UNSIGNED NOT NULL,
  event_type   ENUM('order_placed','order_cancelled','order_status_changed') NOT NULL,
  payload      JSON NOT NULL,
  status       ENUM('pending','done') NOT NULL DEFAULT 'pending',
  attempts     INT NOT NULL DEFAULT 0,
  last_error   VARCHAR(500) NULL,
  created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  processed_at TIMESTAMP NULL,
  CONSTRAINT fk_outbox_order FOREIGN KEY (order_id)
    REFERENCES orders(order_id) ON UPDATE CASCADE ON DELETE CASCADE,
  INDEX idx_outbox_status (status)
) ENGINE=InnoDB;
