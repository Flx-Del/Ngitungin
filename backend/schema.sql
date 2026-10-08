-- Ngitungin MVP schema (PostgreSQL)
CREATE TABLE users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE businesses (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    business_name VARCHAR(160) NOT NULL,
    business_type VARCHAR(80),
    address TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_businesses_user_id ON businesses(user_id);

CREATE TABLE categories (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(24) NOT NULL CHECK (type IN ('product', 'expense', 'income', 'material')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (business_id, type, name)
);

CREATE TABLE units (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    name VARCHAR(40) NOT NULL,
    symbol VARCHAR(16) NOT NULL,
    dimension VARCHAR(24) NOT NULL CHECK (dimension IN ('mass', 'volume', 'count', 'time', 'other')),
    base_factor NUMERIC(18,6) NOT NULL DEFAULT 1 CHECK (base_factor > 0),
    UNIQUE (business_id, symbol)
);

CREATE TABLE products (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    category_id BIGINT REFERENCES categories(id) ON DELETE RESTRICT,
    name VARCHAR(160) NOT NULL,
    sku VARCHAR(80),
    unit_id BIGINT REFERENCES units(id) ON DELETE RESTRICT,
    unit_label VARCHAR(40) NOT NULL DEFAULT 'unit',
    selling_price NUMERIC(18,2) NOT NULL CHECK (selling_price >= 0),
    cost_price NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (cost_price >= 0),
    stock NUMERIC(18,3) NOT NULL DEFAULT 0 CHECK (stock >= 0),
    minimum_stock NUMERIC(18,3) NOT NULL DEFAULT 0 CHECK (minimum_stock >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (business_id, sku)
);
CREATE INDEX ix_products_business_active ON products(business_id, is_active);

CREATE TABLE materials (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    name VARCHAR(160) NOT NULL,
    unit_id BIGINT REFERENCES units(id) ON DELETE RESTRICT,
    unit_label VARCHAR(40) NOT NULL,
    purchase_price NUMERIC(18,2) NOT NULL CHECK (purchase_price >= 0),
    purchase_quantity NUMERIC(18,6) NOT NULL CHECK (purchase_quantity > 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE product_materials (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    material_id BIGINT NOT NULL REFERENCES materials(id) ON DELETE RESTRICT,
    quantity_used NUMERIC(18,6) NOT NULL CHECK (quantity_used > 0),
    unit_label VARCHAR(40) NOT NULL,
    batch_yield NUMERIC(18,3) NOT NULL DEFAULT 1 CHECK (batch_yield > 0),
    UNIQUE (product_id, material_id)
);

CREATE TABLE labor_costs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    description VARCHAR(160) NOT NULL,
    cost NUMERIC(18,2) NOT NULL CHECK (cost >= 0),
    scope VARCHAR(16) NOT NULL DEFAULT 'per_batch' CHECK (scope IN ('per_unit', 'per_batch', 'per_month')),
    production_quantity NUMERIC(18,3) NOT NULL DEFAULT 1 CHECK (production_quantity > 0),
    duration_minutes NUMERIC(12,2) CHECK (duration_minutes IS NULL OR duration_minutes >= 0)
);

CREATE TABLE overhead_costs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    description VARCHAR(160) NOT NULL,
    cost NUMERIC(18,2) NOT NULL CHECK (cost >= 0),
    scope VARCHAR(16) NOT NULL DEFAULT 'per_batch' CHECK (scope IN ('per_unit', 'per_batch', 'per_month')),
    production_quantity NUMERIC(18,3) NOT NULL DEFAULT 1 CHECK (production_quantity > 0)
);

CREATE TABLE transactions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    transaction_number VARCHAR(64) NOT NULL,
    type VARCHAR(24) NOT NULL CHECK (type IN ('sale', 'other_income')),
    status VARCHAR(16) NOT NULL DEFAULT 'posted' CHECK (status IN ('posted', 'void')),
    transaction_date DATE NOT NULL,
    subtotal NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (subtotal >= 0),
    discount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (discount >= 0),
    total NUMERIC(18,2) NOT NULL CHECK (total >= 0),
    payment_method VARCHAR(40) NOT NULL DEFAULT 'tunai',
    description VARCHAR(200),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (business_id, transaction_number)
);
CREATE INDEX ix_transactions_business_date ON transactions(business_id, transaction_date, status);

CREATE TABLE transaction_items (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id BIGINT NOT NULL REFERENCES transactions(id) ON DELETE RESTRICT,
    product_id BIGINT REFERENCES products(id) ON DELETE RESTRICT,
    product_name_snapshot VARCHAR(160) NOT NULL,
    sku_snapshot VARCHAR(80),
    quantity NUMERIC(18,3) NOT NULL CHECK (quantity > 0),
    price NUMERIC(18,2) NOT NULL CHECK (price >= 0),
    cost_per_unit NUMERIC(18,2) NOT NULL CHECK (cost_per_unit >= 0),
    discount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (discount >= 0),
    subtotal NUMERIC(18,2) NOT NULL CHECK (subtotal >= 0)
);
CREATE INDEX ix_transaction_items_product ON transaction_items(product_id);

CREATE TABLE expenses (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    category_id BIGINT REFERENCES categories(id) ON DELETE RESTRICT,
    expense_date DATE NOT NULL,
    amount NUMERIC(18,2) NOT NULL CHECK (amount >= 0),
    description VARCHAR(200) NOT NULL,
    payment_method VARCHAR(40) NOT NULL DEFAULT 'tunai',
    notes TEXT,
    status VARCHAR(16) NOT NULL DEFAULT 'posted' CHECK (status IN ('posted', 'void')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_expenses_business_date ON expenses(business_id, expense_date, status);

CREATE TABLE stock_movements (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    transaction_id BIGINT REFERENCES transactions(id) ON DELETE RESTRICT,
    movement_type VARCHAR(20) NOT NULL CHECK (movement_type IN ('opening', 'sale', 'adjustment', 'return', 'reversal')),
    quantity_change NUMERIC(18,3) NOT NULL CHECK (quantity_change <> 0),
    note VARCHAR(200),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_stock_movements_product_date ON stock_movements(product_id, created_at);
