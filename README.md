# df-backpack

## API Endpoints

- `GET /api/users` - Get all users
- `POST /api/users` - Create a new user
- `POST /api/messages` - Send a message
- `GET /health` - Health check endpoint
- `WS /ws` - WebSocket endpoint for real-time communication

### API Authentication

- **Bearer Token**: Include a valid JWT token in the `Authorization` header for protected endpoints.


## WebSocket Connection

To connect to the WebSocket endpoint, use the following URL:
ws://localhost:8080/ws

### WebSocket Message Format

- **Client to Server**: JSON object with `type` and `data` fields
  - `type`: Message type (e.g., `register`, `message`)
  - `data`: Message payload (e.g., user ID, message content)

- **Server to Client**: JSON object with `type` and `data` fields
  - `type`: Message type (e.g., `register`, `message`)
  - `data`: Message payload (e.g., user ID, message content)