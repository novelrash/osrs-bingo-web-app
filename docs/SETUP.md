# Setup Guide - Pea Kingdom Bingo

## Quick Start

### Prerequisites
- Python 3.7 or higher
- AWS Account (for Cognito authentication)
- Domain name (for production deployment)

### Local Development Setup

1. **Clone the repository**
```bash
git clone <your-repository-url>
cd pea-kingdom-bingo
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp cognito-config.env.example cognito-config.env
# Edit cognito-config.env with your AWS Cognito details
```

5. **Initialize database**
```bash
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

6. **Run development server**
```bash
python app.py
```

Visit `http://localhost:5000` to see your application!

## AWS Cognito Setup

### 1. Create User Pool

1. Go to AWS Console → Cognito → User Pools
2. Click "Create user pool"
3. Configure sign-in options:
   - Username
   - Email (optional)
4. Configure security requirements:
   - Password policy: Default
   - MFA: Optional
5. Configure message delivery:
   - Email: Use Cognito (for development)
6. Review and create

### 2. Create App Client

1. In your User Pool, go to "App integration"
2. Click "Create app client"
3. Configure:
   - App type: Public client
   - App client name: `pea-kingdom-bingo-client`
   - Authentication flows:
     - ✅ ALLOW_USER_PASSWORD_AUTH
     - ✅ ALLOW_USER_SRP_AUTH
     - ✅ ALLOW_REFRESH_TOKEN_AUTH
     - ✅ ALLOW_ADMIN_USER_PASSWORD_AUTH
4. Create app client

### 3. Create Admin User

1. In your User Pool, go to "Users"
2. Click "Create user"
3. Configure:
   - Username: `admin`
   - Password: Set temporary password
   - Email: Your email address
4. Create user
5. Create admin group and add user to it

### 4. Update Configuration

Update your `cognito-config.env`:
```bash
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
COGNITO_CLIENT_ID=your_client_id_here
COGNITO_CLIENT_SECRET=your_client_secret_here
COGNITO_REGION=us-east-1
FLASK_SECRET_KEY=your_secure_random_key_here
```

## Production Deployment

### AWS EC2 Setup

1. **Launch EC2 Instance**
   - AMI: Amazon Linux 2
   - Instance Type: t3.micro (or larger)
   - Security Group: Allow HTTP (80), HTTPS (443), SSH (22)

2. **Connect and Install Dependencies**
```bash
sudo yum update -y
sudo yum install -y python3 python3-pip nginx git
sudo pip3 install gunicorn
```

3. **Deploy Application**
```bash
git clone <your-repository-url> /opt/pea-kingdom-bingo
cd /opt/pea-kingdom-bingo
sudo pip3 install -r requirements.txt
```

4. **Configure Environment**
```bash
sudo cp cognito-config.env.example /opt/pea-kingdom-bingo/cognito-config.env
sudo nano /opt/pea-kingdom-bingo/cognito-config.env
# Add your configuration
```

5. **Create Systemd Service**
```bash
sudo nano /etc/systemd/system/pea-kingdom-bingo.service
```

Add:
```ini
[Unit]
Description=Pea Kingdom Bingo Flask App
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/opt/pea-kingdom-bingo
Environment=PATH=/opt/pea-kingdom-bingo/venv/bin
EnvironmentFile=/opt/pea-kingdom-bingo/cognito-config.env
ExecStart=/usr/local/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

6. **Configure Nginx**
```bash
sudo nano /etc/nginx/conf.d/pea-kingdom-bingo.conf
```

Add:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /opt/pea-kingdom-bingo/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

7. **Start Services**
```bash
sudo systemctl enable pea-kingdom-bingo
sudo systemctl start pea-kingdom-bingo
sudo systemctl enable nginx
sudo systemctl start nginx
```

### SSL Certificate Setup

1. **Install Certbot**
```bash
sudo yum install -y certbot python3-certbot-nginx
```

2. **Obtain Certificate**
```bash
sudo certbot --nginx -d your-domain.com
```

3. **Auto-renewal**
```bash
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Database Management

