"""
Pea Kingdom Bingo - Team Competition Platform

A Flask-based web application for managing team-based bingo competitions
with individual contribution tracking. Built collaboratively with AI assistance.

Author: Human-AI Collaboration
AI Assistant: Claude (Anthropic)
License: MIT
"""

import os
import csv
import json
from io import StringIO, BytesIO
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response, session
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from datetime import datetime
import urllib.parse
from auth import cognito_auth, require_admin, admin_optional

app = Flask(__name__)

# Initialize Cognito authentication
cognito_auth.init_app(app)

# Cache configuration for performance optimization
cache_config = {
    'CACHE_TYPE': 'simple',  # Use in-memory caching for development
    'CACHE_DEFAULT_TIMEOUT': 300  # Cache for 5 minutes
}
cache = Cache(app, config=cache_config)

# Database configuration - easily portable to PostgreSQL/MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///leaderboard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Secret key for sessions - should be environment variable in production
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'change-this-in-production')

# Initialize database
db = SQLAlchemy(app)

# ============================================================================
# DATABASE MODELS
# ============================================================================

class Team(db.Model):
    """
    Represents a competing team in the bingo competition.
    Teams compete against each other for overall rankings.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    competitors = db.relationship('Competitor', backref='team', lazy=True)
    completed_tiles = db.relationship('TeamTileCompletion', backref='team', lazy=True)

    @property
    def total_points(self):
        """Calculate total points from all approved tile completions"""
        return sum(completion.tile.points for completion in self.completed_tiles if completion.admin_approved)

    @property
    def completed_tiles_count(self):
        """Count of approved tile completions"""
        return len([c for c in self.completed_tiles if c.admin_approved])

class Competitor(db.Model):
    """
    Represents an individual player who belongs to a team.
    Individual contributions are tracked separately from team totals.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    submitted_completions = db.relationship('TeamTileCompletion', backref='submitted_by_player', lazy=True)

    @property
    def total_points(self):
        """Calculate individual points based on personal submissions that were approved"""
        return sum(completion.tile.points for completion in self.submitted_completions if completion.admin_approved)

    @property
    def completed_tiles_count(self):
        """Count of tiles this individual submitted that were approved"""
        return len([c for c in self.submitted_completions if c.admin_approved])

