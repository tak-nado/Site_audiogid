import os
import uuid
import json
from datetime import datetime
from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    url_for,
    Response,
)
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'GOIDA!IpYN(#o@uny788q8)'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = (
    'postgresql://neondb_owner:npg_nHMkI1dVi9RT@ep-rapid-rice-akf08p74-pooler.c-3.us-west-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB

YANDEX_MAPS_API_KEY = 'f68b5c1b-7948-45ee-a8dc-2739ed15a546'

db = SQLAlchemy(app)

class Guide(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, default='Без названия')
    description = db.Column(db.Text, default='')
    share_token = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    points = db.relationship('Point', backref='guide', lazy=True,
                             cascade='all, delete-orphan', order_by='Point.order')

class Point(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guide_id = db.Column(db.Integer, db.ForeignKey('guide.id'), nullable=False)
    order = db.Column(db.Integer, default=0)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    title = db.Column(db.String(255), default='')
    description = db.Column(db.Text, default='')
    audio_data = db.Column(db.LargeBinary, nullable=True)     
    audio_mimetype = db.Column(db.String(100), nullable=True)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    guides = Guide.query.order_by(Guide.created_at.desc()).all()
    return render_template('index.html', guides=guides)

@app.route('/create')
def create_guide_page():
    return render_template('create.html', yandex_maps_key=YANDEX_MAPS_API_KEY)

@app.route('/guide/<token>')
def view_guide(token):
    guide = Guide.query.filter_by(share_token=token).first_or_404()
    points_data = []
    for p in guide.points:
        points_data.append({
            'lat': p.lat,
            'lon': p.lon,
            'title': p.title,
            'description': p.description,
            'has_audio': p.audio_data is not None,
            'audio_url': url_for('get_audio', point_id=p.id) if p.audio_data else None
        })
    points_json = json.dumps(points_data, ensure_ascii=False)
    return render_template('view.html',
                           guide=guide,
                           points_json=points_json,
                           yandex_maps_key=YANDEX_MAPS_API_KEY)

@app.route('/audio/<int:point_id>')
def get_audio(point_id):
    point = Point.query.get_or_404(point_id)
    if point.audio_data is None:
        return "No audio", 404
    return Response(point.audio_data, mimetype=point.audio_mimetype or 'audio/mpeg')

@app.route('/api/guides', methods=['POST'])
def api_create_guide():
    title = request.form.get('title', 'Без названия')
    description = request.form.get('description', '')

    guide = Guide(
        title=title,
        description=description,
        share_token=uuid.uuid4().hex[:12]
    )
    db.session.add(guide)
    db.session.flush()

    i = 0
    while True:
        prefix = f'points[{i}]'
        lat = request.form.get(f'{prefix}[lat]')
        if lat is None:
            break
        lon = request.form.get(f'{prefix}[lon]')
        point_title = request.form.get(f'{prefix}[title]', '')
        point_desc = request.form.get(f'{prefix}[description]', '')
        order = int(request.form.get(f'{prefix}[order]', i))

        audio_data = None
        audio_mimetype = None
        audio_file = request.files.get(f'audio_{i}')
        if audio_file and audio_file.filename:
            audio_data = audio_file.read()
            audio_mimetype = audio_file.mimetype

        point = Point(
            guide_id=guide.id,
            lat=float(lat),
            lon=float(lon),
            title=point_title,
            description=point_desc,
            order=order,
            audio_data=audio_data,
            audio_mimetype=audio_mimetype
        )
        db.session.add(point)
        i += 1

    db.session.commit()
    return jsonify({
        'id': guide.id,
        'share_token': guide.share_token,
        'url': url_for('view_guide', token=guide.share_token, _external=True)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)