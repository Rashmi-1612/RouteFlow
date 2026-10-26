
# RouteFlow — Smart Route Optimization System

RouteFlow is a route optimization application designed to help manage delivery locations and generate efficient delivery routes. It combines a React-based frontend with a FastAPI backend and uses mapping services to visualize locations and routes.

## Features

- **Dashboard:** View delivery locations, route plans, and network information.
- **Location Management:** Search, add, view, and delete delivery locations.
- **India-Wide Address Search:** Search for places and addresses across India.
- **Hub Management:** Select a distribution hub as the starting point for delivery routes.
- **Route Optimization:** Generate delivery routes using the algorithms supported by the backend.
- **Interactive Map:** Visualize delivery locations and route geometry on a map.
- **Vehicle Configuration:** Configure the number of vehicles and maximum stops per vehicle.
- **Route History:** Review previously generated route plans.
- **Responsive Interface:** Access the application through a modern web interface.

## Technology Stack

### Frontend
- React
- Vite
- JavaScript
- React Leaflet
- Leaflet
- Lucide React
- CSS

### Backend
- Python
- FastAPI
- Uvicorn

### Mapping and Routing
- OpenStreetMap — map tiles and geographic data
- Nominatim — address search and geocoding
- OSRM — road-network routing, where configured

### Data Storage
- Uses the storage system configured in the existing RouteFlow backend.

## Project Structure

```text
routeflow_react/
├── README.md
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── routeflow/
│   │   ├── __init__.py
│   │   ├── db.py
│   │   ├── geo.py
│   │   ├── live.py
│   │   └── planner.py
│   └── algorithms/
│       ├── __init__.py
│       ├── brute_force.py
│       ├── common.py
│       ├── greedy.py
│       ├── held_karp.py
│       ├── local_search.py
│       └── savings_vrp.py
└── frontend/
    ├── package.json
    ├── index.html
    └── src/
        ├── App.jsx
        ├── main.jsx
        └── styles.css
```

## Prerequisites

Install the following before running the application:

- Python 3.10 or a compatible version supported by the backend dependencies
- Node.js and npm
- Visual Studio Code or another code editor
- An internet connection for online map tiles and external geocoding/routing services

## Installation and Setup

### 1. Open the project

Open the `routeflow_react` folder in Visual Studio Code.

### 2. Set up the backend

Open a terminal in VS Code and run:

```bash
cd backend
python -m venv venv
```

Activate the virtual environment.

**Windows — Command Prompt:**

```bat
venv\Scripts\activate
```

**Windows — PowerShell:**

```powershell
.\venv\Scripts\Activate.ps1
```

Install the backend dependencies:

```bash
python -m pip install -r requirements.txt
```

Start the backend server:

```bash
uvicorn main:app --reload
```

The backend should be available at:

- API base: http://127.0.0.1:8000
- Interactive API documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health

Keep this terminal running.

### 3. Set up the frontend

Open a **second terminal** in VS Code. From the project root, run:

```bash
cd frontend
npm install
npm run dev
```

Vite will display a local development URL, usually:

http://localhost:5173

Open that URL in your browser.

## How to Use RouteFlow

### Step 1: Open the dashboard

The dashboard displays saved locations, delivery stops, route history, and a map of the delivery network.

### Step 2: Add locations

1. Open the **Locations** section.
2. Enter a place or address in the search bar.
3. Select Search.
4. Choose a result and click Add.
5. Repeat for the remaining delivery destinations.

For example, you can search for Hawa Mahal, Jaipur, or Connaught Place, Delhi.

### Step 3: Set the distribution hub

In the Locations section, select **Set hub** next to the location you want to use as the starting point.

### Step 4: Configure the route

1. Open **Route planner**.
2. Select an optimization algorithm.
3. Set the number of vehicles.
4. Configure the maximum stops per vehicle if needed.
5. Choose whether the route should return to the hub.

### Step 5: Generate the route

Click **Generate optimized route**. The application sends a request to the backend, which runs the configured route-planning logic.

The results section displays the route information returned by the backend.

### Step 6: Review route history

Open **Route history** to review previously saved planning runs.

## API Endpoints

The React frontend is configured to communicate with the FastAPI backend using the following endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Check backend health |
| GET | `/api/locations` | Retrieve saved locations |
| POST | `/api/locations` | Add a location |
| DELETE | `/api/locations/{id}` | Delete a location |
| POST | `/api/locations/{id}/make-hub` | Set the distribution hub |
| GET | `/api/geocode` | Search for an address |
| GET | `/api/algorithms` | Retrieve supported algorithms |
| POST | `/api/plan` | Generate an optimized route |
| GET | `/api/history` | Retrieve route history |

The actual request and response formats depend on the implementation in `backend/main.py`.

## Troubleshooting

### Backend connection error

If the frontend displays a connection error:

1. Check that the backend terminal is running.
2. Open `http://127.0.0.1:8000/docs`.
3. Check the backend terminal for Python errors.
4. Confirm that the frontend API base URL in `App.jsx` matches the backend address.

### Frontend dependency error

Run the following commands from the `frontend` folder:

```bash
npm install
npm run dev
```

### Address search returns no results

- Check your internet connection.
- Try a more specific address or a nearby landmark.
- Check the backend terminal for geocoding errors.
- Remember that public geocoding services may impose usage limits.

### Map does not appear

- Check your internet connection.
- Confirm that the browser can load OpenStreetMap tiles.
- Check the browser console for errors.

### Route planning fails

- Make sure a hub is configured.
- Add at least one delivery stop.
- Confirm that the required backend algorithms and routing services are available.
- Review the error message in the backend terminal.

## Important Notes

- The frontend requires the FastAPI backend to be running.
- Route-planning functionality depends on the backend algorithms and their integration with the geographic routing module.
- Public OpenStreetMap, Nominatim, and OSRM services may have usage policies, rate limits, and availability restrictions.
- The README describes the intended application workflow. Verify each endpoint and feature against the current backend implementation before treating it as fully tested.

## Future Enhancements

- Live vehicle tracking
- Delivery status management
- Driver and vehicle assignment
- Route comparison and performance analytics
- Estimated delivery times
- Improved mobile responsiveness
- Authentication and role-based access
- Deployment to a cloud server

## License

This project is intended for educational and development purposes. Add an appropriate open-source or institutional license before distributing it publicly.
