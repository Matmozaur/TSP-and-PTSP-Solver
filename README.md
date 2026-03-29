# TSP and PTSP Solver

A high-performance FastAPI application for solving Traveling Salesman Problem (TSP) and Physical Traveling Salesman Problem (PTSP) using multiple algorithms.

## Features

- **Multiple Solving Algorithms**:
  - Random: Quick random solution generation
  - Hill Climbing (HC): Local search optimization
  - Genetic Algorithm: Population-based evolutionary approach
  - Monte Carlo Tree Search (MCTS): Tree-based search with sampling

- **Modern Stack**:
  - FastAPI for high-performance REST API
  - Pydantic v2 for data validation
  - Async/await support
  - Comprehensive OpenAPI documentation

- **Graph Visualization**: Generate and visualize graph instances

- **Containerized**: Docker support for easy deployment

## Installation

### Local Development

```bash
# Clone repository
git clone <repo-url>
cd tsp-ptsp-solver

# Install dependencies with UV
uv install

# Or with pip
pip install -e ".[dev]"
```

### Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build standalone
docker build -t tsp-solver .
docker run -p 8000:8000 tsp-solver
```

## Running the Application

### Local

```bash
# Using UV
uv run python run.py

# Or directly
python run.py

# Or with uvicorn
uvicorn src.app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Docker

```bash
docker-compose up
```

## API Documentation

Once running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## API Endpoints

### TSP Solving

**POST** `/api/v1/tsp/solve` - Solve TSP instance

Request body:
```json
{
  "graph": {
    "matrix": [[0, 10, 15], [10, 0, 35], [15, 35, 0]],
    "names": ["A", "B", "C"]
  },
  "method": "HC",
  "time_limit": 60.0,
  "population": 50,
  "mutate": true,
  "simulation_type": "nearest"
}
```

**POST** `/api/v1/tsp/upload` - Upload JSON file with TSP instance and solve

**POST** `/api/v1/tsp/visualize` - Generate graph visualization

**GET** `/api/v1/tsp/health` - Health check

### PTSP

**GET** `/api/v1/ptsp/health` - Health check

**GET** `/api/v1/ptsp/methods` - Get available solving methods

## Project Structure

```
tsp-ptsp-solver/
├── src/
│   └── app/
│       ├── main.py              # FastAPI app entry point
│       ├── config.py            # Settings configuration
│       ├── schemas.py           # Pydantic models
│       ├── services.py          # Business logic
│       ├── routes_tsp.py        # TSP endpoints
│       └── routes_ptsp.py       # PTSP endpoints
├── analytics/                   # Algorithm implementations
│   ├── tsp/
│   │   ├── domain/             # Core TSP solvers
│   │   ├── genetic/            # GA implementation
│   │   └── mcts/               # MCTS implementation
│   └── ptsp/
│       ├── domain/
│       ├── genetic/
│       └── mcts/
├── tests/                      # Unit tests
├── Dockerfile                  # Container configuration
├── docker-compose.yml          # Compose configuration
├── pyproject.toml             # Project configuration
└── README.md                  # This file
```

## Configuration

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
DEBUG=false
ENVIRONMENT=production
CORS_ORIGINS=["http://localhost", "http://localhost:3000"]
```

## Development

### Run Tests

```bash
# With pytest
pytest

# With coverage
pytest --cov=src

# Watch mode
pytest-watch
```

### Code Quality

```bash
# Format code
black src/

# Lint code
ruff check src/

# Type checking
mypy src/
```

### Type Checking

All code is fully typed. Run mypy:

```bash
mypy src/ --strict
```

## Performance

- **Random**: O(n) - Instant results
- **Hill Climbing**: Scales with time allocation
- **Genetic Algorithm**: O(p*g) where p=population, g=generations
- **MCTS**: O(t) where t=time budget

All algorithms scale efficiently to handle graphs with 100+ nodes.

## Dependencies

### Core
- fastapi >= 0.104.0
- uvicorn >= 0.24.0
- pydantic >= 2.0.0
- networkx >= 3.0
- numpy >= 1.24.0
- matplotlib >= 3.8.0

### Development
- pytest >= 7.4.0
- black >= 23.9.0
- mypy >= 1.5.0
- ruff >= 0.11.0

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## Support

For issues and questions, please open an issue on the repository.
