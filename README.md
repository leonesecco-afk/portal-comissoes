# Portal de Comissões (Flask)
Login de consultores, visualização de notas e regras de comissão.
## Deploy rápido (Render)
Build: `pip install -r requirements.txt && python seed.py`
Start: `gunicorn app:app --workers=2 --threads=8 --timeout=120`
Env: `SECRET_KEY`, `DATABASE_URL=sqlite:///commission.db`
Usuários demo: admin@pinho.com/admin123 e joao@pinho.com/123456
