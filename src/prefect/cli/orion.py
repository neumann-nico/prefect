"""
Command line interface for working with Orion
"""
import typer
import uvicorn

from prefect import settings
from prefect.cli.base import app, console, exit_with_error, exit_with_success

from prefect.utilities.asyncio import sync_compatible, sync
from prefect.orion.database.dependencies import provide_database_interface


orion_app = typer.Typer(name="orion")
app.add_typer(orion_app)


@orion_app.command()
def start(
    host: str = settings.orion.api.host,
    port: int = settings.orion.api.port,
    log_level: str = settings.logging.default_level,
    services: bool = True,
):
    """Start an Orion server"""
    # Delay this import so we don't instantiate the API uncessarily
    from prefect.orion.api.server import app as orion_fastapi_app

    # TODO - this logic should be abstracted in the interface
    # create the sqlite database if it doesnt already exist
    db = provide_database_interface()
    sync(db.engine)

    console.print("Starting Orion API...")
    # Toggle `run_in_app` (settings are frozen and so it requires a forced update)
    # See https://github.com/PrefectHQ/orion/issues/281
    object.__setattr__(settings.orion.services, "run_in_app", services)
    uvicorn.run(orion_fastapi_app, host=host, port=port, log_level=log_level.lower())
    console.print("Orion stopped!")


@orion_app.command()
@sync_compatible
async def reset_db(yes: bool = typer.Option(False, "--yes", "-y")):
    """Drop and recreate all Orion database tables"""
    db = provide_database_interface()
    engine = await db.engine()
    if not yes:
        confirm = typer.confirm(
            f'Are you sure you want to reset the Orion database located at "{engine.url}"? This will drop and recreate all tables.'
        )
        if not confirm:
            exit_with_error("Database reset aborted")
    console.print("Resetting Orion database...")
    console.print("Dropping tables...")
    await db.drop_db()
    console.print("Creating tables...")
    await db.create_db()
    exit_with_success(f'Orion database "{engine.url}" reset!')