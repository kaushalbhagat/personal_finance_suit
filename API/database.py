import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession
from collections.abc import AsyncGenerator

# DATABASE_URL = "mysql+aiomysql://root:MyRoot123!@127.0.0.1:3306/budget_db"

# 🔌 Load the environment variables from your .env file
load_dotenv()

# 📥 Fetch credentials with clean fallback defaults
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "budget_db")

# 🛡️ Safety Check: URL-encode the password in case it contains characters like '@', ':', or '!'
safe_password = quote_plus(DB_PASSWORD)

# 🏗️ Dynamically construct the connection string
DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{safe_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_async_engine(DATABASE_URL)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine) as session:
        yield session


MONTHLY_INCOME_VIEW_SQL = """
CREATE OR REPLACE VIEW v_monthly_income_summary AS
SELECT 
    DATE_SUB(date, INTERVAL DAYOFMONTH(date) - 1 DAY) AS month,
    ROUND(SUM(amount * -1), 2) AS total
FROM transactions
WHERE category_id = 16
GROUP BY month;
"""

MONTHLY_EXPENSES_VIEW_SQL = """
CREATE OR REPLACE VIEW v_monthly_expenses_summary AS
SELECT 
    DATE_SUB(t.date, INTERVAL DAYOFMONTH(t.date) - 1 DAY) AS month,
    ROUND(SUM(t.amount), 2) AS total
FROM transactions t, categories c
WHERE t.category_id = c.id and c.exclude_from_reporting = 0
GROUP BY month;
"""

MONTHLY_BUSINESS_INCOME_VIEW_SQL = """
CREATE OR REPLACE VIEW v_monthly_business_income_summary AS
SELECT 
    DATE_SUB(date, INTERVAL DAYOFMONTH(date) - 1 DAY) AS month,
    ROUND(SUM(amount * -1), 2) AS total
FROM transactions
WHERE category_id = 16 and type="Business"
GROUP BY month;
"""

MONTHLY_BUSINESS_EXPENSES_VIEW_SQL = """
CREATE OR REPLACE VIEW v_monthly_business_expenses_summary AS
SELECT 
    DATE_SUB(t.date, INTERVAL DAYOFMONTH(t.date) - 1 DAY) AS month,
    ROUND(SUM(t.amount), 2) AS total
FROM transactions t, categories c
WHERE t.category_id=c.id and c.exclude_from_reporting=0 and t.type="Business"
GROUP BY month;
"""

MONTHLY_PERSONAL_INCOME_VIEW_SQL = """
CREATE OR REPLACE VIEW v_monthly_personal_income_summary AS
SELECT 
    DATE_SUB(date, INTERVAL DAYOFMONTH(date) - 1 DAY) AS month,
    ROUND(SUM(amount * -1), 2) AS total
FROM transactions
WHERE category_id = 16 and type="Personal"
GROUP BY month;
"""

MONTHLY_PERSONAL_EXPENSES_VIEW_SQL = """
CREATE OR REPLACE VIEW v_monthly_personal_expenses_summary AS
SELECT 
    DATE_SUB(t.date, INTERVAL DAYOFMONTH(t.date) - 1 DAY) AS month,
    ROUND(SUM(t.amount), 2) AS total
FROM transactions t, categories c
WHERE t.category_id=c.id and c.exclude_from_reporting=0 and t.type="Personal"
GROUP BY month;
"""

async def init_db(engine: AsyncEngine):
    async with engine.begin() as conn:
        # 1. 🔍 Filter out ANY model whose table name starts with 'v_'
        physical_tables = [
            table for name, table in SQLModel.metadata.tables.items()
            if not name.startswith("v_")
        ]
        
        # 2. 🛡️ Instruct SQLModel to ONLY build the physical subset
        # This completely stops the generator from making ghost tables!
        await conn.run_sync(
            lambda sync_conn: SQLModel.metadata.create_all(sync_conn, tables=physical_tables)
        )
        
        # 3. 📊 Create or update your real database views seamlessly
        await conn.execute(text(MONTHLY_EXPENSES_VIEW_SQL))
        await conn.execute(text(MONTHLY_INCOME_VIEW_SQL))     
        await conn.execute(text(MONTHLY_BUSINESS_EXPENSES_VIEW_SQL))
        await conn.execute(text(MONTHLY_BUSINESS_INCOME_VIEW_SQL))       
        await conn.execute(text(MONTHLY_PERSONAL_EXPENSES_VIEW_SQL))
        await conn.execute(text(MONTHLY_PERSONAL_INCOME_VIEW_SQL))                  
        print("🚀 Base tables generated & Virtual Views applied without ghost conflicts!")    

