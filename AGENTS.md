# EmoVision Agent Development Guidelines

## Project Overview
EmoVision is a visual emotion recognition web application supporting multiple visual sources (images, videos, cameras) with real-time emotion recognition pipeline configuration, debugging, and deployment.

## Build Commands

### Backend
```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Run backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
# Install dependencies  
cd frontend
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Lint frontend code
npm run lint
```

### Testing
```bash
# Backend tests
cd backend
pytest tests/ -v

# Run single test file
pytest tests/test_filename.py

# Run single test function
pytest tests/test_filename.py::test_function_name -v

# Frontend type checking
cd frontend
npm run lint
```

## Code Style Guidelines

### Python (Backend)
- Follow PEP 8 style guide with type annotations
- Use 4 spaces for indentation
- Line length: 88 characters maximum
- Function and variable names: snake_case
- Class names: PascalCase
- Constants: UPPER_CASE
- Import order: standard library → third party → local application/library specific
- Group imports with blank lines between groups
- Always use absolute imports for internal modules
- Module docstrings should use triple double quotes
- Function docstrings should document Args, Returns, Raises sections when applicable

### TypeScript/React (Frontend)
- Use strict TypeScript mode
- Component names: PascalCase
- Function/variable names: camelCase
- Type names: PascalCase
- Use functional components with hooks
- Prefer arrow functions for component definitions
- Use TypeScript interfaces for props and state
- Follow React naming conventions (onClick, onSubmit, etc.)
- Use kebab-case for CSS class names
- Limit component complexity (single responsibility principle)
- Use descriptive prop names rather than abbreviations

### Formatting
- Python: Use Black for formatting (black .)
- TypeScript: Use Prettier (prettier --write .)
- Both: Respect editorconfig settings

### Error Handling
- Python: Use specific exception types and meaningful messages
- Python: Implement proper logging with structured logs
- TypeScript: Handle promise rejections appropriately
- TypeScript: Use proper error boundaries for React components
- Always validate inputs at API boundaries
- Never expose internal error details to clients

### Imports
- Python: Standard library imports first, then third-party, then local project imports
- Python: Each import group separated by blank line
- Python: Avoid wildcard imports (*)
- TypeScript: Import only needed functions from libraries
- TypeScript: Use path aliases (@/*) for absolute imports from src

### Naming Conventions
- Variables/functions: Descriptive and unambiguous names
- Boolean variables: Prefix with is/, has/, can/, should/
- Constants: All uppercase with underscores
- Private members: Prefix with underscore (_)
- Test files: test_*.py or *_test.py
- Test functions: test_[scenario_under_test]_[expected_result]

### Types & Documentation
- Python: Use type hints for all public functions/methods
- Python: Include docstrings for all public classes and methods
- TypeScript: Use strict typing and avoid 'any' type when possible
- Both: Document public APIs clearly
- Both: Comment complex business logic

### Security
- Never hardcode secrets in source code
- Validate and sanitize all user inputs
- Use environment variables for configuration
- Implement proper authentication/authorization where needed
- Avoid logging sensitive data

### Performance
- Python: Use efficient algorithms and data structures
- Python: Consider async/await for I/O-bound operations
- TypeScript: Optimize React component renders
- TypeScript: Use React.memo for expensive components
- Both: Profile slow operations when performance issues arise

### Git Workflow
- Branch names: feature/short-description or fix/issue-number
- Commits: Follow conventional commits format
- Keep commits focused on single logical change
- Write clear, descriptive commit messages
- Update changelog for major changes
- Squash small commits before merging

### Architecture Patterns
- Python: Follow dependency injection pattern for services
- Python: Separate concerns between API, core logic, and modules
- TypeScript: Use state management (Zustand) consistently
- TypeScript: Separate UI components from business logic
- Both: Prefer composition over inheritance