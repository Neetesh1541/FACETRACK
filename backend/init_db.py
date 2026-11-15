from database import engine
from models.models import Base

# Create all FACETRACK database tables
Base.metadata.create_all(bind=engine)

print("===================================")
print("FACETRACK DATABASE INITIALIZED!")
print("All tables created successfully.")
print("===================================")

for table in Base.metadata.sorted_tables:
    print("Created table:", table.name)