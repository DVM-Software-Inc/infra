"""Execute inside the dev API container. Read-only counts, no emails or credentials."""
import asyncio
import json
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import Settings


async def main():
    engine = create_async_engine(Settings().database_url, echo=False)
    try:
        async with engine.connect() as conn:
            await conn.execute(text('SET TRANSACTION READ ONLY'))
            row = (await conn.execute(text('SELECT count(*) AS users, '
                'count(oidc_subject) AS bound_identities FROM users'))).mappings().one()
            orgs = (await conn.execute(text('SELECT count(*) FROM organizations'))).scalar_one()
            scoped = (await conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'users' AND column_name = 'oidc_issuer')"
            ))).scalar_one()
            result = {**dict(row), 'organizations': orgs,
                'keycloak_issuer_configured': Settings().oidc_issuer_url ==
                    'https://auth.chatactorai.com/realms/chatactorai-dev',
                'api_audience_configured': Settings().oidc_audience == 'chatactorai-dev-api',
                'issuer_scoped_schema': scoped}
            if scoped:
                result['legacy_bindings'] = (await conn.execute(text(
                    'SELECT count(*) FROM users WHERE oidc_issuer = :issuer'
                ), {'issuer': 'https://auth.chatactorai.com/application/o/chatactorai-dev/'})).scalar_one()
                result['keycloak_bindings'] = (await conn.execute(text(
                    'SELECT count(*) FROM users WHERE oidc_issuer = :issuer'
                ), {'issuer': 'https://auth.chatactorai.com/realms/chatactorai-dev'})).scalar_one()
            print(json.dumps(result))
    finally:
        await engine.dispose()


try:
    asyncio.run(main())
except Exception:
    raise SystemExit('Read-only inventory failed; raw diagnostics withheld') from None