class Tile(db.Model):
    """
    Represents a bingo tile/objective with configurable point values.
    Each tile can only be completed once per team.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    points = db.Column(db.Integer, nullable=False, default=1)
    completed_by_teams = db.relationship('TeamTileCompletion', backref='tile', lazy=True)

    @property
    def completion_count(self):
        """Count of teams that have completed this tile"""
        return len([c for c in self.completed_by_teams if c.admin_approved])

class TeamTileCompletion(db.Model):
    """
    Tracks tile completions with admin approval workflow.
    Links teams, tiles, and the individual who submitted the completion.
    """
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    tile_id = db.Column(db.Integer, db.ForeignKey('tile.id'), nullable=False)
    submitted_by = db.Column(db.Integer, db.ForeignKey('competitor.id'), nullable=True)
    completed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    admin_approved = db.Column(db.Boolean, default=True)  # Admin submissions auto-approved
    
    # Ensure one completion per team per tile
    __table_args__ = (db.UniqueConstraint('team_id', 'tile_id', name='unique_team_tile'),)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def invalidate_leaderboard_cache():
    """Invalidate cached leaderboard data when changes occur"""
    cache.delete('index_data')
    cache.delete('team_rankings')
    cache.delete('competitor_rankings')
    cache.delete('tile_overview')

# ============================================================================
# PUBLIC ROUTES - No authentication required
# ============================================================================

@app.route('/')
@admin_optional
def index():
    """
    Main leaderboard page showing both team and individual standings.
    Displays dual leaderboards with team points and individual contributions.
    """
    teams = Team.query.all()
    competitors = Competitor.query.all()
    tiles = Tile.query.all()

    # Sort teams by total points (team competition)
    teams = sorted(teams, key=lambda x: x.total_points, reverse=True)

    # Sort competitors by individual points (personal contributions)
    competitors = sorted(competitors, key=lambda x: x.total_points, reverse=True)

    # Get last update time for freshness indicator
    last_update = TeamTileCompletion.query.order_by(TeamTileCompletion.completed_at.desc()).first()
    last_update_time = last_update.completed_at if last_update else datetime.utcnow()

    return render_template('index.html',
                         teams=teams,
                         competitors=competitors,
                         tiles=tiles,
                         last_update=last_update_time)

@app.route('/submit_completion', methods=['GET', 'POST'])
def submit_completion():
    """
    Self-service completion submission for users.
    Allows players to submit their own completions for admin approval.
    """
    if request.method == 'POST':
        player_name = request.form.get('player_name', '').strip()
        tile_id = request.form.get('tile_id', '').strip()
        
        if player_name and tile_id:
            # Find the player
            player = Competitor.query.filter_by(name=player_name).first()
            if not player:
                flash(f'Player "{player_name}" not found. Please check the spelling.', 'error')
                return redirect(url_for('submit_completion'))
            
            # Find the tile
            tile = Tile.query.get(int(tile_id))
            if not tile:
                flash('Selected tile not found.', 'error')
                return redirect(url_for('submit_completion'))
            
            # Check if team already completed this tile
            existing_completion = TeamTileCompletion.query.filter_by(
                team_id=player.team_id,
                tile_id=int(tile_id)
            ).first()
            
            if existing_completion:
                flash(f'Your team "{player.team.name}" has already completed "{tile.name}"!', 'warning')
            else:
                # Create the completion (pending approval)
                completion = TeamTileCompletion(
                    team_id=player.team_id,
                    tile_id=int(tile_id),
                    submitted_by=player.id,
                    admin_approved=False  # User submissions need approval
                )
                db.session.add(completion)
                db.session.commit()
                invalidate_leaderboard_cache()
                
                flash(f'Completion submitted! "{tile.name}" for team "{player.team.name}" is pending admin approval.', 'success')
                return redirect(url_for('submit_completion'))
    
    # Get all players and tiles for the form
    competitors = Competitor.query.all()
    tiles = Tile.query.all()
    
    return render_template('submit_completion.html', competitors=competitors, tiles=tiles)

@app.route('/team_progress/<player_name>')
def team_progress(player_name):
    """
    Display team progress for a specific player.
    Shows completed tiles and pending submissions.
    """
    player = Competitor.query.filter_by(name=player_name).first()
    if not player:
        flash(f'Player "{player_name}" not found.', 'error')
        return redirect(url_for('submit_completion'))
    
    team = player.team
    all_tiles = Tile.query.all()
    completed_tile_ids = [completion.tile_id for completion in team.completed_tiles if completion.admin_approved]
    pending_completions = TeamTileCompletion.query.filter_by(
        team_id=team.id, 
        admin_approved=False
    ).all()
    
    return render_template('team_progress.html',
                         player=player,
                         team=team,
                         all_tiles=all_tiles,
                         completed_tile_ids=completed_tile_ids,
                         pending_completions=pending_completions)

@app.route('/team/<int:team_id>')
@cache.memoize(300)  # Cache individual team pages for 5 minutes
def team_details(team_id):
    """Display detailed view of a specific team's progress"""
    team = Team.query.get_or_404(team_id)
    all_tiles = Tile.query.all()
    completed_tile_ids = [completion.tile_id for completion in team.completed_tiles if completion.admin_approved]
    
    return render_template('team_details.html', 
                         team=team, 
                         all_tiles=all_tiles,
                         completed_tile_ids=completed_tile_ids)

