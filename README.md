# Kinga On-Premise

Cette version du projet est pensée pour un déploiement self-hosted avec Dokploy, sans Kubernetes.

## Services inclus

- API FastAPI sur le port 8000
- UI d'administration sur le port 3000
- UI web sur le port 3001
- PostgreSQL sur le port 5432
- Redis sur le port 6379

## Prérequis

- Docker
- Docker Compose
- Un serveur ou un environnement Dokploy

## Configuration

1. Copier le fichier d'exemple :
   ```bash
   cp .env.example .env
   ```
2. Adapter les variables sensibles dans .env.
3. Construire et démarrer les services :
   ```bash
   docker compose up --build -d
   ```

## Vérification

- API : http://localhost:8000/
- Admin : http://localhost:3000/
- Web : http://localhost:3001/

## Notes de sécurité

- Utiliser des secrets forts pour SECRET_KEY et ENCRYPTION_KEY.
- Ne pas exposer PostgreSQL et Redis publiquement si ce n'est pas nécessaire.
- Pour Dokploy, injecter les variables via l'interface ou le fichier .env.
