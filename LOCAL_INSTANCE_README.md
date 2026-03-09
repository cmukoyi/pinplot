# Beacon Telematics - Local Instance

This is a local copy of the GPS Tracker application with differentiated naming for development and testing purposes.

## Key Differences from Production (mobileGPS)

### Container Names
All Docker containers use the `beacon_telematics_*` prefix instead of `ble_tracker_*`:
- `beacon_telematics_db` (vs `ble_tracker_db`)
- `beacon_telematics_backend` (vs `ble_tracker_backend`)
- `beacon_telematics_admin` (vs `ble_tracker_admin`)
- `beacon_telematics_customer` (vs `ble_tracker_customer`)
- `beacon_telematics_flutter_web` (vs `ble_tracker_flutter_web`)
- `beacon_telematics_nginx` (vs `ble_tracker_nginx`)

### Database
- **Name**: `beacon_telematics` (vs `ble_tracker`)
- **User**: `beacon_user` (vs `ble_user`)
- **Password**: Set in `.env` file

### Network
- Network name: `beacon_telematics_network` (vs `ble_network`)
- Local network: `beacon_telematics_network_local` (vs `ble_network_local`)

### Volume
- Volume name: `beacon_telematics_postgres_data` (vs `postgres_data`)
- Local volume: `beacon_telematics_postgres_data_local` (vs `postgres_data_local`)

## Setup Instructions

1. **Configure Environment Variables**:
   ```bash
   cd gps-tracker
   cp .env.example .env
   # Edit .env with your credentials
   
   cd backend
   cp .env.example .env
   # Edit backend/.env with your credentials
   ```

2. **Run Locally**:
   ```bash
   cd gps-tracker
   docker-compose -f docker-compose.local.yml up
   ```

3. **Run Production-like Setup**:
   ```bash
   cd gps-tracker
   docker-compose up
   ```

## Port Mappings (Same as Original)
- Backend: `8000`
- Admin Dashboard: `3000`
- Customer Dashboard: `3001`
- Flutter Web: `3002`
- PostgreSQL: `5432`
- Nginx: `80` (HTTP), `443` (HTTPS)

## Notes
- This instance is completely independent from the production mobileGPS instance
- Container names won't conflict if both are running simultaneously
- Database and volumes are separate
- Modify ports in docker-compose.yml if you need to run both instances at the same time
