#!/bin/bash
# Script de inicialização do DWPLUS Triage

set -e

echo "🚀 Iniciando DWPLUS Triage..."
echo "================================"

# Carrega variáveis de ambiente se .env existir
if [ -f .env ]; then
  echo "📄 Carregando .env..."
  export $(grep -v '^#' .env | xargs)
fi

# Backend
echo ""
echo "⚙️  Configurando backend..."
cd backend

if [ ! -d "venv" ]; then
  echo "📦 Criando virtualenv..."
  python3 -m venv venv
fi

source venv/bin/activate

echo "📥 Instalando dependências..."
pip install -r requirements.txt -q

echo "▶️  Iniciando backend em http://localhost:${API_PORT:-8000}..."
python main.py &
BACKEND_PID=$!

cd ..

# Frontend
echo ""
echo "🌐 Iniciando frontend em http://localhost:${FRONTEND_PORT:-8080}..."
cd frontend
python3 -m http.server "${FRONTEND_PORT:-8080}" &
FRONTEND_PID=$!

cd ..

echo ""
echo "================================"
echo "✓ Backend:  http://localhost:${API_PORT:-8000}"
echo "✓ Docs API: http://localhost:${API_PORT:-8000}/docs"
echo "✓ Frontend: http://localhost:${FRONTEND_PORT:-8080}"
echo "================================"
echo ""
echo "Para parar os serviços: Ctrl+C"
echo "PIDs: backend=$BACKEND_PID  frontend=$FRONTEND_PID"

# Aguarda Ctrl+C e encerra ambos os processos
trap "echo ''; echo '🛑 Encerrando...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

wait $BACKEND_PID $FRONTEND_PID
