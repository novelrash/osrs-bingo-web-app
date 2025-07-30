# System Architecture - Pea Kingdom Bingo

## Overview

Pea Kingdom Bingo is a Flask-based web application designed for managing team-based bingo competitions with individual contribution tracking. The system demonstrates modern web development practices, cloud integration, and AI-assisted development methodologies.

## Technology Stack

### Backend Technologies
- **Python 3.7+**: Core programming language
- **Flask 2.3.3**: Lightweight web framework
- **SQLAlchemy 2.0**: Object-Relational Mapping (ORM)
- **SQLite**: Default database (production-ready for small-medium scale)
- **Gunicorn**: WSGI HTTP Server for production

### Authentication & Security
- **AWS Cognito**: Enterprise-grade user authentication
- **JWT Tokens**: Stateless authentication with token validation
- **HTTPS/TLS**: End-to-end encryption via Let's Encrypt
- **Session Management**: Secure token storage and validation

### Frontend Technologies
- **Bootstrap 5**: Responsive CSS framework
- **Jinja2**: Server-side templating engine
- **JavaScript**: Client-side interactivity
- **Font Awesome**: Icon library

### Infrastructure & Deployment
- **AWS EC2**: Virtual server hosting
- **Nginx**: Reverse proxy and static file serving
- **systemd**: Process management and auto-restart
- **Let's Encrypt**: Automated SSL certificate management

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Internet                                 │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Load Balancer                                 │
│                     (Nginx)                                     │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │   SSL/TLS       │ │  Static Assets  │ │   Rate Limiting │   │
│  │  Termination    │ │     Serving     │ │   & Security    │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Application Layer                               │
│                   (Flask + Gunicorn)                           │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │   Web Routes    │ │   API Endpoints │ │  Admin Interface│   │
│  │   (Public)      │ │     (JSON)      │ │  (Protected)    │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │  Authentication│ │    Caching      │ │   Validation    │   │
│  │   Middleware    │ │   (Flask-Cache) │ │   & Security    │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Data Layer                                    │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │   SQLite DB     │ │   File Storage  │ │   Session Store │   │
│  │  (Primary Data) │ │  (Static Assets)│ │   (In-Memory)   │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                External Services                                │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │   AWS Cognito   │ │  Let's Encrypt  │ │   DNS Provider  │   │
│  │ (Authentication)│ │ (SSL Certificates)│ │  (Domain Mgmt)  │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Data Architecture

### Entity Relationship Diagram

```
┌─────────────────┐         ┌─────────────────┐
│      Team       │         │   Competitor    │
├─────────────────┤         ├─────────────────┤
│ id (PK)         │◄────────┤ id (PK)         │
│ name (UNIQUE)   │    1:N  │ name (UNIQUE)   │
│                 │         │ team_id (FK)    │
└─────────────────┘         └─────────────────┘
         │                           │
         │ 1:N                       │ 1:N
         ▼                           ▼
┌─────────────────┐         ┌─────────────────┐
│TeamTileCompletion│        │      Tile       │
├─────────────────┤         ├─────────────────┤
│ id (PK)         │────────►│ id (PK)         │
│ team_id (FK)    │    N:1  │ name (UNIQUE)   │
│ tile_id (FK)    │         │ description     │
│ submitted_by(FK)│         │ points          │
│ completed_at    │         │                 │
│ admin_approved  │         │                 │
└─────────────────┘         └─────────────────┘
```

### Database Schema Details

#### Teams Table
- **Purpose**: Represents competing teams
- **Key Fields**: 
  - `id`: Primary key
  - `name`: Unique team identifier
- **Relationships**: One-to-many with Competitors and TeamTileCompletions

#### Competitors Table
- **Purpose**: Individual players within teams
- **Key Fields**:
  - `id`: Primary key
  - `name`: Unique player identifier
  - `team_id`: Foreign key to Team
- **Relationships**: Many-to-one with Team, one-to-many with TeamTileCompletions