@app.route('/tiles')
def tile_overview():
    """
    Public tile overview with search and sorting capabilities.
    Shows all available tiles with completion statistics.
    """
    # Get search and sort parameters
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort', 'name')  # name, points, completions
    order = request.args.get('order', 'asc')  # asc, desc

    # Start with all tiles
    tiles_query = Tile.query

    # Apply search filter
    if search:
        tiles_query = tiles_query.filter(
            db.or_(
                Tile.name.ilike(f'%{search}%'),
                Tile.description.ilike(f'%{search}%')
            )
        )

    # Get tiles
    tiles = tiles_query.all()

    # Apply sorting
    if sort_by == 'name':
        tiles = sorted(tiles, key=lambda x: x.name.lower())
    elif sort_by == 'points':
        tiles = sorted(tiles, key=lambda x: x.points)
    elif sort_by == 'completions':
        tiles = sorted(tiles, key=lambda x: x.completion_count)

    # Apply order
    if order == 'desc':
        tiles.reverse()

    return render_template('tile_overview.html',
                         tiles=tiles,
                         search=search,
                         sort_by=sort_by,
                         order=order)

# ============================================================================
# API ROUTES - JSON endpoints for external integration
# ============================================================================

@app.route('/api/leaderboard')
def api_leaderboard():
    """
    JSON API endpoint for leaderboard data.
    Returns both team and individual standings with timestamps.
    """
    teams = Team.query.all()
    competitors = Competitor.query.all()

    # Sort teams by total points
    teams = sorted(teams, key=lambda x: x.total_points, reverse=True)

    # Sort competitors by individual points
    competitors = sorted(competitors, key=lambda x: x.total_points, reverse=True)

    # Get last update time
    last_update = TeamTileCompletion.query.order_by(TeamTileCompletion.completed_at.desc()).first()
    last_update_time = last_update.completed_at.isoformat() if last_update else datetime.utcnow().isoformat()

    return jsonify({
        'teams': [{
            'id': team.id,
            'name': team.name,
            'total_points': team.total_points,
            'completed_tiles_count': team.completed_tiles_count
        } for team in teams],
        'competitors': [{
            'id': comp.id,
            'name': comp.name,
            'team_name': comp.team.name,
            'individual_points': comp.total_points,  # Individual contributions
            'team_points': comp.team.total_points,   # Team total
            'completed_tiles_count': comp.completed_tiles_count
        } for comp in competitors],
        'last_update': last_update_time
    })

@app.route('/status')
def status():
    """
    Health check endpoint for monitoring and load balancers.
    Returns system status and component health.
    """
    try:
        # Check database connection
        db.session.query(Team).first()

        # Get cache status
        cache_status = cache.get('status_check')
        if cache_status is None:
            cache.set('status_check', 'ok', timeout=60)
            cache_status = 'ok'

        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'cache': cache_status,
            'authentication': 'enabled',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/health')
def health():
    """Simple health check for basic monitoring"""
    return jsonify({"status": "healthy", "message": "Pea Kingdom Bingo app is running"})

