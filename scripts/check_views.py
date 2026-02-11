from sqlalchemy import create_engine, inspect, text
from sqlmodel import Session
from app.utils.config import DATABASE_URL

# Create SQLite database engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

def get_session():
    return Session(engine)

def check_views():
    """Checks for the existence of views in the database."""
    with get_session() as session:
        inspector = inspect(session.bind)
        views = inspector.get_view_names()
        if views:
            print("Detected views in the database:")
            for view in views:
                print(f"- {view}")
                session.execute(text(f"DROP VIEW IF EXISTS {view}"))
                print(f"Dropped view: {view}")
            session.commit()
            print("All detected views have been dropped.")
            return True
        else:
            print("No views detected in the database.")
            return False

if __name__ == "__main__":
    check_views()