### Initial Data Setup

1. **Create Teams**
```python
python -c "
from app import app, db, Team
app.app_context().push()
teams = ['Team Alpha', 'Team Beta', 'Team Gamma']
for team_name in teams:
    team = Team(name=team_name)
    db.session.add(team)
db.session.commit()
print('Teams created!')
"
```

2. **Add Sample Tiles**
```python
python -c "
from app import app, db, Tile
app.app_context().push()
tiles = [
    ('Complete Tutorial', 'Finish the game tutorial', 1),
    ('First Boss Kill', 'Defeat your first boss', 5),
    ('Level 50 Achievement', 'Reach level 50', 10)
]
for name, desc, points in tiles:
    tile = Tile(name=name, description=desc, points=points)
    db.session.add(tile)
db.session.commit()
print('Sample tiles created!')
"
```

### Backup and Restore

1. **Backup Database**
```bash
cp /opt/pea-kingdom-bingo/leaderboard.db /opt/pea-kingdom-bingo/backup_$(date +%Y%m%d_%H%M%S).db
```

2. **Restore Database**
```bash
sudo systemctl stop pea-kingdom-bingo
cp /opt/pea-kingdom-bingo/backup_YYYYMMDD_HHMMSS.db /opt/pea-kingdom-bingo/leaderboard.db
sudo systemctl start pea-kingdom-bingo
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Check Cognito configuration in `cognito-config.env`
   - Verify authentication flows are enabled in Cognito console
   - Check AWS credentials and permissions

2. **Database Errors**
   - Ensure database file permissions are correct
   - Check disk space availability
   - Verify SQLite installation

3. **Performance Issues**
   - Monitor system resources (CPU, memory)
   - Check database query performance
   - Review cache configuration

### Logs and Monitoring

1. **Application Logs**
```bash
sudo journalctl -u pea-kingdom-bingo -f
```

2. **Nginx Logs**
```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

3. **Health Check**
```bash
curl http://localhost/status
```

### Performance Tuning

1. **Gunicorn Workers**
   - Adjust worker count based on CPU cores
   - Monitor memory usage per worker

2. **Database Optimization**
   - Consider PostgreSQL for larger datasets
   - Implement database indexing for frequently queried fields

3. **Caching**
   - Configure Redis for distributed caching
   - Implement CDN for static assets

## Development Workflow

### Making Changes

1. **Template Updates** (Safe)
```bash
./scripts/deploy.sh --templates-only
```

2. **Application Updates**
```bash
./scripts/deploy.sh --app-only
```

3. **Full Deployment**
```bash
./scripts/deploy.sh --full
```

### Testing

1. **Local Testing**
```bash
python -m pytest tests/
```

2. **Production Health Check**
```bash
curl https://your-domain.com/status
```

### Monitoring

1. **Application Status**
```bash
sudo systemctl status pea-kingdom-bingo
```

2. **Resource Usage**
```bash
htop
df -h
```

## Security Considerations

### Production Security

1. **Environment Variables**
   - Never commit secrets to version control
   - Use strong, unique passwords
   - Rotate secrets regularly

2. **Network Security**
   - Configure security groups properly
   - Use HTTPS for all traffic
   - Implement rate limiting

3. **Application Security**
   - Keep dependencies updated
   - Monitor for security vulnerabilities
   - Implement proper input validation

### Backup Strategy

1. **Database Backups**
   - Daily automated backups
   - Test restore procedures
   - Store backups securely

2. **Application Backups**
   - Version control for code
   - Configuration backups
   - Deployment rollback procedures

This setup guide provides a comprehensive foundation for deploying and maintaining your Pea Kingdom Bingo application. For additional support, refer to the architecture documentation and AI collaboration guide.
