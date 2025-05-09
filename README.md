├── .github/                     # GitHub workflows for CI/CD
│   └── workflows/
│       └── ci.yml
├── api/                         # FastAPI backend
├── core/                        # Core functionality
├── data/                        # Data storage
├── docker/                      # Dockerfiles and compose files
├── k8s/                         # Kubernetes manifests
├── monitoring/                  # Monitoring setup
├── scripts/                     # Helper scripts
├── tests/                       # Unit and integration tests
├── src/                         # Source code (optional, see notes below)
│   ├── video_qa/                # Python package
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI entry point (if using src/)
│   │   └── ...                  
├── pyproject.toml               # Poetry configuration
├── poetry.lock                  # Poetry lock file (auto-generated)
├── .env                         # Environment variables
├── .gitignore                   # Git ignore rules
├── README.md                    # Project documentation