#### Tiles Table
- **Purpose**: Bingo objectives with point values
- **Key Fields**:
  - `id`: Primary key
  - `name`: Unique tile identifier
  - `description`: Detailed objective description
  - `points`: Point value for completion
- **Relationships**: One-to-many with TeamTileCompletions

#### TeamTileCompletions Table
- **Purpose**: Tracks tile completions with approval workflow
- **Key Fields**:
  - `id`: Primary key
  - `team_id`: Foreign key to Team
  - `tile_id`: Foreign key to Tile
  - `submitted_by`: Foreign key to Competitor (who submitted)
  - `completed_at`: Timestamp of completion
  - `admin_approved`: Boolean approval status
- **Constraints**: Unique constraint on (team_id, tile_id) - one completion per team per tile

## Application Flow

### User Journey - Public Access

```
User Request → Nginx → Flask App → Database Query → Template Render → Response
     │              │        │           │              │             │
     │              │        │           │              │             ▼
     │              │        │           │              │        HTML Response
     │              │        │           │              │             │
     │              │        │           │              ▼             │
     │              │        │           │         Jinja2 Template    │
     │              │        │           │              │             │
     │              │        │           ▼              │             │
     │              │        │      SQLAlchemy ORM      │             │
     │              │        │           │              │             │
     │              │        ▼           │              │             │
     │              │   Route Handler    │              │             │
     │              │        │           │              │             │
     │              ▼        │           │              │             │
     │         Load Balancer │           │              │             │
     │              │        │           │              │             │
     ▼              │        │           │              │             │
SSL Termination     │        │           │              │             │
     │              │        │           │              │             │
     └──────────────┴────────┴───────────┴──────────────┴─────────────┘
```

### Admin Journey - Protected Access

```
Admin Login → Cognito Auth → JWT Validation → Protected Route → Admin Interface
     │             │              │               │                │
     │             │              │               │                ▼
     │             │              │               │         Admin Dashboard
     │             │              │               │                │
     │             │              │               ▼                │
     │             │              │        @require_admin           │
     │             │              │         Decorator              │
     │             │              │               │                │
     │             │              ▼               │                │
     │             │         Token Verification   │                │
     │             │              │               │                │
     │             ▼              │               │                │
     │        AWS Cognito         │               │                │
     │         User Pool          │               │                │
     │             │              │               │                │
     ▼             │              │               │                │
Username/Password  │              │               │                │
     │             │              │               │                │
     └─────────────┴──────────────┴───────────────┴────────────────┘
```

## Security Architecture

### Authentication Flow

1. **User Login**: Username/password submitted to Flask app
2. **Cognito Validation**: Credentials validated against AWS Cognito User Pool
3. **Token Generation**: Cognito returns JWT tokens (Access, ID, Refresh)
4. **Session Storage**: Tokens stored in Flask session (server-side)
5. **Request Validation**: Each protected request validates JWT token
6. **Token Refresh**: Automatic token refresh using refresh token

### Security Measures

- **Input Validation**: All user inputs validated and sanitized
- **SQL Injection Prevention**: SQLAlchemy ORM prevents direct SQL injection
- **XSS Protection**: Jinja2 auto-escaping prevents cross-site scripting
- **CSRF Protection**: Flask-WTF CSRF tokens on forms
- **HTTPS Enforcement**: All traffic encrypted via SSL/TLS
- **Session Security**: Secure session cookies with HttpOnly flag
- **Rate Limiting**: Nginx-based rate limiting for API endpoints

## Performance Optimization

### Caching Strategy

```
Request → Cache Check → Cache Hit? → Return Cached Data
    │          │            │              │
    │          │            │              ▼
    │          │            │         Fast Response
    │          │            │
    │          │            ▼ (Cache Miss)
    │          │       Database Query
    │          │            │
    │          │            ▼
    │          │       Generate Response
    │          │            │
    │          │            ▼
    │          │       Store in Cache
    │          │            │
    │          ▼            ▼
    │     Cache Layer   Return Response
    │          │            │
    ▼          ▼            ▼
Flask-Cache  Memory    HTTP Response
```

### Performance Features

