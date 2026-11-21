
# Fresh First – Perishable Stock Verification Register

## Project Overview
A web-based system for managing perishable stock, verifying expiry dates and storage temperatures, assigning priorities, and maintaining activity history.

## Team Members
- Database: Rutika
- Frontend: Basamma
- Backend: Shrushti
- Testing: Khushi

## Technology Stack
- Frontend: HTML, CSS, JavaScript
- Backend: Python, Flask
- Database: MySQL / MariaDB

## Project Structure
- `backend/` – Backend application and database connection
- `database/` – Database scripts and migrations
- `frontend/` – User interface files
- `diagrams/` – Project workflow diagrams
- `documentation/` – Project and testing documents

## Database
- Database name: `freshfirst_team`
- Database: MySQL / MariaDB

## Database Tables
1. users
2. categories
3. products
4. verifications
5. actions
6. history
7. app_settings

## Backend
The backend is developed using Flask and provides APIs for login, products, categories, verification, priority, actions, history, users, reports and settings.

## Testing
Backend API testing includes:
- API endpoint testing
- Product and category operations
- Verification and action operations
- Role-based access testing
- Reports and settings testing

## Important Files
- `database/freshfirst_team.sql`
- `documentation/DATABASE_DOCUMENTATION.md`
- `documentation/DATABASE_TESTING_REPORT.md`

## Security Note
Configure the `FRESHFIRST_SECRET_KEY` environment variable before running the backend. Database connection settings can be configured using environment variables.

## Team Workflow
Database → Frontend → Backend → Testing