# ============================================================================
# ADMIN AUTHENTICATION ROUTES
# ============================================================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """
    Admin login using AWS Cognito authentication.
    Handles both GET (show form) and POST (process login).
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username and password:
            # Use Cognito authentication
            result = cognito_auth.authenticate_user(username, password)

            if result and 'error' not in result:
                # Store tokens in session for subsequent requests
                session['access_token'] = result['AccessToken']
                session['id_token'] = result['IdToken']
                session['refresh_token'] = result['RefreshToken']

                flash('Login successful!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                error_msg = result.get('error', 'Authentication failed') if result else 'Authentication failed'
                flash(error_msg, 'error')

    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """Clear admin session and redirect to main page"""
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

# ============================================================================
# ADMIN ROUTES - Require authentication
# ============================================================================

@app.route('/admin/dashboard')
@require_admin
def admin_dashboard():
    """
    Admin dashboard with system statistics and recent activity.
    Central hub for all administrative functions.
    """
    # Get system statistics
    total_teams = Team.query.count()
    total_competitors = Competitor.query.count()
    total_tiles = Tile.query.count()
    total_completions = TeamTileCompletion.query.filter_by(admin_approved=True).count()
    pending_completions = TeamTileCompletion.query.filter_by(admin_approved=False).count()

    # Get recent activity for monitoring
    recent_completions = TeamTileCompletion.query.order_by(TeamTileCompletion.completed_at.desc()).limit(10).all()

    return render_template('admin_dashboard.html',
                         total_teams=total_teams,
                         total_competitors=total_competitors,
                         total_tiles=total_tiles,
                         total_completions=total_completions,
                         pending_completions=pending_completions,
                         recent_completions=recent_completions)

@app.route('/add_tile', methods=['GET', 'POST'])
@require_admin
def add_tile():
    """
    Admin interface for adding new bingo tiles.
    Supports bulk import with point values and validation.
    """
    if request.method == 'POST':
        tile_input = request.form.get('tile_input', '').strip()
        description = request.form.get('description', '').strip()
        
        if tile_input:
            success_count = 0
            error_count = 0
            errors = []
            
            # Split by commas and process each tile
            tile_entries = [entry.strip() for entry in tile_input.split(',') if entry.strip()]
            
            for entry in tile_entries:
                try:
                    # Parse tile name and point value
                    # Supports formats: "Tile Name (5)" or "Tile Name:5"
                    if '(' in entry and entry.endswith(')'):
                        name_part = entry[:entry.rfind('(')].strip()
                        points_part = entry[entry.rfind('(')+1:-1].strip()
                    elif ':' in entry:
                        name_part, points_part = entry.rsplit(':', 1)
                        name_part = name_part.strip()
                        points_part = points_part.strip()
                    else:
                        # No point value specified, use default
                        name_part = entry
                        points_part = '1'
                    
                    if not name_part:
                        errors.append(f"Empty tile name in: '{entry}'")
                        error_count += 1
                        continue
                    
                    # Validate points
                    try:
                        points_value = int(points_part)
                        if points_value < 1 or points_value > 100:
                            errors.append(f"Points must be 1-100 for: '{name_part}' (got {points_value})")
                            error_count += 1
                            continue
                    except ValueError:
                        errors.append(f"Invalid points value for: '{name_part}' (got '{points_part}')")
                        error_count += 1
                        continue
                    
                    # Check for duplicates
                    existing_tile = Tile.query.filter_by(name=name_part).first()
                    if existing_tile:
                        errors.append(f"Tile already exists: '{name_part}'")
                        error_count += 1
                        continue
                    
                    # Create the tile
                    tile = Tile(name=name_part, description=description, points=points_value)
                    db.session.add(tile)
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f"Error processing '{entry}': {str(e)}")
                    error_count += 1
            
            # Commit successful tiles
            if success_count > 0:
                db.session.commit()
                invalidate_leaderboard_cache()
            
            # Show results
            if success_count > 0:
                flash(f'Successfully added {success_count} tile(s)!', 'success')
            
            if error_count > 0:
                flash(f'{error_count} error(s) occurred:', 'warning')
                for error in errors[:5]:  # Show first 5 errors
                    flash(f'• {error}', 'warning')
                if len(errors) > 5:
                    flash(f'• ... and {len(errors) - 5} more errors', 'warning')
            
            if success_count > 0:
                return redirect(url_for('admin_dashboard'))

    return render_template('add_tile.html')

