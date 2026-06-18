import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from app import app
from config import DEBUG

if __name__ == '__main__':
    print("=" * 50)
    print("  HeyvanBazar ise dusdu!")
    print("  http://localhost:5000")
    print("  Admin: http://localhost:5000/admin/")
    print(f"  Debug rejimi: {'ACIQ' if DEBUG else 'SONDURULUB'}")
    print("=" * 50)
    app.run(debug=DEBUG, host='0.0.0.0', port=5000)
