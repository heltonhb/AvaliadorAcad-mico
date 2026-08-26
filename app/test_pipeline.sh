#!/bin/bash
set -e

# Kill any existing server
pkill -f "uvicorn api:app" 2>/dev/null || true
sleep 1

cd /home/helton/AnaliseTextos/app
source venv/bin/activate
CELERY_TASK_ALWAYS_EAGER=true timeout 180 uvicorn api:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!
sleep 3

echo "=== Register ==="
curl -s http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"pipeline_final@test.com","password":"finaltest123","name":"Final Pipeline Test"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print('User:', d['user']['email'])"
echo ""

echo "=== Login ==="
TOKEN=$(curl -s http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"pipeline_final@test.com","password":"finaltest123"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['access_token'])")
echo "Token: ${TOKEN:0:50}..."
echo ""

echo "=== Upload ==="
# Create test PDF
cat > /tmp/test_pipeline_final.pdf << 'EOF'
%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
193
%%EOF

curl -s http://localhost:8000/api/upload \
  -H "Authorization: Bearer $(curl -s http://localhost:8000/api/auth/login -H 'Content-Type: application/json' -d '{"email":"pipeline_final@test.com","password":"finaltest123"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['access_token'])")" \
  -F "file=@/tmp/test_final.pdf"

# Create test PDF
cat > /tmp/test_final.pdf << 'EOF'
%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
193
%%EOF

UPLOAD_RESULT=$(curl -s http://localhost:8000/api/upload \
  -H "Authorization: Bearer $(curl -s http://localhost:8000/api/auth/login -H 'Content-Type: application/json' -d '{"email":"uploadtest@test.com","password":"uploadtest123"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['access_token'])")" \
  -F "file=@/tmp/test_upload.pdf")

echo "Upload result: $UPLOAD_RESULT"

pkill -f "uvicorn api:app"