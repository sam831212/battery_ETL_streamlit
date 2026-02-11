import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.config import DATABASE_URL, DB_PATH
from app.utils.database import init_db, get_session
from app.models import Cell, CellChemistry, CellFormFactor
from sqlalchemy import text  

def verify_setup():
    print(f"Checking configuration...")
    print(f"DATABASE_URL: {DATABASE_URL}")
    print(f"DB_PATH: {DB_PATH}")
    
    if "duckdb" not in DATABASE_URL:
        print("❌ Error: DATABASE_URL is not set to DuckDB")
        return False
        
    print("\nInitializing Database...")
    try:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
            print(f"Removed existing {DB_PATH} for clean test")
            
        success = init_db()
        if not success:
            print("❌ Database initialization failed")
            return False
        print("✅ Database initialized successfully")
        
        if not os.path.exists(DB_PATH):
             print(f"❌ Error: {DB_PATH} was not created")
             return False
        print(f"✅ {DB_PATH} created")

    except Exception as e:
        print(f"❌ Error during init: {e}")
        return False

    print("\nTesting Write Operation...")
    try:
        cell = Cell(
            name="Test Cell",
            manufacturer="Test Manufacturer",
            chemistry=CellChemistry.NMC,
            form_factor=CellFormFactor.CYLINDRICAL
        )
        
        with get_session() as session:
            session.add(cell)
            session.commit()
            print("✅ Write successful")
            
            # Test Read
            print("\nTesting Read Operation...")
            fetched_cell = session.query(Cell).first()
            if fetched_cell and fetched_cell.name == "Test Cell":
                 print(f"✅ Read successful: {fetched_cell.name}")
            else:
                 print("❌ Read failed")
                 return False
                 
            # Verify no eager loading (hard to test programmatically without mocking, 
            # but we can check if accessing experiments doesn't crash)
            print("\nVerifying lazy loading...")
            experiments = fetched_cell.experiments
            print(f"✅ Accessed experiments relation (should be empty): {experiments}")

    except Exception as e:
        print(f"❌ Error during operations: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    return True

if __name__ == "__main__":
    if verify_setup():
        print("\n🎉 Verification PASSED!")
    else:
        print("\n💥 Verification FAILED!")
        sys.exit(1)