- **Database Indexing**: Optimized queries with proper indexes
- **Query Optimization**: Efficient SQLAlchemy queries with eager loading
- **Static Asset Caching**: Nginx serves static files with cache headers
- **Template Caching**: Jinja2 template compilation caching
- **Application Caching**: Flask-Caching for expensive operations
- **Connection Pooling**: SQLAlchemy connection pooling

## Scalability Considerations

### Horizontal Scaling Options

1. **Load Balancer**: Multiple Flask app instances behind load balancer
2. **Database Scaling**: Migration path to PostgreSQL with read replicas
3. **Cache Scaling**: Redis cluster for distributed caching
4. **CDN Integration**: CloudFront for global static asset distribution
5. **Container Deployment**: Docker containers with orchestration

### Vertical Scaling Limits

- **Current Setup**: Single EC2 instance with SQLite
- **CPU Scaling**: Multi-core support via Gunicorn workers
- **Memory Scaling**: Configurable cache sizes and connection pools
- **Storage Scaling**: EBS volume expansion for database growth

## Monitoring & Observability

### Health Checks

- **Application Health**: `/status` endpoint with component checks
- **Database Health**: Connection and query validation
- **Cache Health**: Cache connectivity and performance metrics
- **Authentication Health**: Cognito service availability

### Logging Strategy

- **Application Logs**: Flask application logs via Python logging
- **Access Logs**: Nginx access logs for request tracking
- **Error Logs**: Centralized error logging with stack traces
- **Security Logs**: Authentication attempts and security events

### Metrics Collection

- **Response Times**: Request/response latency tracking
- **Error Rates**: HTTP error code monitoring
- **Resource Usage**: CPU, memory, and disk utilization
- **User Activity**: Login attempts, completion submissions

## Deployment Architecture

### CI/CD Pipeline

```
Code Changes → Git Repository → Deployment Script → Server Update
     │              │                │                    │
     │              │                │                    ▼
     │              │                │              Service Restart
     │              │                │                    │
     │              │                ▼                    │
     │              │         Safe Deployment             │
     │              │         (Selective Updates)         │
     │              │                │                    │
     │              ▼                │                    │
     │         Version Control       │                    │
     │              │                │                    │
     ▼              │                │                    │
Development        │                │                    │
Environment        │                │                    │
     │              │                │                    │
     └──────────────┴────────────────┴────────────────────┘
```

### Deployment Options

1. **Template-Only**: Safe UI updates without app restart
2. **App-Only**: Application logic updates with service restart
3. **Static-Only**: Asset updates without service interruption
4. **Full Deployment**: Complete system update with backup

## AI-Assisted Development Architecture

### Human-AI Collaboration Model

```
Requirements → AI Analysis → Code Generation → Human Review → Integration
     │              │              │              │              │
     │              │              │              │              ▼
     │              │              │              │         Testing
     │              │              │              │              │
     │              │              │              ▼              │
     │              │              │        Code Review          │
     │              │              │              │              │
     │              │              ▼              │              │
     │              │         AI Code Gen         │              │
     │              │              │              │              │
     │              ▼              │              │              │
     │         Problem Analysis    │              │              │
     │              │              │              │              │
     ▼              │              │              │              │
Business Logic     │              │              │              │
Definition         │              │              │              │
     │              │              │              │              │
     └──────────────┴──────────────┴──────────────┴──────────────┘
```

### AI Contributions

- **Architecture Design**: System design and technology selection
- **Code Generation**: Core application logic and database models
- **Problem Solving**: Debugging and optimization assistance
- **Documentation**: Comprehensive technical documentation
- **Best Practices**: Security and performance recommendations

### Quality Assurance

- **Code Review**: AI-assisted code analysis and suggestions
- **Testing Strategy**: Automated test generation and validation
- **Security Analysis**: Vulnerability assessment and mitigation
- **Performance Optimization**: Bottleneck identification and solutions

This architecture demonstrates modern web development practices with cloud integration, emphasizing scalability, security, and maintainability through human-AI collaboration.
