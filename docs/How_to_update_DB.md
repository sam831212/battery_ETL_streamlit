How to Add a New Column with Alembic (and Avoid Common Mistakes)
Correct Steps
Update Your Model

Add the new field to your SQLModel/SQLAlchemy model (e.g., add pre_test_rest_time to the Step model).
Generate a Migration

Run:
This creates a migration file in migrations/versions/ with the correct revision and down_revision headers.
Review the Migration

Check the generated migration file to ensure it adds the correct column.
Apply the Migration

Run:
This updates your database schema.
Why You Had Many Errors
Missing Revision Headers:
Alembic migration files must have revision and down_revision variables. If you create a migration file manually and forget these, Alembic cannot track or apply the migration.

Multiple Migration Files for the Same Change:
If you create several migration files for the same schema change (especially with different or missing headers), Alembic gets confused and may report "multiple heads" or "could not determine revision id" errors.

Multiple Heads Error:
If you have two or more migration files that do not share a common parent (i.e., they branch), Alembic will refuse to upgrade until you merge them using:

Not Deleting Bad Migration Files:
If you leave old, broken, or duplicate migration files in migrations/versions/, Alembic will keep trying to process them and fail.

How to Avoid These Mistakes
Always use alembic revision --autogenerate to create migration files.
Never manually create migration files unless you know exactly how to set revision and down_revision.
Delete any migration files that are missing headers or are not needed.
If you see a "multiple heads" error, use alembic heads to list them and alembic merge to resolve.
After fixing migrations, always run alembic upgrade head to ensure your DB is up to date.
Let me know if you want this as a file in your Document folder!- Not Deleting Bad Migration Files:
If you leave old, broken, or duplicate migration files in migrations/versions/, Alembic will keep trying to process them and fail.

How to Avoid These Mistakes
Always use alembic revision --autogenerate to create migration files.
Never manually create migration files unless you know exactly how to set revision and down_revision.
Delete any migration files that are missing headers or are not needed.
If you see a "multiple heads" error, use alembic heads to list them and alembic merge to resolve.
After fixing migrations, always run alembic upgrade head to ensure your DB is up to date.