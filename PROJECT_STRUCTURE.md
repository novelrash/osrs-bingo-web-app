# Project Structure - Pea Kingdom Bingo

## Overview
This document outlines the clean, sanitized project structure for the Pea Kingdom Bingo application, built through human-AI collaboration.

## Directory Structure

```
pea-kingdom-bingo/
├── README.md                           # Main project documentation
├── LICENSE                             # MIT License with AI collaboration note
├── PROJECT_STRUCTURE.md               # This file
├── .gitignore                         # Git ignore patterns
├── requirements.txt                   # Python dependencies
├── cognito-config.env.example        # Environment configuration template
├── app.py                             # Main Flask application
├── auth.py                            # AWS Cognito authentication module
├── docs/                              # Documentation directory
│   ├── ARCHITECTURE.md               # System architecture documentation
│   ├── AI_COLLABORATION.md           # AI-assisted development guide
│   └── SETUP.md                      # Setup and deployment guide
├── scripts/                           # Deployment and utility scripts
│   └── deploy.sh                     # Safe deployment script
├── templates/                         # Jinja2 HTML templates
│   ├── base.html                     # Base template with navigation
│   ├── index.html                    # Main leaderboard page
│   ├── submit_completion.html        # User submission form
│   ├── team_progress.html            # Team progress view
│   ├── team_details.html             # Individual team details
│   ├── tile_overview.html            # Tile catalog with search
│   ├── admin_login.html              # Admin authentication
│   ├── admin_dashboard.html          # Admin control panel
│   ├── add_team.html                 # Team creation form
│   ├── add_competitor.html           # Player registration form
│   ├── add_tile.html                 # Tile creation form
│   └── view_completions.html         # Completion management
└── static/                           # Static assets
    ├── css/                          # Stylesheets
    │   └── custom.css               # Custom styling
    ├── js/                           # JavaScript files
    │   └── app.js                   # Client-side functionality
    └── images/                       # Image assets
        └── favicon.ico              # Site favicon
```

## Core Files

### Application Core
- **`app.py`** - Main Flask application with routes, models, and business logic
- **`auth.py`** - AWS Cognito authentication with JWT token validation
- **`requirements.txt`** - Python package dependencies

### Configuration
- **`cognito-config.env.example`** - Environment variable template
- **`.gitignore`** - Git ignore patterns for Python/Flask projects

### Documentation
- **`README.md`** - Comprehensive project overview and quick start
- **`docs/ARCHITECTURE.md`** - Detailed system architecture and design
- **`docs/AI_COLLABORATION.md`** - AI-assisted development methodology
- **`docs/SETUP.md`** - Complete setup and deployment guide

### Templates (Jinja2)
- **`base.html`** - Base template with Bootstrap navigation
- **`index.html`** - Main leaderboard with team and individual rankings
- **`submit_completion.html`** - User-facing completion submission form
- **`admin_*.html`** - Admin interface templates for management

### Static Assets
- **`static/css/custom.css`** - Custom styling for OSRS-themed design
- **`static/js/app.js`** - Client-side JavaScript for interactivity
- **`static/images/`** - Image assets and favicon

### Scripts
- **`scripts/deploy.sh`** - Safe deployment script with selective updates

## Key Features by File

### `app.py` - Main Application
```python
# Database Models
class Team(db.Model)              # Team management
class Competitor(db.Model)        # Individual players
class Tile(db.Model)             # Bingo objectives
class TeamTileCompletion(db.Model) # Completion tracking

# Public Routes
@app.route('/')                   # Main leaderboard
@app.route('/submit_completion')  # User submissions
@app.route('/api/leaderboard')    # JSON API

# Admin Routes (Protected)
@app.route('/admin/dashboard')    # Admin control panel
@app.route('/add_tile')          # Tile management
@app.route('/add_competitor')    # Player management
```

### `auth.py` - Authentication
```python
class CognitoAuth:
    def authenticate_user()       # Username/password auth
    def verify_token()           # JWT token validation
    def is_admin()              # Admin privilege check

@require_admin                   # Admin route decorator
@admin_optional                 # Optional admin decorator
```

### Templates - User Interface
- **Responsive Design**: Bootstrap 5 with mobile-first approach
- **OSRS Theme**: RuneScape-inspired styling and colors
- **Admin Interface**: Comprehensive management tools
- **User Experience**: Intuitive submission and progress tracking

## AI Collaboration Artifacts

### AI-Generated Components
- **Database Models**: Complete ORM with relationships and properties
- **Authentication System**: Full AWS Cognito integration with JWT
- **Route Handlers**: CRUD operations with validation and error handling
- **Templates**: Responsive HTML with Bootstrap styling
- **Documentation**: Comprehensive guides and architecture diagrams

### Human Contributions
- **Requirements**: Business logic and user experience specifications
- **Testing**: Real-world validation and feedback
- **Deployment**: AWS infrastructure and domain configuration
- **Content**: Tile definitions and competition rules

## Development Workflow

### Local Development
1. Clone repository
2. Set up virtual environment
3. Configure AWS Cognito
4. Initialize database
5. Run development server

### Deployment Process
1. **Template Updates**: `./scripts/deploy.sh --templates-only`
2. **Application Updates**: `./scripts/deploy.sh --app-only`
3. **Full Deployment**: `./scripts/deploy.sh --full`

### Quality Assurance
- **Code Review**: Human oversight of AI-generated code
- **Testing**: Comprehensive validation of functionality
- **Security**: AWS Cognito integration with proper token handling
- **Performance**: Caching and optimization strategies

## Technology Stack

### Backend
- **Python 3.7+**: Core programming language
- **Flask 2.3.3**: Web framework
- **SQLAlchemy 2.0**: Database ORM
- **SQLite**: Default database (production-ready)

### Authentication
- **AWS Cognito**: User pool management
- **JWT Tokens**: Stateless authentication
- **Session Management**: Secure token storage

### Frontend
- **Bootstrap 5**: Responsive CSS framework
- **Jinja2**: Server-side templating
- **Custom CSS**: OSRS-themed styling

### Infrastructure
- **AWS EC2**: Virtual server hosting
- **Nginx**: Reverse proxy and static serving
- **Let's Encrypt**: SSL certificate management
- **systemd**: Process management

## Security Considerations

### Authentication Security
- AWS Cognito User Pool with MFA support
- JWT token validation with proper key verification
- Session management with secure cookies
- Role-based access control for admin functions

### Application Security
- SQLAlchemy ORM prevents SQL injection
- Jinja2 auto-escaping prevents XSS
- Input validation on all forms
- HTTPS enforcement for all traffic

### Deployment Security
- Environment variables for sensitive configuration
- Secure file permissions on server
- Regular security updates and patches
- Backup and recovery procedures

## Performance Optimization

### Caching Strategy
- Flask-Caching for expensive database operations
- Template caching for frequently accessed pages
- Static asset caching with proper headers
- Database query optimization with eager loading

### Scalability Features
- Gunicorn multi-worker deployment
- Nginx load balancing capability
- Database migration path to PostgreSQL
- CDN integration for static assets

## Maintenance and Updates

### Regular Maintenance
- Security updates for dependencies
- Database backup and cleanup
- Log rotation and monitoring
- SSL certificate renewal

### Feature Development
- AI-assisted code generation for new features
- Comprehensive testing before deployment
- Documentation updates with changes
- User feedback integration

This project structure demonstrates modern web development practices with AI assistance, emphasizing clean code, comprehensive documentation, and production-ready deployment strategies.