@app.route('/add_competitor', methods=['GET', 'POST'])
@require_admin
def add_competitor():
    """
    Admin interface for adding competitors to teams.
    Supports bulk import with team assignment.
    """
    if request.method == 'POST':
        player_input = request.form.get('player_input', '').strip()
        team_id = request.form.get('team_id', '').strip()
        
        if player_input and team_id:
            success_count = 0
            error_count = 0
            errors = []
            
            # Validate team exists
            team = Team.query.get(int(team_id))
            if not team:
                flash('Selected team does not exist!', 'error')
                teams = Team.query.all()
                return render_template('add_competitor.html', teams=teams)
            
            # Process multiple players
            player_names = [name.strip() for name in player_input.split(',') if name.strip()]
            
            for player_name in player_names:
                try:
                    if not player_name:
                        errors.append("Empty player name found")
                        error_count += 1
                        continue
                    
                    # Check for duplicates
                    existing_player = Competitor.query.filter_by(name=player_name).first()
                    if existing_player:
                        errors.append(f"Player already exists: '{player_name}'")
                        error_count += 1
                        continue
                    
                    # Create the player
                    competitor = Competitor(name=player_name, team_id=int(team_id))
                    db.session.add(competitor)
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f"Error processing '{player_name}': {str(e)}")
                    error_count += 1
            
            # Commit successful players
            if success_count > 0:
                db.session.commit()
                invalidate_leaderboard_cache()
            
            # Show results
            if success_count > 0:
                flash(f'Successfully added {success_count} player(s) to {team.name}!', 'success')
            
            if error_count > 0:
                flash(f'{error_count} error(s) occurred:', 'warning')
                for error in errors[:5]:
                    flash(f'• {error}', 'warning')
                if len(errors) > 5:
                    flash(f'• ... and {len(errors) - 5} more errors', 'warning')
            
            if success_count > 0:
                return redirect(url_for('admin_dashboard'))

    teams = Team.query.all()
    return render_template('add_competitor.html', teams=teams)

@app.route('/add_team', methods=['GET', 'POST'])
@require_admin
def add_team():
    """Admin interface for creating new teams"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()

        if name:
            team = Team(name=name)
            db.session.add(team)
            db.session.commit()
            invalidate_leaderboard_cache()
            flash('Team added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))

    return render_template('add_team.html')

@app.route('/admin_complete_tile', methods=['POST'])
@require_admin
def admin_complete_tile():
    """
    Admin direct tile completion (bypasses approval workflow).
    Used for manual completions and corrections.
    """
    team_id = request.form.get('team_id')
    tile_id = request.form.get('tile_id')

    if team_id and tile_id:
        # Check if already completed
        existing = TeamTileCompletion.query.filter_by(
            team_id=int(team_id),
            tile_id=int(tile_id)
        ).first()

        if not existing:
            completed_tile = TeamTileCompletion(
                team_id=int(team_id),
                tile_id=int(tile_id),
                admin_approved=True  # Admin completions are auto-approved
            )
            db.session.add(completed_tile)
            db.session.commit()
            invalidate_leaderboard_cache()
            flash('Tile completion recorded!', 'success')
        else:
            flash('Tile already completed by this team!', 'warning')

    return redirect(url_for('admin_dashboard'))

@app.route('/approve_completion/<int:completion_id>', methods=['POST'])
@require_admin
def approve_completion(completion_id):
    """Approve a user-submitted completion"""
    completion = TeamTileCompletion.query.get_or_404(completion_id)
    completion.admin_approved = True
    db.session.commit()
    invalidate_leaderboard_cache()
    
    flash(f'Approved completion: {completion.team.name} - {completion.tile.name}', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/remove_completion/<int:completion_id>', methods=['POST'])
@require_admin
def remove_completion(completion_id):
    """Remove a completion (admin correction tool)"""
    completion = TeamTileCompletion.query.get_or_404(completion_id)
    team_name = completion.team.name
    tile_name = completion.tile.name

    db.session.delete(completion)
    db.session.commit()
    invalidate_leaderboard_cache()

    flash(f'Removed completion: {team_name} - {tile_name}', 'success')
    return redirect(url_for('view_completions'))

@app.route('/view_completions')
@require_admin
def view_completions():
    """Admin interface for viewing and managing all completions"""
    completions = TeamTileCompletion.query.order_by(TeamTileCompletion.completed_at.desc()).all()
    return render_template('view_completions.html', completions=completions)

# ============================================================================
# APPLICATION INITIALIZATION
# ============================================================================

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Development server configuration
    app.run(host='0.0.0.0', port=5000, debug=False)
