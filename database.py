import aiosqlite

DB_PATH = "sneakers.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sneakers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand TEXT NOT NULL,
                model TEXT NOT NULL,
                size TEXT,
                price REAL NOT NULL,
                description TEXT,
                photo_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def add_sneaker(brand, model, size, price, description, photo_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO sneakers (brand, model, size, price, description, photo_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (brand, model, size, price, description, photo_id))
        await db.commit()
        return cursor.lastrowid


async def get_all_sneakers():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM sneakers ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_sneakers_by_brand(brand):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM sneakers WHERE LOWER(brand) = LOWER(?) ORDER BY created_at DESC",
            (brand,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def search_sneakers(query):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM sneakers
            WHERE LOWER(brand) LIKE ? OR LOWER(model) LIKE ?
            ORDER BY created_at DESC
        """, (f"%{query.lower()}%", f"%{query.lower()}%"))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_brands():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT DISTINCT brand FROM sneakers ORDER BY brand")
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


async def count_sneakers():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM sneakers")
        row = await cursor.fetchone()
        return row[0] if row else 0