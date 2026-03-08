import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.middleware.rate_limit import login_rate_limit

# StaticPool forces all connections (including the AuditMiddleware's own
# sessions) to reuse the same underlying SQLite connection, so committed
# audit-log rows are immediately visible to subsequent test queries.
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Let the AuditMiddleware write to the same in-memory DB.
    app.state.session_factory = TestSessionLocal

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncSession:
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    async def override_get_db():
        yield db_session

    async def override_rate_limit():
        # Disable rate limiting in tests to prevent cross-test interference.
        return None

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[login_rate_limit] = override_rate_limit
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
